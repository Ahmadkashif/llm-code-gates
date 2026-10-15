"""Deterministic stub judge: makes the whole review pipeline testable offline, with no model at all.

It is NOT a reviewer. It reads the numbered diff out of the prompt and answers with a few regex heuristics, plus
deliberate noise (a low-confidence speculative finding per prompt) so the floor/verify/dedup stages have
something to filter. Replies vary in wrapping (<think> blocks, ```json fences, prose) to exercise the parser.
Numbers measured with the stub measure the PIPELINE, never model quality.
"""
from __future__ import annotations

import hashlib
import json
import re

FILE_RE = re.compile(r"^=== FILE: (\S+)")
ADD_RE = re.compile(r"^\s*(\d+) \| \+ ?(.*)$")
DEL_RE = re.compile(r"^\s*(\d+) \| - ?(.*)$")

SECURITY = [
    (r"verify\s*=\s*False|_create_unverified_context|CERT_NONE", "TLS verification disabled", "high", "CWE-295"),
    (r"shell\s*=\s*True|os\.system\(", "shell command built from input", "high", "CWE-78"),
    (r"\.execute\(\s*f[\"']|\.execute\([^)]*%\s*\w", "SQL built by string formatting", "high", "CWE-89"),
    (r"pickle\.loads?\(|yaml\.load\((?![^)]*SafeLoader)", "unsafe deserialisation", "high", "CWE-502"),
    (r"\beval\(|\bexec\(", "eval/exec of dynamic input", "high", "CWE-95"),
    (r"hashlib\.(md5|sha1)\(.*pass", "fast hash for passwords", "high", "CWE-916"),
]
TESTS_ADDED = [
    (r"@pytest\.mark\.(skip|xfail)|pytest\.skip\(|self\.skipTest\(|unittest\.skip", "test-integrity",
     "test newly skipped", "high"),
    (r"^\s*assert\s+True\b|assertTrue\(True\)", "test-integrity", "tautological assertion", "high"),
    (r"^\s*assert\s+\w[\w.()\[\]'\"]*\s+is not None\s*$", "test-adequacy",
     "assertion only checks the value is not None", "medium"),
]


def parse_diff(text: str):
    files, cur = {}, None
    for line in text.splitlines():
        m = FILE_RE.match(line)
        if m:
            cur = m.group(1)
            files[cur] = {"added": [], "removed": []}
            continue
        if cur is None:
            continue
        m = ADD_RE.match(line)
        if m:
            files[cur]["added"].append((int(m.group(1)), m.group(2)))
            continue
        m = DEL_RE.match(line)
        if m:
            files[cur]["removed"].append((int(m.group(1)), m.group(2)))
    return files


def is_test(path: str) -> bool:
    n = path.rsplit("/", 1)[-1]
    return n.startswith("test_") or n.endswith("_test.py") or "/tests/" in "/" + path


def _f(cat, sev, conf, path, ln, title, evidence, scenario, side="new", cwe=None):
    return {"category": cat, "severity": sev, "confidence": conf, "path": path, "side": side, "line_start": ln,
            "line_end": ln, "title": title, "evidence": evidence.strip()[:300], "failure_scenario": scenario,
            "suggested_test": None, "cwe": cwe, "scope_kind": None}


def find(prompt_id: str, user: str) -> dict:
    files = parse_diff(user)
    out = []
    want_sec = prompt_id in ("find-security", "review-single-pass")
    want_tests = prompt_id in ("find-test-integrity", "find-test-adequacy", "review-single-pass")
    for path, d in files.items():
        for ln, code in d["added"]:
            if want_sec and not is_test(path):
                for rx, title, sev, cwe in SECURITY:
                    if re.search(rx, code):
                        out.append(_f("security", sev, 0.8, path, ln, title, code,
                                      f"Input/state: attacker-controlled value -> executes line {ln} -> actual: "
                                      f"{cwe} -> expected: the safe API is used", cwe=cwe))
            if want_tests and is_test(path):
                for rx, cat, title, sev in TESTS_ADDED:
                    if re.search(rx, code):
                        out.append(_f(cat, sev, 0.75, path, ln, title, code,
                                      f"Input/state: code under test returns a wrong value -> executes line {ln} -> "
                                      "actual: test passes -> expected: test fails"))
        if want_tests and is_test(path):
            gone = [(n, r) for n, r in d["removed"] if re.search(r"\bassert|self\.assert", r)]
            if gone and len(gone) > len([1 for _, c in d["added"] if re.search(r"\bassert|self\.assert", c)]):
                ln, code = gone[0]
                out.append(_f("test-integrity", "high", 0.7, path, ln, "assertion removed from tests", code,
                              f"Input/state: the checked behaviour regresses -> executes old line {ln} (now gone) "
                              "-> actual: suite passes -> expected: suite fails", side="old"))
    if prompt_id == "find-scope":
        m = re.search(r"<task-\w+>(.*?)</task-\w+>", user, re.S)
        intent = m.group(1).lower().replace("unverified claim by the code author about what this change should do:", "") if m else ""
        if intent.strip():
            for path, d in files.items():
                stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
                if not is_test(path) and d["added"] and stem not in intent:
                    ln, code = d["added"][0]
                    f = _f("scope", "medium", 0.6, path, ln, f"{path} changed but the task does not mention it",
                           code, f"Input/state: normal use of {stem} -> executes line {ln} -> actual: behaviour "
                           "changed -> expected: unchanged, the task is about something else")
                    f["scope_kind"] = "unrequested"
                    out.append(f)
    # deliberate noise: one speculative, low-confidence finding without a concrete scenario
    first = next(((p, a) for p, d in files.items() if not is_test(p) for a in d["added"] if a[1].strip()), None)
    if first and prompt_id.startswith(("find-correctness", "review-single-pass")):
        p, (ln, code) = first
        out.append(_f("correctness", "medium", 0.65, p, ln, "possible edge case not handled", code,
                      "Some unusual input might behave unexpectedly here."))
    return {"analysis": f"stub heuristic review of {len(files)} file(s)", "findings": out[:8]}


def verify(user: str) -> dict:
    m = re.search(r"<hypothesis-\w+>\s*(\{.*?\})\s*</hypothesis-\w+>", user, re.S)
    finding = json.loads(m.group(1)) if m else {}
    files = parse_diff(user)
    key = "removed" if finding.get("side") == "old" else "added"
    lines = {c.strip() for d in files.values() for _, c in d[key]}
    ev = (finding.get("evidence") or "").strip()
    in_added = bool(ev) and any(ev in a or a in ev for a in lines if a)
    sc = finding.get("failure_scenario", "")
    concrete = len(sc) >= 40 and "might" not in sc and "->" in sc
    checks = {"evidence_in_shown_code": in_added, "scenario_traced": concrete,
              "already_prevented": False, "requested_by_task": False}
    if not in_added:
        return {"checks": checks, "verdict": "refuted", "confidence": 0.9, "reason": "evidence not on an added line"}
    if not concrete:
        return {"checks": checks, "verdict": "refuted", "confidence": 0.7, "reason": "no concrete failing scenario"}
    return {"checks": checks, "verdict": "confirmed", "confidence": 0.8,
            "reason": "evidence present and scenario concrete"}


def respond(prompt_id: str, messages: list[dict]) -> str:
    user = "\n".join(m["content"] for m in messages if m["role"] == "user")
    obj = verify(user) if prompt_id == "verify-finding" else find(prompt_id, user)
    body = json.dumps(obj, indent=1)
    style = int(hashlib.sha256(user.encode()).hexdigest(), 16) % 4
    if style == 0:
        return body
    if style == 1:
        return "<think>\nChecking the diff line by line.\n</think>\n\n" + body
    if style == 2:
        return "Here is my review:\n```json\n" + body + "\n```\n"
    return "<think>\n\n</think>\n\n" + body + "\nDone."


def prompt_id_from(messages: list[dict]) -> str:
    for m in messages:
        mm = re.search(r"\[gates-prompt:([\w-]+)\]", m.get("content", ""))
        if mm:
            return mm.group(1)
    return "find-correctness"
