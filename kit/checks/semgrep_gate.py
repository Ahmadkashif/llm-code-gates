#!/usr/bin/env python3
"""semgrep-gate: run the kit's VENDORED Semgrep rules (no registry fetch, --metrics=off) and report findings
in the kit format. --changed scans only files changed vs BASE_REF (L0); default scans the repo (L2).
Only findings on ADDED lines block (diff-aware, like a new-code baseline); pre-existing ones are inform.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import gateslib as g  # noqa: E402

SEV = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=os.environ.get("BASE_REF", "origin/main"))
    ap.add_argument("--changed", action="store_true")
    a = ap.parse_args(argv)
    root = g.repo_root()
    cfg = g.config(root)
    base = g.resolve_base(a.base, cwd=root)
    kit_rel = os.path.relpath(g.KIT_DIR, root)
    rules = [str(g.KIT_DIR / "semgrep")] + g.cfg_list(cfg, "GATES_SEMGREP_EXTRA_CONFIGS")
    exe = cfg.get("GATES_SEMGREP", shutil.which("semgrep") or "semgrep")
    if a.changed:
        targets = [p for p in g.changed_files(base, cwd=root) if (root / p).is_file()
                   and not p.startswith(kit_rel + "/") and p.endswith((".py", ".ts", ".tsx", ".js", ".go"))]
        if not targets:
            return g.emit("semgrep", [], root, ["no changed source files"], {"base": base[:12]})
    else:
        targets = ["."]
    cmd = [exe, "scan", "--metrics=off", "--json", "--quiet", "--disable-version-check",
           "--exclude", kit_rel, "--exclude", ".gates"]
    for c in rules:
        cmd += ["--config", c]
    p = subprocess.run(cmd + targets, cwd=root, capture_output=True, text=True)
    try:
        data = json.loads(p.stdout)
    except json.JSONDecodeError:
        print(p.stdout[-2000:], p.stderr[-2000:], sep="\n", file=sys.stderr)
        g.die(f"semgrep did not produce JSON (rc={p.returncode})")
    added = g.added_lines(base, cwd=root)
    F = []
    for r in data.get("results", []):
        meta = r.get("extra", {}).get("metadata", {})
        cid = r["check_id"]  # semgrep prefixes the config directory, e.g. "gates.semgrep.gates.py.eval-exec"
        rule = cid[cid.rfind("gates.py."):] if "gates.py." in cid else cid
        path, line = r["path"], r["start"]["line"]
        span = range(line, r["end"]["line"] + 1)
        new = any(ln in added.get(path, {}) for ln in span)
        default = "block" if r["extra"].get("severity") == "ERROR" else "warn"
        F.append(g.Finding("semgrep", rule, meta.get("category", "security"),
                           meta.get("gates_severity", SEV.get(r["extra"].get("severity"), "medium")),
                           r["extra"]["message"].strip(), path, line, r["extra"].get("lines", "").strip()[:200],
                           level=g.level_for(cfg, rule, default) if new else "inform"))
    notes = g.apply_suppressions(F, root)
    if data.get("errors"):
        notes.append(f"semgrep reported {len(data['errors'])} error(s) (parse failures are not findings)")
    return g.emit("semgrep", F, root, notes, {"base": base[:12], "targets": len(targets),
                                               "rules": len({r['check_id'] for r in data.get('results', [])})})


if __name__ == "__main__":
    sys.exit(main())
