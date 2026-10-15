#!/usr/bin/env python3
"""coverage-drop: total line coverage must not fall vs BASE_REF; added lines should be exercised.

Runs GATES_COVERAGE_CMD (must write coverage.py JSON to $GATES_COV_JSON) twice: in the working tree and in a
`git archive` export of BASE (no .git changes, no worktree). GATES_COVERAGE_MODE=baseline compares with the
committed .gates/coverage-baseline.json instead (cheaper; refresh it on main).

Rules
  test-adequacy.coverage-drop   total % fell by more than GATES_COV_MAX_DROP points          block
  test-adequacy.diff-coverage   < GATES_DIFF_COV_MIN of executable added lines are executed  warn
  test-adequacy.coverage-error  coverage could not be measured                               warn
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import gateslib as g  # noqa: E402

DEFAULT_CMD = ("python3 -m coverage run --branch -m pytest -q -p no:cacheprovider && "
               "python3 -m coverage json -q -o \"$GATES_COV_JSON\"")


def measure(cmd: str, cwd: Path, out_json: Path, timeout: float):
    env = {**os.environ, "GATES_COV_JSON": str(out_json), "PYTHONDONTWRITEBYTECODE": "1",
           "COVERAGE_FILE": str(out_json.with_suffix(".data"))}
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    if not out_json.exists():
        return None, (p.stdout + p.stderr)[-500:]
    return json.loads(out_json.read_text()), (p.stdout + p.stderr)[-500:] if p.returncode else ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=os.environ.get("BASE_REF", "origin/main"))
    ap.add_argument("--write-baseline", action="store_true",
                    help="measure HEAD and write .gates/coverage-baseline.json")
    a = ap.parse_args(argv)
    root = g.repo_root()
    cfg = g.config(root)
    cmd = cfg.get("GATES_COVERAGE_CMD", DEFAULT_CMD)
    timeout = float(cfg.get("GATES_COV_TIMEOUT_S", "300"))
    max_drop = float(cfg.get("GATES_COV_MAX_DROP", "0.5"))
    diff_min = float(cfg.get("GATES_DIFF_COV_MIN", "0.7"))
    od = g.out_dir(root)
    F: list[g.Finding] = []
    head, err = measure(cmd, root, od / "coverage-head.json", timeout)
    if head is None:
        F.append(g.Finding("coverage-drop", "test-adequacy.coverage-error", "test-adequacy", "medium",
                           "could not measure coverage at HEAD", evidence=err, level="warn"))
        return g.emit("coverage-drop", F, root)
    head_pct = head["totals"]["percent_covered"]
    if a.write_baseline:
        (root / ".gates" / "coverage-baseline.json").write_text(json.dumps({"percent_covered": head_pct}) + "\n")
        print(f"wrote baseline {head_pct:.2f}%")
        return 0
    base = g.resolve_base(a.base, cwd=root)
    if cfg.get("GATES_COVERAGE_MODE", "base") == "baseline":
        bp = root / ".gates" / "coverage-baseline.json"
        base_pct = json.loads(bp.read_text())["percent_covered"] if bp.exists() else None
    else:
        with tempfile.TemporaryDirectory(prefix="gates-cov-") as td:
            tar = subprocess.run(["git", "archive", "--format=tar", base], cwd=root, capture_output=True, check=True)
            with tarfile.open(fileobj=io.BytesIO(tar.stdout)) as tf:
                tf.extractall(td, filter="data")
            bjson, berr = measure(cmd, Path(td), Path(td) / ".gates-cov-base.json", timeout)
            base_pct = bjson["totals"]["percent_covered"] if bjson else None
            if bjson is None:
                F.append(g.Finding("coverage-drop", "test-adequacy.coverage-error", "test-adequacy", "low",
                                   "could not measure coverage at BASE; only diff coverage checked", evidence=berr,
                                   level="inform"))
    stats = {"base": base[:12], "head_pct": round(head_pct, 2),
             "base_pct": round(base_pct, 2) if base_pct is not None else None}
    if base_pct is not None and base_pct - head_pct > max_drop:
        F.append(g.Finding("coverage-drop", "test-adequacy.coverage-drop", "test-adequacy", "high",
                           f"total coverage fell {base_pct:.2f}% -> {head_pct:.2f}% (max drop {max_drop:g} pts)",
                           evidence="coverage-drop", level=g.level_for(cfg, "test-adequacy.coverage-drop", "block")))
    # diff coverage over added executable lines
    files = head.get("files", {})
    added = g.added_lines(base, cwd=root, paths=[p for p in g.changed_files(base, cwd=root)
                                                 if p.endswith(".py") and not g.is_test_path(p)])
    hit = miss = 0
    missed_at = []
    for path, lines in added.items():
        info = files.get(path)
        if not info:
            continue
        ex, mi = set(info.get("executed_lines", [])), set(info.get("missing_lines", []))
        for ln in lines:
            if ln in ex:
                hit += 1
            elif ln in mi:
                miss += 1
                missed_at.append(f"{path}:{ln}")
    if hit + miss:
        ratio = hit / (hit + miss)
        stats["diff_cov"] = round(ratio, 3)
        if ratio < diff_min:
            F.append(g.Finding("coverage-drop", "test-adequacy.diff-coverage", "test-adequacy", "medium",
                               f"only {hit}/{hit + miss} executable added lines run under tests ({ratio:.0%} < "
                               f"{diff_min:.0%})", evidence=", ".join(missed_at[:12]),
                               level=g.level_for(cfg, "test-adequacy.diff-coverage", "warn")))
    notes = g.apply_suppressions(F, root)
    return g.emit("coverage-drop", F, root, notes, stats)


if __name__ == "__main__":
    sys.exit(main())
