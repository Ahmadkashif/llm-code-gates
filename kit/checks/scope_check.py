#!/usr/bin/env python3
"""scope-check: files changed outside the declared task scope (silent scope expansion).

The scope comes from the task statement the agent was given: GATES_SCOPE (comma-separated globs) or a
`Scope:` line / `## Scope` list in GATES_TASK_FILE (default .gates/task.md). Tests of in-scope modules
(tests/test_<module>.py, <module>_test.go, <module>.test.ts) are in scope automatically.

Rules
  scope.out-of-scope-file   changed non-test file matches no scope glob (scope declared)  block
  scope.out-of-scope-test   changed TEST file outside the scope (expectations elsewhere often
                            legitimately follow a requested change; v0.2 after corpus FP A3) warn
  scope.large-change        > GATES_SCOPE_MAX_FILES files or > GATES_SCOPE_MAX_LINES lines  warn
  scope.undeclared          no scope declared (only the size heuristic ran)               inform
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import gateslib as g  # noqa: E402


def read_scope(root: Path, cfg: dict) -> list[str]:
    if cfg.get("GATES_SCOPE"):
        return g.cfg_list(cfg, "GATES_SCOPE")
    p = root / cfg.get("GATES_TASK_FILE", ".gates/task.md")
    if not p.exists():
        return []
    globs, in_list = [], False
    for line in p.read_text().splitlines():
        m = re.match(r"^\s*scope\s*:\s*(.+)$", line, re.I)
        if m:
            globs += [x.strip(" `") for x in m.group(1).split(",") if x.strip()]
            continue
        if re.match(r"^#+\s*scope\b", line, re.I):
            in_list = True
            continue
        if in_list:
            if line.startswith("#"):
                in_list = False
            elif re.match(r"^\s*[-*]\s+", line):
                globs.append(re.sub(r"^\s*[-*]\s+", "", line).split(" ")[0].strip("`"))
    return [x for x in globs if x]


def test_globs(glob: str) -> list[str]:
    stem = Path(glob).stem
    if "*" in stem:
        return []
    return [f"**/test_{stem}.py", f"**/{stem}_test.py", f"**/{stem}_test.go", f"**/{stem}.test.*", f"**/{stem}.spec.*"]


def match(path: str, globs: list[str]) -> bool:
    for gl in globs:
        if fnmatch.fnmatch(path, gl) or fnmatch.fnmatch(path, gl.rstrip("/") + "/*") or path == gl:
            return True
        if gl.startswith("**/") and fnmatch.fnmatch(path, gl[3:]):
            return True
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=os.environ.get("BASE_REF", "origin/main"))
    a = ap.parse_args(argv)
    root = g.repo_root()
    cfg = g.config(root)
    base = g.resolve_base(a.base, cwd=root)
    F = []
    changed = g.changed_files(base, cwd=root)
    scope = read_scope(root, cfg)
    always = g.cfg_list(cfg, "GATES_SCOPE_ALWAYS", ".gates/*,CHANGELOG.md")
    if scope:
        allowed = scope + always + [t for s in scope for t in test_globs(s)]
        for p in changed:
            if match(p, allowed):
                continue
            if g.is_test_path(p):
                F.append(g.Finding("scope-check", "scope.out-of-scope-test", "scope", "low",
                                   f"test file outside the declared scope {scope}: confirm the expectation change "
                                   "follows from the requested work", p, evidence=p,
                                   level=g.level_for(cfg, "scope.out-of-scope-test", "warn")))
            else:
                F.append(g.Finding("scope-check", "scope.out-of-scope-file", "scope", "medium",
                                   f"changed outside the declared scope {scope}", p, evidence=p,
                                   level=g.level_for(cfg, "scope.out-of-scope-file", "block")))
    else:
        F.append(g.Finding("scope-check", "scope.undeclared", "scope", "info",
                           "no task scope declared (GATES_SCOPE or Scope: in the task file); size heuristic only",
                           level="inform"))
    numstat = g.git("diff", "--numstat", base, cwd=root).splitlines()
    lines = sum(int(x.split()[0]) + int(x.split()[1]) for x in numstat if x.split()[0].isdigit())
    mf, ml = int(cfg.get("GATES_SCOPE_MAX_FILES", "15")), int(cfg.get("GATES_SCOPE_MAX_LINES", "600"))
    if len(changed) > mf or lines > ml:
        F.append(g.Finding("scope-check", "scope.large-change", "scope", "low",
                           f"{len(changed)} files / {lines} lines changed (limits {mf}/{ml}); split the change",
                           evidence="large", level=g.level_for(cfg, "scope.large-change", "warn")))
    notes = g.apply_suppressions(F, root)
    return g.emit("scope-check", F, root, notes, {"base": base[:12], "files": len(changed), "lines": lines,
                                                  "scope": scope})


if __name__ == "__main__":
    sys.exit(main())
