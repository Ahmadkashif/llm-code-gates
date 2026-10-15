#!/usr/bin/env python3
"""Run every pre-registered change set through the contract tasks and through each gate individually.

For each cs/<id>: a fresh git worktree, then (all with BASE_REF=main, SKIP_IMAGE=1, niced):
  contract : task check:fast ; task check ; task ci                       -> rc + wall (what a developer/agent sees)
  per gate : task gates:fast ; task gates:deterministic ; task gates:server -> per-check rc/wall + findings
  repo     : lint, typecheck, test:unit, build, secrets, audit, sast, workflows, test:integration -> rc + wall
  review   : gates/review/llm_review.py with the stub judge, 3 repeats    -> findings per repeat
Writes phase-6/results/<id>.json and logs/<id>/*.log. Read-only w.r.t. labels (scored by score_corpus.py).
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SAMPLE = ROOT / "sample-service"
WT = HERE / "wt"
PREFIX = os.environ.get("CS_PREFIX", "cs")
RES = HERE / os.environ.get("CS_RESULTS", "results")
LOGS = HERE / os.environ.get("CS_LOGS", "logs")
ENV = {**os.environ, "PATH": f"{ROOT/'tools/bin'}:{ROOT/'tools/venv/bin'}:{os.environ['PATH']}",
       "SKIP_IMAGE": "1", "BASE_REF": "main", "PYTHONDONTWRITEBYTECODE": "1"}
REPO_TASKS = ["lint", "typecheck", "test:unit", "build", "secrets", "audit", "sast", "workflows", "test:integration"]


def sh(cmd, cwd, log, timeout=900):
    t = time.monotonic()
    with open(log, "w") as fh:
        try:
            rc = subprocess.run(["nice", "-n", "10", *cmd], cwd=cwd, env=ENV, stdout=fh, stderr=subprocess.STDOUT,
                                timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    return rc, round(time.monotonic() - t, 2)


def findings(out: Path, check: str):
    f = out / f"{check}.jsonl"
    if not f.exists():
        return []
    res = []
    for line in f.read_text().splitlines():
        e = json.loads(line)
        if e.get("event") == "finding":
            res.append({k: e[k] for k in ("rule", "category", "level", "severity", "path", "line", "suppressed",
                                          "fingerprint")})
    return res


def run_one(cid):
    wt = WT / cid
    if wt.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=SAMPLE)
        shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(["git", "worktree", "add", "-q", "--detach", str(wt), f"{PREFIX}/{cid}"], cwd=SAMPLE, check=True)
    logs = LOGS / cid
    logs.mkdir(parents=True, exist_ok=True)
    out = wt / ".gates" / "out"
    r = {"id": cid, "contract": {}, "gates": {}, "repo": {}, "review": []}
    for t in ("check:fast", "check", "ci"):
        rc, w = sh(["task", t, "BASE_REF=main"], wt, logs / f"contract-{t.replace(':', '_')}.log")
        r["contract"][t] = {"rc": rc, "wall_s": w}
    for layer in ("fast", "deterministic", "server"):
        rc, w = sh(["task", f"gates:{layer}", "BASE_REF=main"], wt, logs / f"gates-{layer}.log")
        summ = json.loads((out / f"summary-{layer}.json").read_text()) if (out / f"summary-{layer}.json").exists() else {}
        checks = {}
        for c in summ.get("checks", []):
            name = "semgrep" if c["check"] == "semgrep-changed" else c["check"]
            checks[c["check"]] = {"rc": c["rc"], "wall_s": c["wall_s"], "findings": findings(out, name)}
        r["gates"][layer] = {"rc": rc, "wall_s": w, "checks": checks}
    for t in REPO_TASKS:
        rc, w = sh(["task", t, "BASE_REF=main"], wt, logs / f"repo-{t.replace(':', '_')}.log")
        r["repo"][t] = {"rc": rc, "wall_s": w}
    for i in range(3):
        rc, w = sh(["python3", "gates/review/llm_review.py", "--base", "main"], wt, logs / f"review-stub-{i}.log")
        ev = [json.loads(x) for x in (out / "llm-review.events.jsonl").read_text().splitlines()]
        r["review"].append({"rc": rc, "wall_s": w, "findings": findings(out, "llm-review"),
                            "calls": sum(1 for e in ev if e.get("event") == "call"),
                            "decisions": [e.get("stage") for e in ev if e.get("event") == "decision"]})
    subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=SAMPLE)
    (RES / f"{cid}.json").write_text(json.dumps(r, indent=1))
    return r


def main():
    RES.mkdir(exist_ok=True)
    ids = sys.argv[1:] or [c["id"] for c in json.loads((SAMPLE / "verification/labels.json").read_text())["changesets"]]
    for cid in ids:
        t = time.monotonic()
        r = run_one(cid)
        print(cid, {k: v["rc"] for k, v in r["contract"].items()}, f"{time.monotonic() - t:.0f}s", flush=True)


if __name__ == "__main__":
    main()
