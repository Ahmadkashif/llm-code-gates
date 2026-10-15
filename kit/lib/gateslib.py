"""Shared helpers for the llm-code-gates kit. Python 3.10+ standard library only.

Contents: git diff helpers, the Finding record, suppressions with expiry, baselines, JSONL/SARIF/markdown
writers, config loading, a YAML-subset loader for profiles, and a JSON-Schema-subset validator for LLM output.
"""
from __future__ import annotations

import datetime as _dt
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

KIT_DIR = Path(__file__).resolve().parent.parent
SEVERITIES = ["info", "low", "medium", "high", "critical"]
LEVELS = ["inform", "warn", "block"]

# Categories shared by deterministic checks and LLM prompts (RQ1 taxonomy -> ids).
CATEGORIES = [
    "dependency",        # hallucinated / non-existent / suspiciously new package, undeclared import
    "correctness",       # plausible logic that fails on edge cases
    "scope",             # silent scope expansion
    "test-integrity",    # deleted/weakened/skipped tests and assertions
    "test-adequacy",     # tests written to pass: coverage drop, surviving mutants
    "security",          # insecure defaults, copied vulnerable patterns
    "secret",            # hard-coded credentials
    "licence",           # licence-contaminated snippets, incompatible dependency licences
    "dead-code",
    "error-handling",    # over-broad / swallowed exceptions
    "duplication",
    "maintainability",
]


# ----------------------------------------------------------------------------------------------- process / git
def run(cmd, cwd=None, timeout=None, env=None, check=False, input_text=None):
    """Run a command (list or str). Returns CompletedProcess with text output."""
    p = subprocess.run(cmd, cwd=cwd, timeout=timeout, env=env, shell=isinstance(cmd, str),
                       capture_output=True, text=True, input=input_text)
    if check and p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {cmd}\n{p.stdout}\n{p.stderr}")
    return p


def git(*args, cwd=None, check=True):
    return run(["git", *args], cwd=cwd, check=check).stdout


def repo_root(cwd=None) -> Path:
    return Path(git("rev-parse", "--show-toplevel", cwd=cwd).strip())


def resolve_base(base: str, cwd=None) -> str:
    """Return a commit for BASE_REF; fall back to merge-base so a branch is compared with where it forked."""
    try:
        sha = git("rev-parse", "--verify", f"{base}^{{commit}}", cwd=cwd).strip()
    except RuntimeError:
        raise SystemExit(f"gates: BASE_REF '{base}' does not resolve to a commit (fetch it, or pass BASE_REF=...)") \
            from None
    mb = run(["git", "merge-base", sha, "HEAD"], cwd=cwd)
    return mb.stdout.strip() if mb.returncode == 0 and mb.stdout.strip() else sha


def skipped(path: str, root: Path | None = None) -> bool:
    """The vendored kit itself and the kit's state dir are never checked or reviewed."""
    root = root or repo_root()
    try:
        kit_rel = KIT_DIR.relative_to(root).as_posix()
    except ValueError:
        kit_rel = None  # kit runs from outside the repo (tests, docker image)
    return path.startswith(".gates/") or bool(kit_rel) and (path == kit_rel or path.startswith(kit_rel + "/"))


def repo_files(cwd=None, untracked=True) -> list[str]:
    """Tracked (+ untracked, not ignored) files, minus the kit and .gates/."""
    root = repo_root(cwd)
    files = git("ls-files", cwd=cwd).splitlines()
    if untracked:
        files += git("ls-files", "--others", "--exclude-standard", cwd=cwd).splitlines()
    return [f for f in dict.fromkeys(files) if f and not skipped(f, root)]


def changed_files(base: str, cwd=None, include_untracked=True) -> list[str]:
    """Files changed between BASE and the working tree (committed + staged + unstaged + untracked)."""
    out = git("diff", "--name-only", "--diff-filter=ACMRD", base, cwd=cwd).splitlines()
    if include_untracked:
        out += git("ls-files", "--others", "--exclude-standard", cwd=cwd).splitlines()
    seen, res = set(), []
    root = repo_root(cwd)
    for f in out:
        if f and f not in seen and not skipped(f, root):
            seen.add(f)
            res.append(f)
    return res


def deleted_files(base: str, cwd=None) -> list[str]:
    return [f for f in git("diff", "--name-only", "--diff-filter=D", base, cwd=cwd).splitlines() if f]


def file_at(ref: str | None, path: str, cwd=None) -> str | None:
    """Content of path at ref (None = working tree). None if absent."""
    if ref is None:
        p = (Path(cwd) if cwd else repo_root()) / path
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except (FileNotFoundError, IsADirectoryError):
            return None
    r = run(["git", "show", f"{ref}:{path}"], cwd=cwd)
    return r.stdout if r.returncode == 0 else None


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def added_lines(base: str, cwd=None, paths=None) -> dict[str, dict[int, str]]:
    """{path: {new_line_no: text}} for lines added vs base (working tree), plus untracked files in full."""
    args = ["diff", "--unified=0", "--no-color", "--no-ext-diff", base]
    if paths:
        args += ["--", *paths]
    res: dict[str, dict[int, str]] = {}
    cur = None
    new_no = 0
    for line in git(*args, cwd=cwd).splitlines():
        if line.startswith("+++ "):
            cur = None if line[4:] == "/dev/null" else line[6:] if line[4:].startswith("b/") else line[4:]
            if cur and skipped(cur, repo_root(cwd)):
                cur = None
            if cur:
                res.setdefault(cur, {})
            continue
        if line.startswith("--- "):
            continue
        m = _HUNK.match(line)
        if m:
            new_no = int(m.group(3))
            continue
        if cur and line.startswith("+"):
            res[cur][new_no] = line[1:]
            new_no += 1
        elif cur and line.startswith(" "):
            new_no += 1
    root = repo_root(cwd)
    for f in git("ls-files", "--others", "--exclude-standard", cwd=cwd).splitlines():
        if skipped(f, root) or paths and not any(fnmatch.fnmatch(f, p) or f == p for p in paths):
            continue
        try:
            text = (root / f).read_text(encoding="utf-8", errors="replace")
        except (IsADirectoryError, FileNotFoundError):
            continue
        res[f] = {i + 1: t for i, t in enumerate(text.splitlines())}
    return res


def diff_text(base: str, cwd=None, paths=None, context=3) -> str:
    args = ["diff", f"--unified={context}", "--no-color", "--no-ext-diff", base]
    if paths:
        args += ["--", *paths]
    out = git(*args, cwd=cwd)
    root = repo_root(cwd)
    for f in git("ls-files", "--others", "--exclude-standard", cwd=cwd).splitlines():
        if skipped(f, root) or paths and f not in paths:
            continue
        try:
            body = (root / f).read_text(encoding="utf-8", errors="replace").splitlines()
        except (IsADirectoryError, FileNotFoundError):
            continue
        out += f"diff --git a/{f} b/{f}\nnew file mode 100644\n--- /dev/null\n+++ b/{f}\n@@ -0,0 +1,{len(body)} @@\n"
        out += "".join(f"+{l}\n" for l in body)
    return out


# ----------------------------------------------------------------------------------------------- config
def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            v = v[1:-1]
        env[k.strip()] = v
    return env


def config(root: Path | None = None) -> dict[str, str]:
    """Rendered .gates/config.env, overridden by GATES_* environment variables."""
    root = root or repo_root()
    cfg = load_env_file(root / ".gates" / "config.env")
    for k, v in os.environ.items():
        if k.startswith("GATES_"):
            cfg[k] = v
    return cfg


def cfg_list(cfg, key, default=""):
    return [x.strip() for x in cfg.get(key, default).replace(";", ",").split(",") if x.strip()]


def out_dir(root: Path | None = None) -> Path:
    d = (root or repo_root()) / ".gates" / "out"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ----------------------------------------------------------------------------------------------- findings
@dataclass
class Finding:
    check: str                 # producing check, e.g. "dep-check", "llm-review/correctness"
    rule: str                  # stable rule id, e.g. "dependency.not-on-registry"
    category: str              # one of CATEGORIES
    severity: str              # one of SEVERITIES
    message: str
    path: str = ""
    line: int = 0
    evidence: str = ""
    level: str = "block"       # block | warn | inform (after policy)
    confidence: float = 1.0    # deterministic checks: 1.0
    extra: dict = field(default_factory=dict)
    suppressed: bool = False
    suppression_note: str = ""

    @property
    def fingerprint(self) -> str:
        """Stable across line shifts: rule + path + normalised evidence (not the line number)."""
        norm = re.sub(r"\s+", " ", (self.evidence or self.message)).strip().lower()
        return hashlib.sha256(f"{self.rule}|{self.path}|{norm}".encode()).hexdigest()[:16]

    def to_dict(self):
        d = asdict(self)
        d["fingerprint"] = self.fingerprint
        return d


def load_suppressions(root: Path) -> list[dict]:
    p = root / ".gates" / "suppressions.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text())
    return data.get("suppressions", data) if isinstance(data, dict) else data


def apply_suppressions(findings: list[Finding], root: Path, today: _dt.date | None = None) -> list[str]:
    """Mark matching findings suppressed. Each suppression needs reason + expires (YYYY-MM-DD, max 90 days
    ahead is enforced by kit tests on the repo, not here). Expired entries no longer suppress; returns warnings."""
    today = today or _dt.date.today()
    warnings = []
    for s in load_suppressions(root):
        try:
            exp = _dt.date.fromisoformat(s["expires"])
        except (KeyError, ValueError):
            warnings.append(f"suppression without a valid 'expires' date ignored: {s}")
            continue
        if not s.get("reason"):
            warnings.append(f"suppression without 'reason' ignored: {s}")
            continue
        active = exp >= today
        for f in findings:
            if s.get("fingerprint") and s["fingerprint"] != f.fingerprint:
                continue
            if s.get("rule") and not fnmatch.fnmatch(f.rule, s["rule"]):
                continue
            if s.get("path") and not fnmatch.fnmatch(f.path, s["path"]):
                continue
            if not (s.get("fingerprint") or s.get("rule")):
                continue
            if active:
                f.suppressed = True
                f.suppression_note = f"suppressed until {s['expires']}: {s['reason']}"
            else:
                warnings.append(f"EXPIRED suppression ({s['expires']}) no longer applies to {f.rule} {f.path}")
    return warnings


def load_baseline(root: Path, name: str) -> set[str]:
    p = root / ".gates" / f"baseline-{name}.json"
    if not p.exists():
        return set()
    return set(json.loads(p.read_text()).get("fingerprints", []))


def write_baseline(root: Path, name: str, findings: list[Finding]):
    p = root / ".gates" / f"baseline-{name}.json"
    p.write_text(json.dumps({"fingerprints": sorted({f.fingerprint for f in findings})}, indent=2) + "\n")


def emit(check: str, findings: list[Finding], root: Path, notes: list[str] | None = None,
         stats: dict | None = None) -> int:
    """Write .gates/out/<check>.jsonl + .sarif, print a human summary; return exit code (1 iff unsuppressed block)."""
    od = out_dir(root)
    safe = check.replace("/", "_")
    with (od / f"{safe}.jsonl").open("w") as fh:
        fh.write(json.dumps({"event": "run", "check": check, "time": _dt.datetime.now(_dt.UTC)
                             .isoformat(timespec="seconds"), "stats": stats or {}, "notes": notes or []}) + "\n")
        for f in findings:
            fh.write(json.dumps({"event": "finding", **f.to_dict()}) + "\n")
    (od / f"{safe}.sarif").write_text(json.dumps(to_sarif(check, findings), indent=1))
    blocking = [f for f in findings if f.level == "block" and not f.suppressed]
    print(f"== gates/{check}: {len(findings)} finding(s), {len(blocking)} blocking"
          + (f" | {json.dumps(stats)}" if stats else ""))
    for n in notes or []:
        print(f"   note: {n}")
    for f in findings:
        tag = "SUPPRESSED" if f.suppressed else f.level.upper()
        loc = f"{f.path}:{f.line}" if f.line else f.path
        print(f"   [{tag}] {f.rule} ({f.severity}) {loc} — {f.message}")
        if f.suppressed:
            print(f"            {f.suppression_note}")
    return 1 if blocking else 0


_SARIF_LEVEL = {"block": "error", "warn": "warning", "inform": "note"}


def to_sarif(tool: str, findings: list[Finding]) -> dict:
    rules = {}
    results = []
    for f in findings:
        rules.setdefault(f.rule, {"id": f.rule, "shortDescription": {"text": f.rule},
                                  "properties": {"category": f.category}})
        r = {"ruleId": f.rule, "level": _SARIF_LEVEL.get(f.level, "warning"),
             "message": {"text": f.message + (f"\nEvidence: {f.evidence}" if f.evidence else "")},
             "partialFingerprints": {"gates/v1": f.fingerprint},
             "properties": {"category": f.category, "severity": f.severity, "confidence": f.confidence}}
        if f.path:
            loc = {"physicalLocation": {"artifactLocation": {"uri": f.path}}}
            if f.line:
                loc["physicalLocation"]["region"] = {"startLine": max(1, int(f.line))}
            r["locations"] = [loc]
        if f.suppressed:
            r["suppressions"] = [{"kind": "external", "justification": f.suppression_note}]
        results.append(r)
    return {"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": f"llm-code-gates/{tool}",
                                          "informationUri": "https://github.com/Ahmadkashif/llm-code-gates",
                                          "rules": list(rules.values())}},
                      "results": results}]}


def level_for(cfg: dict, rule: str, default: str) -> str:
    """Policy override: GATES_LEVEL_<RULE with . and - as _> = block|warn|inform."""
    key = "GATES_LEVEL_" + re.sub(r"[^A-Za-z0-9]", "_", rule).upper()
    v = cfg.get(key, default)
    return v if v in LEVELS else default


# ----------------------------------------------------------------------------------------------- mini YAML
class YamlError(ValueError):
    pass


def _scalar(s: str):
    s = s.strip()
    if s == "" or s in ("~", "null", "Null", "NULL"):
        return None
    if s[0] in "'\"":
        q = s[0]
        if not s.endswith(q) or len(s) < 2:
            raise YamlError(f"unterminated string: {s}")
        body = s[1:-1]
        return body.replace("''", "'") if q == "'" else bytes(body, "utf-8").decode("unicode_escape")
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [] if not inner else [_scalar(x) for x in _split_flow(inner)]
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1].strip()
        out = {}
        for part in _split_flow(inner) if inner else []:
            k, _, v = part.partition(":")
            out[_scalar(k)] = _scalar(v)
        return out
    if re.fullmatch(r"[-+]?\d+", s):
        return int(s)
    if re.fullmatch(r"[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?", s):
        return float(s)
    return s


def _split_flow(s: str) -> list[str]:
    parts, depth, cur, q = [], 0, "", None
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = None
            continue
        if ch in "'\"":
            q = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return parts


def _strip_comment(line: str) -> str:
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def yaml_load(text: str):
    """Load the YAML subset used by kit profiles: block maps/lists, flow lists/maps, scalars, `|`/`>` blocks."""
    raw = text.splitlines()
    lines = []  # (indent, content, raw_index)
    for idx, l in enumerate(raw):
        if l.strip() in ("---",):
            continue
        c = _strip_comment(l)
        if c.strip():
            if "\t" in l[: len(l) - len(l.lstrip())]:
                raise YamlError(f"tab indentation at line {idx + 1}")
            lines.append((len(c) - len(c.lstrip()), c.strip(), idx))
    pos = 0

    def block_scalar(style, parent_indent, raw_idx):
        nonlocal pos
        body, ind = [], None
        j = raw_idx + 1
        while j < len(raw):
            l = raw[j]
            if l.strip() == "":
                body.append("")
                j += 1
                continue
            li = len(l) - len(l.lstrip())
            if li <= parent_indent:
                break
            ind = li if ind is None else ind
            body.append(l[ind:])
            j += 1
        while pos < len(lines) and lines[pos][2] < j:
            pos += 1
        while body and body[-1] == "":
            body.pop()
        chomp_strip = style.endswith("-")
        if style.startswith(">"):
            txt = " ".join(x for x in body if x)
        else:
            txt = "\n".join(body)
        return txt if chomp_strip else txt + "\n"

    def parse(indent):
        nonlocal pos
        if pos >= len(lines):
            return None
        is_list = lines[pos][1].startswith("- ") or lines[pos][1] == "-"
        result = [] if is_list else {}
        while pos < len(lines):
            ind, content, ridx = lines[pos]
            if ind < indent:
                break
            if ind > indent:
                raise YamlError(f"unexpected indent at line {ridx + 1}: {content}")
            if is_list:
                if not (content.startswith("- ") or content == "-"):
                    raise YamlError(f"expected list item at line {ridx + 1}")
                item = content[1:].strip()
                pos += 1
                if not item:
                    result.append(parse(lines[pos][0]) if pos < len(lines) and lines[pos][0] > ind else None)
                elif re.match(r"^[^'\"\[{][^:]*:(\s|$)", item) or re.match(r"^['\"][^'\"]+['\"]:(\s|$)", item):
                    # "- key: value" -> mapping whose first key is inline; following keys at ind+2
                    sub_indent = ind + 2
                    lines.insert(pos, (sub_indent, item, ridx))
                    result.append(parse(sub_indent))
                else:
                    result.append(_scalar(item))
            else:
                m = re.match(r"^(\"[^\"]*\"|'[^']*'|[^:]+?):(\s+(.*))?$", content)
                if not m:
                    raise YamlError(f"expected 'key: value' at line {ridx + 1}: {content}")
                key = _scalar(m.group(1))
                val = (m.group(3) or "").strip()
                pos += 1
                if val in ("|", "|-", ">", ">-"):
                    result[key] = block_scalar(val, ind, ridx)
                elif val == "":
                    if pos < len(lines) and lines[pos][0] > ind:
                        result[key] = parse(lines[pos][0])
                    elif pos < len(lines) and lines[pos][0] == ind and lines[pos][1].startswith("- "):
                        result[key] = parse(ind)  # list at same indent as key (common style)
                    else:
                        result[key] = None
                else:
                    result[key] = _scalar(val)
        return result

    data = parse(lines[0][0]) if lines else None
    if pos < len(lines):
        raise YamlError(f"trailing content at line {lines[pos][2] + 1}")
    return data


def load_yaml_file(path: Path):
    return yaml_load(Path(path).read_text())


# ----------------------------------------------------------------------------------------------- JSON schema subset
_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list,
          "object": dict, "null": type(None)}


def validate(instance, schema: dict, path: str = "$") -> list[str]:
    """Validate against the JSON Schema subset used by kit schemas (draft 2020-12 keywords). Returns errors."""
    errs: list[str] = []
    t = schema.get("type")
    if t:
        types = t if isinstance(t, list) else [t]
        ok = False
        for tt in types:
            py = _TYPES[tt]
            if isinstance(instance, bool) and tt in ("integer", "number"):
                continue
            if isinstance(instance, py):
                ok = True
        if not ok:
            return [f"{path}: expected {t}, got {type(instance).__name__}"]
    if "const" in schema and instance != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in {schema['enum']}")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errs.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: > maximum {schema['maximum']}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errs.append(f"{path}: more than {schema['maxItems']} items")
        if "items" in schema:
            for i, it in enumerate(instance):
                errs += validate(it, schema["items"], f"{path}[{i}]")
    if isinstance(instance, dict):
        for r in schema.get("required", []):
            if r not in instance:
                errs.append(f"{path}: missing required '{r}'")
        props = schema.get("properties", {})
        for k, v in instance.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected property '{k}'")
    return errs


# ----------------------------------------------------------------------------------------------- misc
def is_test_path(path: str) -> bool:
    p = path.replace("\\", "/")
    name = p.rsplit("/", 1)[-1]
    return (name.startswith("test_") and name.endswith(".py")) or name.endswith("_test.py") \
        or name.endswith("_test.go") or re.search(r"\.(test|spec)\.[cm]?[jt]sx?$", name) is not None \
        or "/tests/" in f"/{p}" or "/__tests__/" in f"/{p}"


def die(msg: str, code: int = 2):
    print(f"gates: {msg}", file=sys.stderr)
    raise SystemExit(code)
