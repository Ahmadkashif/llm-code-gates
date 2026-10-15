#!/usr/bin/env python3
"""Score phase-6 results against the pre-registered labels. Smoke test, n stated; never a benchmark.

Definitions
  contract catch : a defective change set makes a contract task fail (first layer: L0 check:fast, L2 check, L3 ci)
  contract FP    : a clean change set makes any contract task fail
  gate fired     : a kit check reported >= 1 unsuppressed 'block' finding (or a repo task exited non-zero)
  gate warned    : the kit check reported only 'warn' findings
Writes results-summary.md (+ .json).
"""
import json
import os
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS = json.loads((HERE.parent / "sample-service/verification/labels.json").read_text())["changesets"]
KIT_CHECKS = ["test-tamper", "dep-check", "semgrep-changed", "semgrep", "scope-check", "licence-check", "dup-check",
              "coverage-drop", "diff-mutation", "llm-review"]
REPO = ["lint", "typecheck", "test:unit", "build", "secrets", "audit", "sast", "workflows", "test:integration"]


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    rows, per_gate = [], {g: {"fired_defect": [], "fired_clean": [], "warn_defect": [], "warn_clean": []}
                          for g in KIT_CHECKS + REPO}
    walls = {"check:fast": [], "check": [], "ci": [], "gates:fast": [], "gates:deterministic": [], "gates:server": []}
    check_walls = {g: [] for g in KIT_CHECKS}
    review_var = []
    for lab in LABELS:
        f = HERE / os.environ.get("CS_RESULTS", "results") / f"{lab['id']}.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text())
        c = r["contract"]
        first = next((name for name, t in (("L0", "check:fast"), ("L2", "check"), ("L3", "ci")) if c[t]["rc"] != 0), None)
        for t in ("check:fast", "check", "ci"):
            walls[t].append(c[t]["wall_s"])
        fired, warned = [], []
        for layer, g in r["gates"].items():
            walls[f"gates:{layer}"].append(g["wall_s"])
            for name, chk in g["checks"].items():
                check_walls[name].append(chk["wall_s"])
                blk = [x for x in chk["findings"] if x["level"] == "block" and not x["suppressed"]]
                wrn = [x for x in chk["findings"] if x["level"] == "warn" and not x["suppressed"]]
                if blk and layer == "fast" and name != "semgrep-changed":
                    continue  # the same check re-runs in 'deterministic'; count it once
                if blk:
                    fired.append(f"{name}:" + ",".join(sorted({x['rule'] for x in blk})))
                    per_gate[name]["fired_defect" if lab["label"] == "defect" else "fired_clean"].append(lab["id"])
                elif wrn:
                    warned.append(f"{name}:" + ",".join(sorted({x['rule'] for x in wrn})))
                    per_gate[name]["warn_defect" if lab["label"] == "defect" else "warn_clean"].append(lab["id"])
        for t, res in r["repo"].items():
            if res["rc"] != 0:
                fired.append(f"repo:{t}")
                per_gate[t]["fired_defect" if lab["label"] == "defect" else "fired_clean"].append(lab["id"])
        fired, warned = list(dict.fromkeys(f.replace("semgrep-changed:", "semgrep:") for f in fired)), \
            list(dict.fromkeys(w.replace("semgrep-changed:", "semgrep:") for w in warned))
        warned = [w for w in warned if w.split(":")[0] not in {f.split(":")[0] for f in fired}]
        llm = [sorted({x["fingerprint"] for x in rv["findings"]}) for rv in r["review"]]
        review_var.append(len({json.dumps(x) for x in llm}) == 1)
        llm_warn = sorted({x["rule"] for rv in r["review"] for x in rv["findings"] if x["level"] in ("warn", "block")})
        rows.append({"id": lab["id"], "label": lab["label"], "category": lab["category"],
                     "expected": lab["expected_catch"], "blocked_at": first,
                     "contract_rc": {t: c[t]["rc"] for t in c}, "fired": fired, "warned": warned,
                     "llm_stub_warn": llm_warn, "llm_repeats_identical": review_var[-1],
                     "wall": {t: c[t]["wall_s"] for t in c}})
    defects = [r for r in rows if r["label"] == "defect"]
    cleans = [r for r in rows if r["label"] == "clean"]
    caught = [r for r in defects if r["blocked_at"]]
    fps = [r for r in cleans if r["blocked_at"]]
    out = ["# Phase 6 — corpus results (smoke test, n = %d change sets: %d defective, %d clean)\n" %
           (len(rows), len(defects), len(cleans)),
           "Labels pre-registered in `sample-service/verification/labels.json` (committed before any gate ran).",
           "Machine: 16-core workstation, niced, no GPU; LLM review = stub judge (pipeline only, NOT a model).\n",
           "## Contract outcome (what an agent / developer / CI would experience)\n",
           f"- defective change sets blocked by some contract task: **{len(caught)}/{len(defects)}**"
           f" (Wilson 95% CI {wilson(len(caught), len(defects))[0]:.2f}–{wilson(len(caught), len(defects))[1]:.2f})",
           f"  - first blocked at L0 `check:fast`: {sum(r['blocked_at'] == 'L0' for r in defects)}, "
           f"L2 `check`: {sum(r['blocked_at'] == 'L2' for r in defects)}, L3 `ci`: {sum(r['blocked_at'] == 'L3' for r in defects)}",
           f"  - missed: {', '.join(r['id'] + ' (' + r['category'] + ')' for r in defects if not r['blocked_at']) or 'none'}",
           f"- clean change sets blocked (false positives): **{len(fps)}/{len(cleans)}**"
           f" (Wilson 95% CI {wilson(len(fps), len(cleans))[0]:.2f}–{wilson(len(fps), len(cleans))[1]:.2f})"
           + (f": {', '.join(r['id'] + ' by ' + '; '.join(r['fired']) for r in fps)}" if fps else ""), "",
           "## Per change set\n",
           "| id | label | category | blocked at | blocking gates (kit check:rules / repo task) | warn-only | LLM stub (advisory) | expected |",
           "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['id']} | {r['label']} | {r['category']} | {r['blocked_at'] or '—'} | "
                   f"{'<br>'.join(r['fired']) or '—'} | {'<br>'.join(r['warned']) or '—'} | "
                   f"{', '.join(r['llm_stub_warn']) or '—'} | {r['expected']} |")
    out += ["", "## Per gate (fired = blocking finding / non-zero exit)\n",
            "| gate | fired on defective | fired on clean (FP) | warn on defective | warn on clean |", "|---|---|---|---|---|"]
    for g, v in per_gate.items():
        if any(v.values()):
            out.append(f"| {g} | {len(v['fired_defect'])} {v['fired_defect']} | {len(v['fired_clean'])} {v['fired_clean']} | "
                       f"{len(v['warn_defect'])} | {len(v['warn_clean'])} {v['warn_clean'] if v['warn_clean'] else ''} |")
    out += ["", "## Wall time (seconds; smoke test on one machine, niced, sequential)\n",
            "| task | n | median | max | budget |", "|---|---|---|---|---|"]
    budget = {"check:fast": 60, "check": 120, "ci": 600, "gates:fast": 60, "gates:deterministic": 120, "gates:server": 600}
    for t, ws in walls.items():
        if ws:
            out.append(f"| `{t}` | {len(ws)} | {st.median(ws):.1f} | {max(ws):.1f} | < {budget[t]} {'OK' if max(ws) < budget[t] else 'OVER'} |")
    out += ["", "| kit check | median | max |", "|---|---|---|"]
    for g, ws in check_walls.items():
        if ws:
            out.append(f"| {g} | {st.median(ws):.2f} | {max(ws):.2f} |")
    out += ["", f"LLM review (stub) repeats identical across 3 runs: {sum(review_var)}/{len(review_var)} change sets "
            "(the stub is deterministic; the nonce and reply wrapping vary per run, so this exercises parser stability)."]
    tag = os.environ.get("CS_TAG", "")
    (HERE / f"results-summary{tag}.md").write_text("\n".join(out) + "\n")
    (HERE / f"results-summary{tag}.json").write_text(json.dumps({"rows": rows, "per_gate": per_gate,
                                                            "walls": walls}, indent=1))
    print("\n".join(out[:12]))


if __name__ == "__main__":
    main()
