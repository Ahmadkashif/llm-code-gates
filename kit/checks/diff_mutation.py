#!/usr/bin/env python3
"""diff-mutation: mutation testing restricted to lines added since BASE_REF (Python), capped and time-boxed.

Answers "do the tests that came with this change actually constrain it?" (tests written to pass). For each
mutable expression on an added line it applies ONE small mutation (boundary flip, operator swap, constant
change, negation, return None), runs the test command in a scratch copy of the working tree, and counts kills.

Rules
  test-adequacy.mutation-score    score < GATES_MUT_MIN_SCORE with >= GATES_MUT_MIN_MUTANTS mutants  block
  test-adequacy.surviving-mutant  one per survivor (where the tests are blind)                       inform
  test-adequacy.mutation-skipped  baseline tests fail / nothing to mutate / budget exhausted         inform

Other stacks: the stack profile can point GATES_MUTATION_CMD at a native tool (StrykerJS --incremental,
cargo-mutants --in-diff, PIT with scmMutationCoverage); this script then only runs that command.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import gateslib as g  # noqa: E402

SWAP_CMP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq,
            ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot, ast.IsNot: ast.Is}
SWAP_BIN = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult, ast.FloorDiv: ast.Mult,
            ast.Mod: ast.FloorDiv, ast.Pow: ast.Mult}
PRIORITY = {"cmp": 0, "bool": 1, "const": 2, "bin": 3, "not": 4, "return": 5, "aug": 3}


def candidates(tree: ast.AST, lines: set[int]):
    """Yield (index, kind, lineno, description) for mutable nodes on added lines; index = position in ast.walk."""
    for i, n in enumerate(ast.walk(tree)):
        ln = getattr(n, "lineno", None)
        if ln not in lines:
            continue
        if isinstance(n, ast.Compare) and type(n.ops[0]) in SWAP_CMP:
            yield i, "cmp", ln, f"{type(n.ops[0]).__name__} -> {SWAP_CMP[type(n.ops[0])].__name__}"
        elif isinstance(n, ast.BinOp) and type(n.op) in SWAP_BIN:
            yield i, "bin", ln, f"{type(n.op).__name__} -> {SWAP_BIN[type(n.op)].__name__}"
        elif isinstance(n, ast.AugAssign) and type(n.op) in SWAP_BIN:
            yield i, "aug", ln, f"{type(n.op).__name__}= -> {SWAP_BIN[type(n.op)].__name__}="
        elif isinstance(n, ast.BoolOp):
            yield i, "bool", ln, f"{type(n.op).__name__} -> {'Or' if isinstance(n.op, ast.And) else 'And'}"
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            yield i, "not", ln, "remove not"
        elif isinstance(n, ast.Constant) and type(n.value) in (int, float) and not isinstance(n.value, bool):
            yield i, "const", ln, f"{n.value!r} -> {n.value + 1!r}"
        elif isinstance(n, ast.Constant) and isinstance(n.value, bool):
            yield i, "const", ln, f"{n.value} -> {not n.value}"
        elif isinstance(n, ast.Return) and n.value is not None and not (
                isinstance(n.value, ast.Constant) and n.value.value is None):
            yield i, "return", ln, "return value -> None"


def mutate(tree: ast.AST, index: int) -> str:
    t = copy.deepcopy(tree)
    for i, n in enumerate(ast.walk(t)):
        if i != index:
            continue
        if isinstance(n, ast.Compare):
            n.ops[0] = SWAP_CMP[type(n.ops[0])]()
        elif isinstance(n, (ast.BinOp, ast.AugAssign)):
            n.op = SWAP_BIN[type(n.op)]()
        elif isinstance(n, ast.BoolOp):
            n.op = ast.Or() if isinstance(n.op, ast.And) else ast.And()
        elif isinstance(n, ast.UnaryOp):
            class _Drop(ast.NodeTransformer):  # replace `not x` by `bool(x)`: removes the negation, stays valid
                def __init__(self, target):
                    self.target = target

                def visit(self, node):
                    if node is self.target:
                        return ast.Call(ast.Name("bool", ast.Load()), [node.operand], [])
                    return self.generic_visit(node)
            t = _Drop(n).visit(t)
        elif isinstance(n, ast.Constant):
            n.value = (not n.value) if isinstance(n.value, bool) else n.value + 1
        elif isinstance(n, ast.Return):
            n.value = ast.Constant(None)
        break
    return ast.unparse(ast.fix_missing_locations(t)) + "\n"


def spread(items, k):
    """Pick k items, prioritising boundary/bool mutants, spread over lines."""
    items = sorted(items, key=lambda x: (PRIORITY[x[1]], x[2]))
    if len(items) <= k:
        return items
    picked, seen_lines = [], set()
    for it in items:  # first pass: one per line
        if it[2] not in seen_lines and len(picked) < k:
            picked.append(it)
            seen_lines.add(it[2])
    for it in items:
        if len(picked) >= k:
            break
        if it not in picked:
            picked.append(it)
    return picked


def copy_tree(root: Path, dst: Path):
    files = g.git("ls-files", "-co", "--exclude-standard", cwd=root).splitlines()
    for f in files:
        s = root / f
        if s.is_file():
            d = dst / f
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)


def run_tests(cmd: str, cwd: Path, timeout: float):
    t0 = time.monotonic()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        p = subprocess.run(shlex.split(cmd), cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, time.monotonic() - t0, (p.stdout + p.stderr)[-2000:]
    except subprocess.TimeoutExpired:
        return 124, time.monotonic() - t0, "timeout"


PYTEST = re.compile(r"^(\S*python3?(?:\.\d+)?)\s+-m\s+pytest\b(.*)$")


def executed_lines(test_cmd: str, work: Path, timeout: float):
    """{path: executed line numbers} from one coverage run of the test command (v0.2), or None if unavailable."""
    m = PYTEST.match(test_cmd.strip())
    if not m:
        return None
    py, rest = m.group(1), m.group(2)
    data = work / ".gates-mut.coverage"
    cmd = f"{py} -m coverage run --data-file={data} -m pytest{rest}"
    rc, _, _ = run_tests(cmd, work, timeout)
    if not data.exists():
        return None
    out = work / ".gates-mut-cov.json"
    subprocess.run(shlex.split(f"{py} -m coverage json -q --data-file={data} -o {out}"), cwd=work,
                   capture_output=True, timeout=timeout)
    if not out.exists():
        return None
    files = json.loads(out.read_text()).get("files", {})
    res = {}
    for f, info in files.items():
        rel = os.path.relpath(f, work) if os.path.isabs(f) else f
        res[rel] = set(info.get("executed_lines", []))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=os.environ.get("BASE_REF", "origin/main"))
    a = ap.parse_args(argv)
    root = g.repo_root()
    cfg = g.config(root)
    base = g.resolve_base(a.base, cwd=root)
    native = cfg.get("GATES_MUTATION_CMD", "").strip()
    if native:
        print(f"== gates/diff-mutation: delegating to native tool: {native}")
        return subprocess.run(native, shell=True, cwd=root).returncode
    test_cmd = cfg.get("GATES_TEST_CMD", "python3 -m pytest -x -q -p no:cacheprovider")
    max_mut = int(cfg.get("GATES_MUT_MAX", "20"))
    min_mut = int(cfg.get("GATES_MUT_MIN_MUTANTS", "4"))
    min_score = float(cfg.get("GATES_MUT_MIN_SCORE", "0.6"))
    budget = float(cfg.get("GATES_MUT_BUDGET_S", "240"))
    exclude = g.cfg_list(cfg, "GATES_MUT_EXCLUDE")
    F: list[g.Finding] = []
    changed = [p for p in g.changed_files(base, cwd=root) if p.endswith(".py") and not g.is_test_path(p)
               and not any(p.startswith(x) for x in exclude) and (root / p).exists()]
    added = g.added_lines(base, cwd=root, paths=changed) if changed else {}
    pool = []
    trees = {}
    for path, lines in added.items():
        try:
            trees[path] = ast.parse((root / path).read_text())
        except SyntaxError:
            continue
        for c in candidates(trees[path], set(lines)):
            pool.append((path, *c))
    stats = {"base": base[:12], "files": len(trees), "candidates": len(pool)}
    if not pool:
        F.append(g.Finding("diff-mutation", "test-adequacy.mutation-skipped", "test-adequacy", "info",
                           "no mutable code on added lines", level="inform"))
        return g.emit("diff-mutation", F, root, None, stats)
    with tempfile.TemporaryDirectory(prefix="gates-mut-") as td:
        work = Path(td)
        copy_tree(root, work)
        rc, base_t, out = run_tests(test_cmd, work, timeout=max(60.0, budget / 2))
        stats["baseline_test_s"] = round(base_t, 2)
        if rc != 0:
            F.append(g.Finding("diff-mutation", "test-adequacy.mutation-skipped", "test-adequacy", "info",
                               f"baseline tests fail (rc={rc}); mutation not meaningful", evidence=out[-300:],
                               level="inform"))
            return g.emit("diff-mutation", F, root, None, stats)
        executed = executed_lines(test_cmd, work, max(60.0, budget / 2)) \
            if cfg.get("GATES_MUT_EXECUTED_ONLY", "1") == "1" else None
        if executed is not None:
            unexec = [p for p in pool if p[3] not in executed.get(p[0], set())]
            pool = [p for p in pool if p[3] in executed.get(p[0], set())]
            stats["unexecuted_candidates"] = len(unexec)
            if unexec:
                F.append(g.Finding("diff-mutation", "test-adequacy.unexecuted-lines", "test-adequacy", "info",
                                   f"{len({(p[0], p[3]) for p in unexec})} added line(s) are not executed by any test; "
                                   "not mutated (coverage-drop owns untested code)", level="inform"))
        chosen = []
        per_file = {}
        for p in pool:
            per_file.setdefault(p[0], []).append(p[1:])
        quota = max(1, max_mut // max(1, len(per_file)))
        for path, items in per_file.items():
            chosen += [(path, *it) for it in spread(items, quota)]
        chosen = chosen[:max_mut]
        per_timeout = max(10.0, 3 * base_t + 5)
        killed, survived, ran = 0, [], 0
        t_start = time.monotonic()
        for path, idx, kind, ln, desc in chosen:
            if time.monotonic() - t_start > budget:
                F.append(g.Finding("diff-mutation", "test-adequacy.mutation-skipped", "test-adequacy", "info",
                                   f"budget {budget:g}s exhausted after {ran} mutants", level="inform"))
                break
            target = work / path
            original = target.read_text()
            target.write_text(mutate(trees[path], idx))
            rc, _, _ = run_tests(test_cmd, work, per_timeout)
            target.write_text(original)
            ran += 1
            if rc != 0:
                killed += 1
            else:
                survived.append((path, ln, kind, desc))
        stats.update({"mutants": ran, "killed": killed, "survived": len(survived),
                      "score": round(killed / ran, 3) if ran else None,
                      "wall_s": round(time.monotonic() - t_start, 1)})
    for path, ln, kind, desc in survived:
        F.append(g.Finding("diff-mutation", "test-adequacy.surviving-mutant", "test-adequacy", "low",
                           f"mutant survived ({kind}: {desc}) — no test fails when this line changes", path, ln,
                           f"{kind}:{desc}", level=g.level_for(cfg, "test-adequacy.surviving-mutant", "inform")))
    if ran >= min_mut and killed / ran < min_score:
        F.append(g.Finding("diff-mutation", "test-adequacy.mutation-score", "test-adequacy", "high",
                           f"diff mutation score {killed}/{ran} = {killed / ran:.2f} < {min_score:g}: the tests do "
                           "not constrain the new code", evidence=f"score<{min_score}",
                           level=g.level_for(cfg, "test-adequacy.mutation-score", "block")))
    notes = g.apply_suppressions(F, root)
    return g.emit("diff-mutation", F, root, notes, stats)


if __name__ == "__main__":
    sys.exit(main())
