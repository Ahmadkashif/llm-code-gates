#!/usr/bin/env python3
"""llm_review: advisory LLM review of the change since BASE_REF, against any OpenAI-compatible endpoint.

Pipeline:  find (per prompt, per diff chunk, n samples) -> parse + schema-validate (one repair retry)
           -> grounding (evidence must be on an added line) -> vote (>= min_votes of n samples)
           -> verify (independent verifier prompt; refuted = dropped, uncertain = inform)
           -> dedup across prompts -> confidence/severity floor -> suppressions (with expiry) -> baseline
Outputs:   .gates/out/llm-review.jsonl (+ .events.jsonl per call/decision), llm-review.sarif, llm-review.md,
           a summary on stdout (= the CI job log), and $GITHUB_STEP_SUMMARY / $FORGEJO_STEP_SUMMARY if set.
Exit code: 0 unless a surviving finding's category is in the judge profile's blocking_categories (default: none).
           Endpoint failures exit 0 ("review unavailable") unless the profile sets fail_on_error: true.

Usage: llm_review.py [--base REF] [--judge PATH(.yml|.json)] [--write-baseline] [--max-chunks N]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE))
import gateslib as g  # noqa: E402
import parse  # noqa: E402
import stub_judge  # noqa: E402
from client import JudgeError, OpenAICompatClient  # noqa: E402

PROMPTS = HERE.parent / "prompts"
SCHEMAS = HERE.parent / "schemas"
SEV_RANK = {s: i for i, s in enumerate(g.SEVERITIES)}
CAP_MEDIUM = {"scope", "test-adequacy"}
SKIP_FILES = re.compile(r"(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|poetry\.lock|uv\.lock|go\.sum|"
                        r"Cargo\.lock)$|\.(png|jpe?g|gif|svg|ico|pdf|zip|gz|min\.js)$")


# ------------------------------------------------------------------------------------------- prompts
def load_prompt(pid: str) -> dict:
    text = (PROMPTS / f"{pid}.md").read_text()

    def block(heading):
        m = re.search(rf"^##\s+{heading}[^\n]*\n+```text\n(.*?)\n```", text, re.S | re.M)
        if not m:
            raise SystemExit(f"prompt {pid}: missing '## {heading}' ```text block")
        return m.group(1)
    schema_name = re.search(r"^Schema:\s*`?schemas/([\w.-]+)`?", text, re.M)
    version = re.search(r"^Version:\s*(\S+)", text, re.M)
    cats = re.search(r"^Categories:\s*(.+)$", text, re.M)
    return {"id": pid, "system": block("System"), "user": block("User"),
            "categories": [c.strip() for c in cats.group(1).split(",")] if cats and "(" not in cats.group(1) else [],
            "schema": json.loads((SCHEMAS / (schema_name.group(1) if schema_name else "findings.schema.json"))
                                 .read_text()),
            "version": version.group(1) if version else "?",
            "sha256": hashlib.sha256(text.encode()).hexdigest()[:16]}


CLOSE_TAG = re.compile(r"</\s*(task|diff|hypothesis)\b", re.I)


def render(tpl: str, **kw) -> str:
    """Fill {{NAME}} placeholders. Data values cannot close the nonce-tagged blocks (closing tags neutralised)."""
    def val(name):
        v = str(kw.get(name, "{{" + name + "}}"))
        return v if name == "NONCE" else CLOSE_TAG.sub(lambda m: "<\\/" + m.group(1), v)
    return re.sub(r"\{\{(\w+)\}\}", lambda m: val(m.group(1)), tpl)


SECRETISH = re.compile(r"(?<![A-Za-z0-9])([A-Za-z0-9_\-+/=]{4})[A-Za-z0-9_\-+/=]{16,}")


def redact(s: str) -> str:
    """Keep 4 chars of any long token-like string (keys/tokens must never reach CI logs)."""
    return SECRETISH.sub(lambda m: m.group(1) + "...", s or "")


# ------------------------------------------------------------------------------------------- diff
def numbered_diff(base: str, root: Path, exclude: list[str]) -> dict[str, str]:
    """{path: numbered block}; added lines carry their new line number: '  41 | + code', removed '     | - code'."""
    raw = g.diff_text(base, cwd=root, context=3)
    files, cur, buf, new_no, old_no = {}, None, [], 0, 0
    status = {}

    def flush():
        if cur and buf:
            files[cur] = f"=== FILE: {cur} ({status.get(cur, 'modified')})\n" + "\n".join(buf)
    for line in raw.splitlines():
        if line.startswith("diff --git "):
            flush()
            cur, buf = None, []
            continue
        if line.startswith("new file mode"):
            status["__next"] = "new file"
            continue
        if line.startswith("deleted file mode"):
            status["__next"] = "deleted"
            continue
        if line.startswith("+++ "):
            p = line[4:]
            cur = None if p == "/dev/null" else p[2:] if p.startswith("b/") else p
            if cur:
                status[cur] = status.pop("__next", "modified")
                if SKIP_FILES.search(cur) or any(cur.startswith(x) for x in exclude):
                    cur = None
            continue
        if line.startswith("--- ") or cur is None:
            continue
        m = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$", line)
        if m:
            old_no, new_no = int(m.group(1)), int(m.group(2))
            buf.append(f"     @@ {m.group(3).strip()}")
            continue
        if line.startswith("+"):
            buf.append(f"{new_no:>5} | + {line[1:]}")
            new_no += 1
        elif line.startswith("-"):
            buf.append(f"{old_no:>5} | - {line[1:]}")
            old_no += 1
        elif line.startswith(" "):
            buf.append(f"{new_no:>5} |   {line[1:]}")
            new_no += 1
            old_no += 1
    flush()
    return files


def chunks(files: dict[str, str], budget_chars: int) -> list[list[str]]:
    """Greedy packing of whole files (split large files at hunk boundaries) into chunks of <= budget chars."""
    out, cur, size = [], [], 0
    pieces = []
    for block in files.values():
        if len(block) <= budget_chars:
            pieces.append(block)
            continue
        header, *rest = block.split("\n", 1)
        hunks = re.split(r"(?m)^(?=     @@)", rest[0] if rest else "")
        part = header
        for h in hunks:
            if len(part) + len(h) > budget_chars and part != header:
                pieces.append(part)
                part = header + " (continued)"
            part += "\n" + h[:budget_chars - len(header) - 30]
        pieces.append(part)
    for p in pieces:
        if size + len(p) > budget_chars and cur:
            out.append(cur)
            cur, size = [], 0
        cur.append(p)
        size += len(p) + 1
    if cur:
        out.append(cur)
    return out


def side_map(files: dict[str, str], marker: str) -> dict[str, dict[int, str]]:
    """marker '+' -> added lines by new number; '-' -> removed lines by old number."""
    res = {}
    rx = re.compile(r"^\s*(\d+) \| " + re.escape(marker) + r" (.*)$")
    for path, block in files.items():
        for line in block.splitlines():
            m = rx.match(line)
            if m:
                res.setdefault(path, {})[int(m.group(1))] = m.group(2)
    return res


def task_text(root: Path, cfg: dict, base: str) -> str:
    p = root / cfg.get("GATES_TASK_FILE", ".gates/task.md")
    if p.exists():
        t = p.read_text()
    else:
        t = g.git("log", "--format=%B", f"{base}..HEAD", cwd=root, check=False)
    return t.strip()[:3000] or "(no task statement provided)"


# ------------------------------------------------------------------------------------------- judge
class Judge:
    def __init__(self, profile: dict):
        self.p = profile
        self.stub = profile.get("provider") == "stub"
        if not self.stub:
            prof = dict(profile)
            prof["base_url"] = os.environ.get(profile.get("base_url_env", ""), "") or profile.get("base_url", "")
            prof["model"] = os.environ.get(profile.get("model_env", ""), "") or profile.get("model", "")
            if not prof["base_url"] or not prof["model"]:
                raise JudgeError("judge profile needs base_url and model (or their *_env variables)")
            self.client = OpenAICompatClient(prof)
            self.model = prof["model"]
        else:
            self.model = "stub-judge"
        self.calls = 0
        self.nonce = os.urandom(4).hex()

    def ask(self, prompt: dict, user: str, seed: int | None):
        system = render(prompt["system"], NONCE=self.nonce)
        msgs = [{"role": "system", "content": f"[gates-prompt:{prompt['id']}]\n" + system},
                {"role": "user", "content": user}]
        self.calls += 1
        if self.stub:
            t0 = time.monotonic()
            return {"content": stub_judge.respond(prompt["id"], msgs), "latency_s": round(time.monotonic() - t0, 4),
                    "usage": {}, "finish_reason": "stop"}, msgs
        return self.client.chat(msgs, schema=prompt["schema"], seed=seed), msgs

    def ask_json(self, prompt: dict, user: str, seed: int | None, events: list, meta: dict):
        """Call, parse, validate; one repair turn on failure. Returns obj or None."""
        resp, msgs = self.ask(prompt, user, seed)
        obj, err = parse.extract_json(resp["content"])
        if obj is not None and isinstance(obj.get("findings"), list):
            obj["findings"] = obj["findings"][:3]
        errs = g.validate(obj, prompt["schema"]) if obj is not None else [err]
        ev = {"event": "call", **meta, "prompt": prompt["id"], "latency_s": resp.get("latency_s"),
              "usage": resp.get("usage"), "finish_reason": resp.get("finish_reason"), "parse_ok": obj is not None,
              "schema_errors": errs[:5]}
        if errs and int(self.p.get("repair_attempts", 1)) > 0:
            repair = (f"Your previous reply was not valid for the required JSON schema: {'; '.join(errs[:5])}.\n"
                      "Reply again with ONLY the corrected JSON object, no prose, no code fences.")
            if self.stub:
                resp2 = {"content": stub_judge.respond(prompt["id"], msgs), "latency_s": 0}
            else:
                resp2 = self.client.chat(msgs + [{"role": "assistant", "content": resp["content"][:4000]},
                                                 {"role": "user", "content": repair}], schema=prompt["schema"],
                                         seed=seed)
            self.calls += 1
            obj, err = parse.extract_json(resp2["content"])
            if obj is not None and isinstance(obj.get("findings"), list):
                obj["findings"] = obj["findings"][:3]
            errs = g.validate(obj, prompt["schema"]) if obj is not None else [err]
            ev.update({"repaired": True, "repair_ok": not errs, "schema_errors": errs[:5]})
        events.append(ev)
        return None if errs else obj


# ------------------------------------------------------------------------------------------- pipeline helpers
def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def ground(f: dict, added: dict, removed: dict, task: str) -> bool:
    """Evidence must be copied from a line of that file on the stated side (added, or removed for side=old), or
    from the task text for scope 'unimplemented'. Snaps line numbers to where the evidence actually is."""
    if f.get("category") == "scope" and f.get("scope_kind") == "unimplemented":
        return bool(norm_ws(f["evidence"])) and norm_ws(f["evidence"]) in norm_ws(task)
    lines = (removed if f.get("side") == "old" else added).get(f["path"])
    if not lines:
        return False
    ev = norm_ws(f["evidence"])
    if not ev:
        return False
    hits = [ln for ln, text in lines.items() if ev in norm_ws(text) or (len(norm_ws(text)) > 8 and norm_ws(text) in ev)]
    if not hits:
        return False
    if f["line_start"] not in hits:
        nearest = min(hits, key=lambda ln: abs(ln - f["line_start"]))
        f["line_start"] = f["line_end"] = nearest
    f["line_end"] = max(f["line_start"], f.get("line_end") or 0)
    return True


def same(a: dict, b: dict, tol: int = 3) -> bool:
    return a["path"] == b["path"] and a["category"] == b["category"] and \
        a["line_start"] - tol <= b["line_end"] and b["line_start"] - tol <= a["line_end"]


def cluster(findings: list[dict]) -> list[list[dict]]:
    groups: list[list[dict]] = []
    for f in findings:
        for grp in groups:
            if same(grp[0], f):
                grp.append(f)
                break
        else:
            groups.append([f])
    return groups


# ------------------------------------------------------------------------------------------- main
def load_judge(path: str | None, root: Path) -> dict:
    p = Path(path) if path else root / ".gates" / "judge.json"
    if not p.exists():
        g.die(f"no judge profile at {p} (run render.py, or pass --judge)")
    return json.loads(p.read_text()) if p.suffix == ".json" else g.load_yaml_file(p)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=os.environ.get("BASE_REF", "origin/main"))
    ap.add_argument("--judge", default=os.environ.get("GATES_JUDGE_PROFILE"))
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--max-chunks", type=int, default=None)
    a = ap.parse_args(argv)
    t_start = time.monotonic()
    root = g.repo_root()
    cfg = g.config(root)
    prof = load_judge(a.judge, root)
    base = g.resolve_base(a.base, cwd=root)
    od = g.out_dir(root)
    events: list[dict] = []
    notes: list[str] = []
    kit_rel = os.path.relpath(g.KIT_DIR, root)
    files = numbered_diff(base, root, [kit_rel + "/", ".gates/"] + g.cfg_list(cfg, "GATES_REVIEW_EXCLUDE"))
    added, removed = side_map(files, "+"), side_map(files, "-")
    ctx_tokens = int(prof.get("context_tokens", 8192))
    out_tokens = int(prof.get("params", {}).get("max_tokens", 1024))
    cpt = float(prof.get("chars_per_token", 3.2))
    prompts = [load_prompt(p) for p in prof.get("prompts", ["review-single-pass"])]
    overhead = max(len(p["system"]) + len(p["user"]) for p in prompts) + 3000  # + task text
    budget_chars = max(2000, int((ctx_tokens - out_tokens) * cpt) - overhead)
    parts = chunks(files, budget_chars)
    max_chunks = a.max_chunks or int(prof.get("max_chunks", 6))
    if len(parts) > max_chunks:
        notes.append(f"diff needs {len(parts)} chunks; only the first {max_chunks} were reviewed (raise max_chunks "
                     "or split the change)")
        parts = parts[:max_chunks]
    task = task_text(root, cfg, base)
    run = {"event": "run", "time": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
           "profile": prof.get("name"), "provider": prof.get("provider"), "base": base[:12],
           "prompts": {p["id"]: {"version": p["version"], "sha256": p["sha256"]} for p in prompts},
           "chunks": len(parts), "budget_chars": budget_chars, "files": len(files)}
    stats = {"profile": prof.get("name"), "files": len(files), "chunks": len(parts)}
    if not files:
        g.emit("llm-review", [], root, ["no reviewable diff"], stats)
        return 0
    try:
        judge = Judge(prof)
    except JudgeError as e:
        return unavailable(root, str(e), prof, stats)
    run["model"] = judge.model
    samples = int(prof.get("samples", 1))
    min_votes = int(prof.get("min_votes", 1))
    budget_s = float(prof.get("budget_s", 480))
    raw: list[dict] = []
    trusted = cfg.get("GATES_TASK_TRUSTED", "1" if prof.get("task_trusted") else "0") == "1"
    blocking = set(prof.get("blocking_categories") or [])
    try:
        for pr in prompts:
            if pr["id"] == "find-scope" and not trusted:
                notes.append("find-scope skipped: task text not marked human-authored (GATES_TASK_TRUSTED=1)")
                continue
            for ci, part in enumerate(parts):
                user = render(pr["user"], DIFF="\n".join(part), TASK=task, NONCE=judge.nonce)
                for s in range(samples):
                    if time.monotonic() - t_start > budget_s:
                        notes.append(f"time budget {budget_s:g}s reached; remaining calls skipped")
                        raise TimeoutError
                    obj = judge.ask_json(pr, user, seed=1000 + s, events=events,
                                         meta={"chunk": ci, "sample": s})
                    for f in (obj or {}).get("findings", []):
                        f.update({"_prompt": pr["id"], "_sample": s, "_chunk": ci})
                        if pr["categories"] and f["category"] not in pr["categories"]:
                            events.append({"event": "decision", "stage": "off-category", "prompt": pr["id"],
                                           "category": f["category"], "title": f.get("title")})
                            continue
                        if f["category"] in CAP_MEDIUM and SEV_RANK[f["severity"]] > SEV_RANK["medium"]:
                            f["severity"] = "medium"
                        f["evidence"] = redact(f["evidence"])
                        raw.append(f)
    except TimeoutError:
        pass
    except JudgeError as e:
        if not raw:
            return unavailable(root, str(e), prof, stats, events)
        notes.append(f"judge error mid-run, partial review: {e}")

    def drop(f, stage, why=""):
        events.append({"event": "decision", "stage": stage, "why": why, "prompt": f.get("_prompt"),
                       "path": f.get("path"), "line": f.get("line_start"), "category": f.get("category"),
                       "title": f.get("title")})

    # grounding
    grounded = []
    for f in raw:
        (grounded.append(f) if ground(f, added, removed, task) else
         drop(f, "ungrounded", "evidence not found on the stated side of the diff"))
    # voting within each prompt across samples
    voted = []
    for pr in prompts:
        for grp in cluster([f for f in grounded if f["_prompt"] == pr["id"]]):
            votes = len({f["_sample"] for f in grp})
            rep = max(grp, key=lambda f: (SEV_RANK[f["severity"]], f["confidence"]))
            rep = dict(rep, confidence=sum(f["confidence"] for f in grp) / len(grp), _votes=votes)
            need = max(min_votes, min(2, samples)) if rep["category"] in blocking else min_votes
            (voted.append(rep) if votes >= need else drop(rep, "votes", f"{votes}/{samples} < {need}"))
    # dedup across prompts (before verify, to save calls)
    merged = []
    for grp in cluster(voted):
        rep = max(grp, key=lambda f: (SEV_RANK[f["severity"]], f["confidence"]))
        rep = dict(rep, _sources=sorted({f["_prompt"] for f in grp}))
        merged.append(rep)
        for f in grp:
            if f is not rep and f.get("title") != rep.get("title"):
                drop(f, "dedup", f"merged into {rep.get('title')}")
    # pre-verify floor on severity only (cheap), then verify
    min_sev = SEV_RANK[prof.get("min_severity", "medium")]
    min_conf = float(prof.get("min_confidence", 0.6))
    kept = []
    for f in merged:
        (kept.append(f) if SEV_RANK[f["severity"]] >= min_sev else drop(f, "severity-floor", f["severity"]))
    if prof.get("verify", True) and kept:
        vprompt = load_prompt("verify-finding")
        cap = int(prof.get("max_findings_to_verify", 8))
        verified = []
        for i, f in enumerate(sorted(kept, key=lambda f: -SEV_RANK[f["severity"]])):
            if i >= cap or time.monotonic() - t_start > budget_s:
                f["_verdict"] = "unverified"
                verified.append(f)
                continue
            # neutral hypothesis: no finder severity, confidence, title adjectives or analysis
            hyp = {"path": f["path"], "side": f.get("side", "new"), "line_start": f["line_start"],
                   "line_end": f["line_end"], "category": f["category"], "claim": f["title"],
                   "evidence": f["evidence"], "failure_scenario": f["failure_scenario"]}
            user = render(vprompt["user"], FINDING_JSON=json.dumps(hyp, indent=1), HUNK=files.get(f["path"], ""),
                          TASK=task, NONCE=judge.nonce)
            try:
                v = judge.ask_json(vprompt, user, seed=7, events=events, meta={"verify": f.get("title")})
            except JudgeError as e:
                notes.append(f"verifier unavailable: {e}")
                v = None
            if v is None:
                f["_verdict"] = "unverified"
                verified.append(f)
            else:
                ch = v["checks"]
                verdict = v["verdict"]
                # harness consistency rules (a terse model's verdict may contradict its own checks)
                if not ch["evidence_in_shown_code"] or ch["already_prevented"]:
                    verdict = "refuted"
                elif verdict == "confirmed" and not ch["scenario_traced"]:
                    verdict = "uncertain"
                if ch["requested_by_task"] and f["category"] in ("correctness", "scope"):
                    verdict = "refuted"
                if verdict == "refuted":
                    drop(f, "refuted", v.get("reason", ""))
                    continue
                f["_verdict"] = verdict
                f["confidence"] = min(f["confidence"], v["confidence"]) if verdict == "confirmed" \
                    else v["confidence"] * 0.5
                if v.get("severity") and SEV_RANK[v["severity"]] < SEV_RANK[f["severity"]]:
                    f["severity"] = v["severity"]
                verified.append(f)
        kept = verified
    final = []
    for f in kept:
        if f["confidence"] < min_conf:
            drop(f, "confidence-floor", f"{f['confidence']:.2f} < {min_conf}")
        elif SEV_RANK[f["severity"]] < min_sev:
            drop(f, "severity-floor", f["severity"])
        else:
            final.append(f)
    findings = []
    for f in final:
        verdict = f.get("_verdict", "not-run")
        if verdict in ("uncertain", "unverified"):
            level = "inform"
        elif verdict == "confirmed" and f["category"] in blocking:
            level = "block"  # only verified findings in a promoted category can ever block
        else:
            level = "warn"
        findings.append(g.Finding("llm-review", f"llm.{f['category']}", f["category"], f["severity"],
                                  f"{f['title']} — {f['failure_scenario']}", f["path"], f["line_start"],
                                  f["evidence"], level=level, confidence=round(f["confidence"], 2),
                                  extra={"prompts": f.get("_sources"), "votes": f.get("_votes"),
                                         "verdict": f.get("_verdict", "not-run"),
                                         "suggested_test": f.get("suggested_test")}))
    notes += g.apply_suppressions(findings, root)
    baseline = g.load_baseline(root, "llm")
    if a.write_baseline:
        g.write_baseline(root, "llm", findings)
        notes.append(f"baseline written with {len(findings)} fingerprint(s)")
    before_bl = len(findings)
    findings = [f for f in findings if f.fingerprint not in baseline]
    stats.update({"model": judge.model, "calls": judge.calls, "raw": len(raw), "grounded": len(grounded),
                  "after_votes": len(voted), "after_dedup": len(merged), "reported": len(findings),
                  "baselined": before_bl - len(findings), "wall_s": round(time.monotonic() - t_start, 2)})
    with (od / "llm-review.events.jsonl").open("w") as fh:
        for e in [run, *events]:
            fh.write(json.dumps(e) + "\n")
    rc = g.emit("llm-review", findings, root, notes, stats)
    write_summary(od, prof, findings, stats, notes, blocking)
    if rc:
        print(f"llm-review: BLOCKING — categories promoted by profile '{prof.get('name')}': {sorted(blocking)}")
    else:
        print(f"llm-review: advisory only (profile '{prof.get('name')}', blocking categories: "
              f"{sorted(blocking) or 'none'}) — exit 0")
    return rc


def unavailable(root, msg, prof, stats, events=None) -> int:
    od = g.out_dir(root)
    with (od / "llm-review.events.jsonl").open("w") as fh:
        for e in events or []:
            fh.write(json.dumps(e) + "\n")
        fh.write(json.dumps({"event": "unavailable", "error": msg}) + "\n")
    g.emit("llm-review", [], root, [f"REVIEW UNAVAILABLE: {msg}"], stats)
    write_summary(od, prof, [], stats, [f"review unavailable: {msg}"], set())
    if prof.get("fail_on_error"):
        return 1
    print("llm-review: unavailable; advisory gate exits 0")
    return 0


def write_summary(od: Path, prof, findings, stats, notes, blocking):
    lines = [f"## LLM review (advisory) — profile `{prof.get('name')}`", "",
             f"Model: `{stats.get('model', '?')}` · calls: {stats.get('calls', 0)} · raw findings: "
             f"{stats.get('raw', 0)} → reported: {len(findings)} · blocking categories: "
             f"{', '.join(sorted(blocking)) or 'none'}", ""]
    if not findings:
        lines.append("No findings survived verification and floors.")
    else:
        lines += ["| level | severity | category | location | finding | conf |", "|---|---|---|---|---|---|"]
        for f in findings:
            lvl = "suppressed" if f.suppressed else f.level
            msg = f.message.replace("|", "\\|")[:220]
            lines.append(f"| {lvl} | {f.severity} | {f.category} | `{f.path}:{f.line}` | {msg} | {f.confidence} |")
    for n in notes:
        lines.append(f"\n> note: {n}")
    lines.append("\n_LLM findings are advisory: they can be wrong. A category blocks only after its measured "
                 "precision is >= 90% on labelled data (see the kit README)._\n")
    text = "\n".join(lines)
    (od / "llm-review.md").write_text(text)
    for var in ("GITHUB_STEP_SUMMARY", "FORGEJO_STEP_SUMMARY"):
        if os.environ.get(var):
            with open(os.environ[var], "a") as fh:
                fh.write(text + "\n")
            break


if __name__ == "__main__":
    sys.exit(main())
