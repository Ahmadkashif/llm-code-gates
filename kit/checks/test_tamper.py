#!/usr/bin/env python3
"""test-tamper: did this change make the tests easier to pass? Compares test code at BASE_REF with the working tree.

Rules (default level)
  test-integrity.test-file-deleted     test file removed without a rename                           block
  test-integrity.test-removed          test function removed (not moved, its target code still exists) block
  test-integrity.test-removed-with-code test removed together with the code it exercised             inform
  test-integrity.assertions-removed    a surviving test has fewer assertions than before             block
  test-integrity.assertion-weakened    strong assertions (==, in, raises, assertEqual...) replaced
                                       by weak ones (is not None, isinstance, bare truthiness)        block
  test-integrity.tautology             assert True / assert x == x / assertTrue(True) added          block
  test-integrity.test-skipped          skip/xfail marker or skip call added                          block
  test-integrity.expectation-changed   expected literal in an assertion changed                      warn
  test-integrity.test-config-weakened  --deselect/--ignore/-k not/omit/fail_under lowered in config   block
Python is analysed with `ast`; JS/TS/Go test files with per-file counts (declarations, assertions, skips).
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import gateslib as g  # noqa: E402

STRONG_METHODS = {"assertEqual", "assertEquals", "assertNotEqual", "assertIn", "assertNotIn", "assertRaises",
                  "assertRaisesRegex", "assertAlmostEqual", "assertCountEqual", "assertDictEqual", "assertListEqual",
                  "assertGreater", "assertLess", "assertGreaterEqual", "assertLessEqual", "assertRegex",
                  "assertIs", "assertIsNot", "assertSetEqual", "assertTupleEqual", "assertMultiLineEqual"}
WEAK_METHODS = {"assertTrue", "assertFalse", "assertIsNotNone", "assertIsNone", "assertIsInstance"}
CONFIG_FILES = ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini", ".coveragerc", "conftest.py",
                "vitest.config.ts", "vitest.config.js", "jest.config.js", "jest.config.ts", "package.json")
CONFIG_WEAKEN = re.compile(r"--deselect|--ignore\b|--ignore-glob|-k\s+['\"]?not\b|\bomit\s*=|testPathIgnorePatterns|"
                           r"coveragePathIgnorePatterns|collect_ignore|pytest\.skip\(|"
                           r"--passWithNoTests|addopts.*-p\s+no:")


# ------------------------------------------------------------------------------------------- python analysis
class TestInfo:
    def __init__(self, name, node):
        self.name = name
        self.lineno = node.lineno
        self.strong = []
        self.weak = []
        self.tautologies = []
        self.skips = 0
        self.expected = []  # literal right-hand sides of == comparisons
        self.refs = set()
        self.rows = 1  # pytest.mark.parametrize cases (v0.2: a table-driven refactor keeps its assertion count)
        for d in getattr(node, "decorator_list", []):
            if isinstance(d, ast.Call) and ast.unparse(d.func).endswith("parametrize") and len(d.args) >= 2 \
                    and isinstance(d.args[1], (ast.List, ast.Tuple)):
                self.rows *= max(1, len(d.args[1].elts))
            src = ast.unparse(d)
            if re.search(r"\b(skip|skipif|xfail|skipIf|skipUnless|expectedFailure)\b", src):
                self.skips += 1
        for n in ast.walk(node):
            if isinstance(n, ast.Name):
                self.refs.add(n.id)
            elif isinstance(n, ast.Attribute):
                self.refs.add(n.attr)
            if isinstance(n, ast.Assert):
                self._classify_assert(n.test)
            elif isinstance(n, ast.Call):
                fn = n.func
                fname = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""
                full = ast.unparse(fn)
                if fname in STRONG_METHODS:
                    self.strong.append(ast.unparse(n))
                    if fname in ("assertEqual", "assertEquals") and len(n.args) >= 2:
                        if all(isinstance(a, ast.Constant) for a in n.args[:2]) and \
                                n.args[0].value == n.args[1].value:
                            self.tautologies.append(ast.unparse(n))
                        for a in n.args[:2]:
                            if isinstance(a, ast.Constant):
                                self.expected.append(repr(a.value))
                elif fname in WEAK_METHODS:
                    if fname == "assertTrue" and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value:
                        self.tautologies.append(ast.unparse(n))
                    else:
                        self.weak.append(ast.unparse(n))
                elif full in ("pytest.raises", "raises") or fname in ("raises",):
                    self.strong.append(ast.unparse(n))
                elif full in ("pytest.skip", "self.skipTest", "pytest.xfail") or fname in ("skipTest",):
                    self.skips += 1
                elif re.match(r"assert_(called|any_call|has_calls|not_called)", fname):
                    self.strong.append(ast.unparse(n))

    def _classify_assert(self, t):
        src = ast.unparse(t)
        if isinstance(t, ast.Constant):
            (self.tautologies if t.value else self.strong).append(f"assert {src}")
            return
        if isinstance(t, ast.Compare):
            ops = t.ops
            left, right = t.left, t.comparators[-1]
            if len(ops) == 1 and isinstance(ops[0], (ast.Eq, ast.Is, ast.GtE, ast.LtE)) \
                    and ast.unparse(left) == ast.unparse(right):
                self.tautologies.append(f"assert {src}")
                return
            if len(ops) == 1 and isinstance(ops[0], ast.IsNot) and isinstance(right, ast.Constant) \
                    and right.value is None:
                self.weak.append(f"assert {src}")
                return
            if isinstance(ops[0], ast.Eq):
                for side in (left, right):
                    if isinstance(side, ast.Constant):
                        self.expected.append(repr(side.value))
            self.strong.append(f"assert {src}")
            return
        if isinstance(t, ast.Call) and isinstance(t.func, ast.Name) and t.func.id in ("isinstance", "callable",
                                                                                        "hasattr", "bool", "len"):
            self.weak.append(f"assert {src}")
            return
        if isinstance(t, (ast.Name, ast.Attribute)):
            self.weak.append(f"assert {src}")
            return
        self.strong.append(f"assert {src}")

    @property
    def n_asserts(self):
        """Effective assertion count: textual assertions x parametrize rows."""
        return (len(self.strong) + len(self.weak) + len(self.tautologies)) * self.rows

    @property
    def n_strong(self):
        return len(self.strong) * self.rows

    @property
    def n_weak(self):
        return (len(self.weak) + len(self.tautologies)) * self.rows


def py_tests(text: str | None) -> dict[str, TestInfo] | None:
    if text is None:
        return None
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    out = {}

    def visit(body, prefix=""):
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
                out[prefix + n.name] = TestInfo(prefix + n.name, n)
            elif isinstance(n, ast.ClassDef):
                cls_skip = any(re.search(r"\bskip", ast.unparse(d)) for d in n.decorator_list)
                before = set(out)
                visit(n.body, prefix + n.name + ".")
                if cls_skip:
                    for k in set(out) - before:
                        out[k].skips += 1
    visit(tree.body)
    return out


def defined_names(text: str | None) -> set[str]:
    if not text:
        return set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


# ------------------------------------------------------------------------------------------- other languages
JS_DECL = re.compile(r"\b(it|test)\s*(\.\w+)?\s*\(")
JS_ASSERT = re.compile(r"\bexpect\s*\(|\bassert[.(]")
JS_SKIP = re.compile(r"\b(it|test|describe)\.(skip|todo)\s*\(|\bx(it|describe|test)\s*\(")
GO_DECL = re.compile(r"^func\s+Test\w+\s*\(", re.M)
GO_ASSERT = re.compile(r"\bt\.(Error|Errorf|Fatal|Fatalf|Fail|FailNow)\b|\b(assert|require)\.\w+\(")
GO_SKIP = re.compile(r"\bt\.(Skip|Skipf|SkipNow)\b")


def counts(path: str, text: str | None):
    if text is None:
        return None
    if path.endswith(".go"):
        return len(GO_DECL.findall(text)), len(GO_ASSERT.findall(text)), len(GO_SKIP.findall(text))
    return (len([m for m in JS_DECL.finditer(text) if m.group(2) not in (".skip", ".todo")]),
            len(JS_ASSERT.findall(text)), len(JS_SKIP.findall(text)))


# ------------------------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=os.environ.get("BASE_REF", "origin/main"))
    a = ap.parse_args(argv)
    root = g.repo_root()
    cfg = g.config(root)
    base = g.resolve_base(a.base, cwd=root)
    F = []

    def add(rule, sev, msg, path, line=0, evidence="", default="block"):
        F.append(g.Finding("test-tamper", rule, "test-integrity", sev, msg, path, line, evidence,
                           level=g.level_for(cfg, rule, default)))

    status = g.git("diff", "-M", "--name-status", base, cwd=root).splitlines()
    renamed_from = {}
    deleted = []
    for line in status:
        parts = line.split("\t")
        if parts[0].startswith("R") and len(parts) == 3:
            renamed_from[parts[1]] = parts[2]
        elif parts[0] == "D":
            deleted.append(parts[1])
    changed = g.changed_files(base, cwd=root)
    test_paths = [p for p in changed if g.is_test_path(p) and re.search(r"\.(py|[cm]?[jt]sx?|go)$", p)]
    test_paths += [old for old in renamed_from if g.is_test_path(old)]
    # names defined in non-test code that this change deleted (tests removed with their code are OK)
    removed_code_names = set()
    for p in changed + deleted:
        if p.endswith(".py") and not g.is_test_path(p):
            removed_code_names |= defined_names(g.file_at(base, p, cwd=root)) - defined_names(g.file_at(None, p, cwd=root))
    now_all_tests: dict[str, str] = {}
    for p in g.repo_files(cwd=root):
        if p.endswith(".py") and g.is_test_path(p):
            for name in (py_tests(g.file_at(None, p, cwd=root)) or {}):
                now_all_tests.setdefault(name.split(".")[-1], p)

    for path in sorted(set(test_paths)):
        old_path, new_path = path, renamed_from.get(path, path)
        old_text = g.file_at(base, old_path, cwd=root)
        new_text = g.file_at(None, new_path, cwd=root)
        if old_text is None:
            # new test file: only tautologies / skips are interesting
            if path.endswith(".py"):
                for name, t in (py_tests(new_text) or {}).items():
                    for x in t.tautologies:
                        add("test-integrity.tautology", "high", f"tautological assertion in new test {name}", path,
                            t.lineno, x)
            continue
        if new_text is None:
            add("test-integrity.test-file-deleted", "high", "test file deleted", path, 0, path)
            continue
        if path.endswith(".py"):
            before, after = py_tests(old_text), py_tests(new_text)
            if before is None or after is None:
                continue
            total_before = sum(t.n_asserts for t in before.values())
            total_after = sum(t.n_asserts for t in after.values())
            for name, t in before.items():
                if name not in after:
                    short = name.split(".")[-1]
                    if short in now_all_tests and now_all_tests[short] != path:
                        continue  # moved to another file
                    if t.refs & removed_code_names:
                        add("test-integrity.test-removed-with-code", "info",
                            f"test {name} removed together with code it referenced "
                            f"({', '.join(sorted(t.refs & removed_code_names))})", path, 0, name, "inform")
                    elif total_after >= total_before and len(after) > len(before) - 1:
                        add("test-integrity.test-removed", "low",
                            f"test {name} removed but file assertions did not drop ({total_before}->{total_after}); "
                            "looks like a restructure", path, 0, name, "warn")
                    else:
                        add("test-integrity.test-removed", "high", f"test {name} removed ({t.n_asserts} assertion(s))",
                            path, 0, name)
                    continue
                n = after[name]
                if n.skips > t.skips:
                    add("test-integrity.test-skipped", "high", f"test {name} is now skipped/xfail", path, n.lineno, name)
                if n.n_asserts < t.n_asserts:
                    add("test-integrity.assertions-removed", "high",
                        f"test {name}: assertions {t.n_asserts} -> {n.n_asserts}", path, n.lineno,
                        "; ".join(sorted(set(t.strong + t.weak) - set(n.strong + n.weak)))[:300])
                elif n.n_strong < t.n_strong and n.n_weak > t.n_weak:
                    add("test-integrity.assertion-weakened", "high",
                        f"test {name}: strong assertions {len(t.strong)} -> {len(n.strong)}, weak "
                        f"{len(t.weak)} -> {len(n.weak)}", path, n.lineno,
                        "; ".join(sorted(set(n.weak + n.tautologies) - set(t.weak + t.tautologies)))[:300])
                for x in set(n.tautologies) - set(t.tautologies):
                    add("test-integrity.tautology", "high", f"tautological assertion added in {name}", path,
                        n.lineno, x)
                if n.n_asserts == t.n_asserts and sorted(n.expected) != sorted(t.expected) and n.expected:
                    add("test-integrity.expectation-changed", "medium",
                        f"test {name}: expected values changed {sorted(set(t.expected) - set(n.expected))} -> "
                        f"{sorted(set(n.expected) - set(t.expected))}; confirm the behaviour change was requested",
                        path, n.lineno, name, "warn")
            for name, n in after.items():
                if name not in before and n.skips:
                    add("test-integrity.test-skipped", "medium", f"new test {name} is skipped", path, n.lineno, name)
        else:
            cb, ca = counts(path, old_text), counts(path, new_text)
            if ca[0] < cb[0]:
                add("test-integrity.test-removed", "high", f"test declarations {cb[0]} -> {ca[0]}", path)
            if ca[1] < cb[1]:
                add("test-integrity.assertions-removed", "high", f"assertions {cb[1]} -> {ca[1]}", path)
            if ca[2] > cb[2]:
                add("test-integrity.test-skipped", "high", f"skips {cb[2]} -> {ca[2]}", path)

    # test configuration that hides tests or lowers thresholds
    added = g.added_lines(base, cwd=root, paths=[p for p in changed if p.rsplit("/", 1)[-1] in CONFIG_FILES])
    for path, lines in added.items():
        for ln, text in lines.items():
            if CONFIG_WEAKEN.search(text):
                add("test-integrity.test-config-weakened", "high", "test/coverage configuration now excludes or "
                    "deselects tests", path, ln, text.strip())
            m = re.search(r"fail_under\s*=\s*([\d.]+)", text)
            if m:
                old = re.search(r"fail_under\s*=\s*([\d.]+)", g.file_at(base, path, cwd=root) or "")
                if old and float(m.group(1)) < float(old.group(1)):
                    add("test-integrity.test-config-weakened", "high",
                        f"coverage fail_under lowered {old.group(1)} -> {m.group(1)}", path, ln, text.strip())
    notes = g.apply_suppressions(F, root)
    return g.emit("test-tamper", F, root, notes, {"base": base[:12], "test_files_compared": len(set(test_paths))})


if __name__ == "__main__":
    sys.exit(main())
