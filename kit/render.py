#!/usr/bin/env python3
"""Render the kit's configuration for one stack profile and one judge profile, and check budgets.

Usage:  python3 gates/render.py --stack python --judge stub [--site .gates/site.env] [--out .gates]
        python3 gates/render.py --check            # validate every profile, prompt, schema and the Taskfile; write nothing
Follows the self-hosted-cicd render.py pattern: stdlib only, refuses profiles that do not fit the declared host,
never touches Docker, the network or a model. Writes <out>/config.env (KEY=VALUE for the checks) and
<out>/judge.json (the judge profile, with site overrides) plus <out>/.gitignore for out/ and cache/.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT / "lib"))
import gateslib as g  # noqa: E402

JUDGE_REQUIRED = {"name": str, "provider": str, "min_vram_gb": (int, float), "context_tokens": int,
                  "prompts": list, "samples": int, "min_votes": int, "verify": bool, "min_confidence": (int, float),
                  "min_severity": str, "blocking_categories": list, "budget_s": (int, float), "params": dict}
STACK_REQUIRED = {"name": str, "verified": bool, "ecosystem": str, "env": dict, "checks": dict}
LAYER_BUDGET_S = {"L0": 60, "L2": 120, "L3": 600}
SMALL_TIER_FORBIDDEN = {"verify-finding", "find-security", "find-scope", "find-test-adequacy"}


def check_judge(j: dict, host_vram: float | None) -> list[str]:
    p = []
    for k, t in JUDGE_REQUIRED.items():
        if k not in j:
            p.append(f"judge {j.get('name')}: missing '{k}'")
        elif not isinstance(j[k], t) or (t is int and isinstance(j[k], bool)):
            p.append(f"judge {j.get('name')}: '{k}' has wrong type")
    if p:
        return p
    if j["provider"] not in ("stub", "openai-compatible"):
        p.append(f"judge {j['name']}: provider must be stub|openai-compatible")
    if j["min_severity"] not in g.SEVERITIES:
        p.append(f"judge {j['name']}: min_severity not in {g.SEVERITIES}")
    bad = [c for c in j["blocking_categories"] if c not in g.CATEGORIES]
    if bad:
        p.append(f"judge {j['name']}: unknown blocking categories {bad}")
    if j["blocking_categories"] and not j.get("verify"):
        p.append(f"judge {j['name']}: blocking categories require verify: true")
    if j["min_votes"] > j["samples"]:
        p.append(f"judge {j['name']}: min_votes > samples")
    for pid in j["prompts"] + (["verify-finding"] if j["verify"] else []):
        if not (KIT / "prompts" / f"{pid}.md").exists():
            p.append(f"judge {j['name']}: prompt '{pid}' not found")
    if j.get("tier") == "small":
        used = (set(j["prompts"]) | ({"verify-finding"} if j["verify"] else set())) & SMALL_TIER_FORBIDDEN
        if used:
            p.append(f"judge {j['name']}: prompts {sorted(used)} are not reliable on a small (~4B) model")
    out_tok = int(j["params"].get("max_tokens", 1024))
    prompt_chars = max(len((KIT / "prompts" / f"{x}.md").read_text()) for x in j["prompts"]
                       if (KIT / "prompts" / f"{x}.md").exists()) if j["prompts"] else 0
    diff_tokens = j["context_tokens"] - out_tok - prompt_chars / float(j.get("chars_per_token", 3.2)) - 900
    if diff_tokens < 1500:
        p.append(f"judge {j['name']}: context {j['context_tokens']} leaves only {diff_tokens:.0f} tokens for the diff")
    if host_vram is not None and j["min_vram_gb"] > host_vram:
        p.append(f"judge {j['name']}: needs >= {j['min_vram_gb']} GB VRAM, host declares {host_vram:g} GB")
    if j["budget_s"] > LAYER_BUDGET_S["L3"] - 60:
        p.append(f"judge {j['name']}: budget_s {j['budget_s']} does not fit L3 (< 10 min incl. other gates)")
    return p


def check_stack(s: dict) -> list[str]:
    p = [f"stack {s.get('name')}: missing/invalid '{k}'" for k, t in STACK_REQUIRED.items()
         if not isinstance(s.get(k), t)]
    for layer in ("fast", "deterministic", "server"):
        if layer not in s.get("checks", {}):
            p.append(f"stack {s.get('name')}: checks.{layer} missing")
    return p


def check_prompts() -> list[str]:
    p = []
    for f in sorted((KIT / "prompts").glob("*.md")):
        t = f.read_text()
        for h in ("System", "User"):
            if not re.search(rf"^##\s+{h}[^\n]*\n+```text\n", t, re.M):
                p.append(f"prompt {f.name}: missing '## {h}' text block")
        m = re.search(r"^Schema:\s*`?schemas/([\w.-]+)`?", t, re.M)
        if not m or not (KIT / "schemas" / m.group(1)).exists():
            p.append(f"prompt {f.name}: schema reference missing or not found")
        if "{{NONCE}}" not in t:
            p.append(f"prompt {f.name}: no nonce-tagged data blocks")
    for f in sorted((KIT / "schemas").glob("*.json")):
        try:
            json.loads(f.read_text())
        except json.JSONDecodeError as e:
            p.append(f"schema {f.name}: {e}")
    return p


def check_taskfile() -> list[str]:
    try:
        tf = g.load_yaml_file(KIT / "Taskfile.gates.yml")
    except g.YamlError as e:
        return [f"Taskfile.gates.yml: {e}"]
    need = {"fast", "deterministic", "mutation", "llm-review", "server", "report", "selftest"}
    missing = need - set(tf.get("tasks", {}))
    return [f"Taskfile.gates.yml: missing tasks {sorted(missing)}"] if missing else []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stack")
    ap.add_argument("--judge")
    ap.add_argument("--site", default=None, help="site env file (default <out>/site.env if present)")
    ap.add_argument("--out", default=".gates")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    problems = check_prompts() + check_taskfile()
    stacks = {f.stem: g.load_yaml_file(f) for f in sorted((KIT / "profiles/stacks").glob("*.yml"))}
    judges = {f.stem: g.load_yaml_file(f) for f in sorted((KIT / "profiles/judges").glob("*.yml"))}
    if a.check:
        for s in stacks.values():
            problems += check_stack(s)
        for j in judges.values():
            problems += check_judge(j, None)
        print(f"checked {len(stacks)} stack + {len(judges)} judge profiles, "
              f"{len(list((KIT / 'prompts').glob('*.md')))} prompts, {len(list((KIT / 'schemas').glob('*.json')))} schemas")
        for x in problems:
            print("PROBLEM:", x)
        print("render --check:", "FAIL" if problems else "OK")
        return 1 if problems else 0
    if a.stack not in stacks or a.judge not in judges:
        g.die(f"--stack one of {sorted(stacks)} and --judge one of {sorted(judges)} are required")
    out = Path(a.out)
    site_path = Path(a.site) if a.site else out / "site.env"
    site = g.load_env_file(site_path) if site_path.exists() else {}
    host_vram = float(site["GATES_HOST_VRAM_GB"]) if site.get("GATES_HOST_VRAM_GB") else None
    stack, judge = stacks[a.stack], judges[a.judge]
    problems += check_stack(stack) + check_judge(judge, host_vram)
    for k in ("GATES_JUDGE_BASE_URL", "GATES_JUDGE_MODEL"):
        if judge["provider"] != "stub" and site.get(k):
            judge["base_url" if k.endswith("URL") else "model"] = site[k]
    if problems:
        print("\n".join("PROBLEM: " + x for x in problems))
        return 1
    env = {"GATES_STACK": stack["name"], "GATES_JUDGE": judge["name"],
           **{k: str(v) for k, v in stack["env"].items()},
           "GATES_LAYER_FAST": ",".join(stack["checks"]["fast"]),
           "GATES_LAYER_DETERMINISTIC": ",".join(stack["checks"]["deterministic"]),
           "GATES_LAYER_SERVER": ",".join(stack["checks"]["server"]),
           **{k: v for k, v in site.items() if k.startswith("GATES_") and not re.search(r"KEY|TOKEN|SECRET", k)}}
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.env").write_text("# rendered by gates/render.py — edit .gates/site.env and re-render\n" +
                                    "".join(f"{k}={v}\n" for k, v in sorted(env.items())))
    (out / "judge.json").write_text(json.dumps(judge, indent=2) + "\n")
    gi = out / ".gitignore"
    if not gi.exists():
        gi.write_text("out/\ncache/\n")
    print(f"rendered stack={stack['name']} (verified={stack['verified']}) judge={judge['name']} -> {out}/"
          f"{{config.env,judge.json}}" + ("" if stack["verified"] else "  [stack profile NOT VERIFIED]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
