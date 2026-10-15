#!/usr/bin/env python3
"""Run one gate layer: every check configured for it, all of them (no fail-fast), with per-check wall time.

Usage: python3 gates/run.py <fast|deterministic|server|CHECK...> [--base REF]
Writes .gates/out/summary-<layer>.json and a merged .gates/out/gates-<layer>.sarif; exit 1 if any check failed.
llm-review only fails when its judge profile promoted a category to blocking (default: never).
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT / "lib"))
import gateslib as g  # noqa: E402

PY = sys.executable or "python3"
CHECKS = {
    "test-tamper": [PY, str(KIT / "checks/test_tamper.py")],
    "dep-check": [PY, str(KIT / "checks/dep_check.py")],
    "semgrep-changed": [PY, str(KIT / "checks/semgrep_gate.py"), "--changed"],
    "semgrep": [PY, str(KIT / "checks/semgrep_gate.py")],
    "scope-check": [PY, str(KIT / "checks/scope_check.py")],
    "licence-check": [PY, str(KIT / "checks/licence_check.py")],
    "dup-check": [PY, str(KIT / "checks/dup_check.py")],
    "coverage-drop": [PY, str(KIT / "checks/coverage_drop.py")],
    "diff-mutation": [PY, str(KIT / "checks/diff_mutation.py")],
    "llm-review": [PY, str(KIT / "review/llm_review.py")],
}
HEAVY = {"coverage-drop", "diff-mutation"}
DEFAULT_LAYERS = {
    "fast": ["test-tamper", "dep-check", "semgrep-changed", "scope-check"],
    "deterministic": ["test-tamper", "dep-check", "semgrep", "scope-check", "licence-check", "dup-check",
                      "coverage-drop"],
    "server": ["diff-mutation", "llm-review"],
}
SARIF_NAME = {"semgrep-changed": "semgrep"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("what", nargs="+")
    ap.add_argument("--base", default=os.environ.get("BASE_REF", "origin/main"))
    a = ap.parse_args(argv)
    root = g.repo_root()
    cfg = g.config(root)
    if not (root / ".gates" / "config.env").exists():
        g.die("no .gates/config.env — run: python3 gates/render.py --stack <stack> --judge <judge>")
    layer = a.what[0] if len(a.what) == 1 and a.what[0] in DEFAULT_LAYERS else "custom"
    names = g.cfg_list(cfg, f"GATES_LAYER_{layer.upper()}") if layer != "custom" else a.what
    names = names or DEFAULT_LAYERS.get(layer, [])
    nice = cfg.get("GATES_NICE", "1") == "1"
    env = {**os.environ, **{k: v for k, v in cfg.items()}, "BASE_REF": a.base}
    results, t0 = [], time.monotonic()
    for n in names:
        if n not in CHECKS:
            g.die(f"unknown check '{n}' (known: {', '.join(CHECKS)})")
        cmd = CHECKS[n] + ["--base", a.base]
        if nice and n in HEAVY:
            cmd = ["nice", "-n", "19"] + cmd
        print(f"\n--- gates:{layer} -> {n}: {' '.join(shlex.quote(c) for c in cmd[-3:])}", flush=True)
        t = time.monotonic()
        rc = subprocess.run(cmd, cwd=root, env=env).returncode
        results.append({"check": n, "rc": rc, "wall_s": round(time.monotonic() - t, 2)})
    total = round(time.monotonic() - t0, 2)
    od = g.out_dir(root)
    runs = []
    for r in results:
        f = od / f"{SARIF_NAME.get(r['check'], r['check'])}.sarif"
        if f.exists():
            runs += json.loads(f.read_text())["runs"]
    (od / f"gates-{layer}.sarif").write_text(json.dumps({"version": "2.1.0", "$schema":
                                                         "https://json.schemastore.org/sarif-2.1.0.json",
                                                         "runs": runs}, indent=1))
    failed = [r["check"] for r in results if r["rc"] != 0]
    summary = {"layer": layer, "base": a.base, "wall_s": total, "checks": results, "failed": failed}
    (od / f"summary-{layer}.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"\n=== gates:{layer} {'FAILED: ' + ', '.join(failed) if failed else 'passed'} in {total}s "
          + " ".join(f"[{r['check']} {r['wall_s']}s rc={r['rc']}]" for r in results))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
