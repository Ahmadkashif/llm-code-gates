#!/usr/bin/env python3
"""dep-check: dependencies added since BASE_REF must exist on their registry and must not be suspiciously new.

Catches hallucinated packages ("slopsquatting" bait) before anything is installed. Only package METADATA is read
(PyPI JSON API, npm registry, Go module proxy); nothing is downloaded or executed.

Rules
  dependency.not-on-registry      added package does not exist                         -> block
  dependency.version-not-found    pinned version does not exist                        -> block
  dependency.too-new              package first published < GATES_DEP_MIN_AGE_DAYS ago   -> block
  dependency.fresh-release        pinned version published < GATES_DEP_COOLDOWN_DAYS ago  -> warn
  dependency.undeclared-import    python import that is not stdlib, local or declared   -> warn
  dependency.registry-unreachable lookup failed (fail-open unless GATES_DEP_FAIL_CLOSED=1) -> warn

Usage: dep_check.py [--base REF]   (env: BASE_REF, GATES_REGISTRY_FIXTURE=<json> for offline tests)
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import os
import re
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import gateslib as g  # noqa: E402

UA = "llm-code-gates-dep-check/0.1 (+https://github.com/Ahmadkashif/llm-code-gates)"
NOW = dt.datetime.now(dt.UTC)


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


# ------------------------------------------------------------------------------------------- manifest parsing
_REQ = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(?:(==|===)\s*([A-Za-z0-9.*+!_-]+))?")


def parse_requirement(spec: str):
    m = _REQ.match(spec)
    if not m:
        return None
    return norm(m.group(1)), (m.group(3) if m.group(2) else None)


def py_deps(files: dict[str, str]) -> dict[str, str | None]:
    deps: dict[str, str | None] = {}
    for path, text in files.items():
        name = path.rsplit("/", 1)[-1]
        if name == "pyproject.toml":
            try:
                data = tomllib.loads(text)
            except tomllib.TOMLDecodeError:
                continue
            specs = list(data.get("project", {}).get("dependencies", []))
            for grp in data.get("project", {}).get("optional-dependencies", {}).values():
                specs += grp
            for grp in data.get("dependency-groups", {}).values():
                specs += [s for s in grp if isinstance(s, str)]
            for s in specs:
                r = parse_requirement(s)
                if r:
                    deps[r[0]] = r[1]
        else:  # requirements*.txt
            for line in text.splitlines():
                line = line.split("#", 1)[0].strip()
                if not line or line.startswith(("-", "git+", "http:", "https:", ".", "/")):
                    continue
                r = parse_requirement(line)
                if r:
                    deps[r[0]] = r[1]
    return deps


def npm_deps(text: str) -> dict[str, str | None]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    out = {}
    for key in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        for n, v in (data.get(key) or {}).items():
            ver = v if re.fullmatch(r"\d+\.\d+\.\d+[^\s]*", str(v)) else None
            out[n] = ver
    return out


def go_deps(text: str) -> dict[str, str | None]:
    out, in_block = {}, False
    for line in text.splitlines():
        s = line.split("//", 1)[0].strip()
        if s.startswith("require ("):
            in_block = True
            continue
        if in_block and s == ")":
            in_block = False
            continue
        if s.startswith("require "):
            s = s[len("require "):]
        elif not in_block:
            continue
        parts = s.split()
        if len(parts) >= 2:
            out[parts[0]] = parts[1]
    return out


def manifests(root: Path, ref: str | None, paths: list[str]):
    """Return {ecosystem: {name: version}} for the given manifest paths at ref (None = working tree)."""
    py_files, res = {}, {"pypi": {}, "npm": {}, "go": {}}
    for p in paths:
        text = g.file_at(ref, p, cwd=root)
        if text is None:
            continue
        name = p.rsplit("/", 1)[-1]
        if name == "package.json":
            res["npm"].update(npm_deps(text))
        elif name == "go.mod":
            res["go"].update(go_deps(text))
        else:
            py_files[p] = text
    res["pypi"].update(py_deps(py_files))
    return res


def is_manifest(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    if "node_modules/" in path:
        return False
    return name in ("pyproject.toml", "package.json", "go.mod") or bool(re.fullmatch(r"requirements[\w.-]*\.txt", name))


# ------------------------------------------------------------------------------------------- registry lookups
class Registry:
    def __init__(self, root: Path, cfg: dict):
        self.cache_path = root / ".gates" / "cache" / "registry.json"
        self.ttl = float(cfg.get("GATES_DEP_CACHE_HOURS", "24")) * 3600
        self.timeout = float(cfg.get("GATES_DEP_TIMEOUT_S", "6"))
        self.fixture = None
        fx = cfg.get("GATES_REGISTRY_FIXTURE")
        if fx:
            self.fixture = json.loads(Path(fx).read_text())
        try:
            self.cache = json.loads(self.cache_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            self.cache = {}
        self.lookups = 0

    def save(self):
        if self.fixture is None:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self.cache, indent=0))

    def _get(self, url: str):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        self.lookups += 1
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read().decode()
                return 200, body
        except urllib.error.HTTPError as e:
            return e.code, ""

    def info(self, eco: str, name: str) -> dict:
        """{'exists': bool, 'created': iso|None, 'versions': {ver: iso}} or {'error': str}."""
        key = f"{eco}:{name}"
        if self.fixture is not None:
            return self.fixture.get(key, {"exists": False, "versions": {}, "created": None})
        c = self.cache.get(key)
        if c and time.time() - c.get("_t", 0) < self.ttl:
            return c
        try:
            res = getattr(self, f"_{eco}")(name)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            return {"error": f"{type(e).__name__}: {e}"}
        res["_t"] = time.time()
        self.cache[key] = res
        return res

    def _pypi(self, name):
        code, body = self._get(f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json")
        if code == 404:
            return {"exists": False, "versions": {}, "created": None}
        if code != 200:
            raise ValueError(f"HTTP {code}")
        d = json.loads(body)
        versions = {}
        for v, files in d.get("releases", {}).items():
            times = [f["upload_time_iso_8601"] for f in files if f.get("upload_time_iso_8601")]
            if times:
                versions[v] = min(times)
        created = min(versions.values()) if versions else None
        return {"exists": True, "versions": versions, "created": created}

    def _npm(self, name):
        code, body = self._get(f"https://registry.npmjs.org/{urllib.parse.quote(name, safe='@')}")
        if code == 404:
            return {"exists": False, "versions": {}, "created": None}
        if code != 200:
            raise ValueError(f"HTTP {code}")
        d = json.loads(body)
        t = d.get("time", {})
        versions = {v: t[v] for v in d.get("versions", {}) if v in t}
        return {"exists": True, "versions": versions, "created": t.get("created")}

    def _go(self, name):
        esc = re.sub(r"[A-Z]", lambda m: "!" + m.group(0).lower(), name)
        code, body = self._get(f"https://proxy.golang.org/{esc}/@v/list")
        if code in (404, 410):
            return {"exists": False, "versions": {}, "created": None}
        if code != 200:
            raise ValueError(f"HTTP {code}")
        versions = {}
        for v in [x for x in body.split() if x][:200]:
            c2, b2 = self._get(f"https://proxy.golang.org/{esc}/@v/{v}.info")
            if c2 == 200:
                versions[v] = json.loads(b2).get("Time")
        if not versions:  # pseudo-version only modules
            c2, b2 = self._get(f"https://proxy.golang.org/{esc}/@latest")
            if c2 != 200:
                return {"exists": False, "versions": {}, "created": None}
            j = json.loads(b2)
            versions[j["Version"]] = j.get("Time")
        created = min(t for t in versions.values() if t) if any(versions.values()) else None
        return {"exists": True, "versions": versions, "created": created}


def age_days(iso: str | None) -> float | None:
    if not iso:
        return None
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.UTC)
    return (NOW - t).total_seconds() / 86400


# ------------------------------------------------------------------------------------------- python imports
def local_modules(root: Path) -> set[str]:
    mods = set()
    for base in (root, root / "src"):
        if not base.is_dir():
            continue
        for p in base.iterdir():
            if p.suffix == ".py":
                mods.add(p.stem)
            elif p.is_dir() and ((p / "__init__.py").exists() or any(p.glob("*.py"))):
                mods.add(p.name)
    return mods


def imports_in_added(root: Path, base: str, paths: list[str]) -> list[tuple[str, int, str]]:
    """(path, line, top-level module) for import statements on added lines of python files."""
    res = []
    added = g.added_lines(base, cwd=root, paths=[p for p in paths if p.endswith(".py")])
    for path, lines in added.items():
        text = g.file_at(None, path, cwd=root)
        if text is None:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if getattr(node, "lineno", None) not in lines:
                continue
            if isinstance(node, ast.Import):
                for a in node.names:
                    res.append((path, node.lineno, a.name.split(".")[0]))
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                res.append((path, node.lineno, node.module.split(".")[0]))
    return res


# ------------------------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=os.environ.get("BASE_REF", "origin/main"))
    a = ap.parse_args(argv)
    root = g.repo_root()
    cfg = g.config(root)
    base = g.resolve_base(a.base, cwd=root)
    min_age = float(cfg.get("GATES_DEP_MIN_AGE_DAYS", "30"))
    cooldown = float(cfg.get("GATES_DEP_COOLDOWN_DAYS", "7"))
    fail_closed = cfg.get("GATES_DEP_FAIL_CLOSED", "0") == "1"
    changed = g.changed_files(base, cwd=root)
    manifest_paths = [p for p in changed if is_manifest(p)]
    all_manifests = [p for p in g.repo_files(cwd=root, untracked=False) if is_manifest(p)]
    findings: list[g.Finding] = []
    reg = Registry(root, cfg)

    before = manifests(root, base, manifest_paths)
    after = manifests(root, None, manifest_paths)
    checked = 0
    for eco in ("pypi", "npm", "go"):
        for name, ver in after[eco].items():
            if name in before[eco] and before[eco][name] == ver:
                continue  # unchanged
            checked += 1
            mpath = next((p for p in manifest_paths
                          if name.lower() in (g.file_at(None, p, cwd=root) or "").lower().replace("_", "-")),
                         manifest_paths[0] if manifest_paths else "")
            info = reg.info(eco, name)
            if "error" in info:
                findings.append(g.Finding("dep-check", "dependency.registry-unreachable", "dependency", "medium",
                                          f"could not verify {eco} package '{name}': {info['error']}", mpath,
                                          evidence=name, level="block" if fail_closed else "warn"))
                continue
            if not info.get("exists"):
                findings.append(g.Finding("dep-check", "dependency.not-on-registry", "dependency", "critical",
                                          f"{eco} package '{name}' does not exist on the registry (hallucinated "
                                          "name? anyone could register it later)", mpath, evidence=f"{eco}:{name}",
                                          level=g.level_for(cfg, "dependency.not-on-registry", "block")))
                continue
            age = age_days(info.get("created"))
            if age is not None and age < min_age:
                findings.append(g.Finding("dep-check", "dependency.too-new", "dependency", "high",
                                          f"{eco} package '{name}' was first published {age:.1f} days ago "
                                          f"(< {min_age:g}); new names are the slopsquatting attack surface",
                                          mpath, evidence=f"{eco}:{name}",
                                          level=g.level_for(cfg, "dependency.too-new", "block")))
            if ver:
                vers = info.get("versions", {})
                vkey = ver.lstrip("v") if eco == "npm" else ver
                if vkey not in vers and ver not in vers:
                    findings.append(g.Finding("dep-check", "dependency.version-not-found", "dependency", "high",
                                              f"{eco} package '{name}' has no version {ver}", mpath,
                                              evidence=f"{eco}:{name}=={ver}",
                                              level=g.level_for(cfg, "dependency.version-not-found", "block")))
                else:
                    vage = age_days(vers.get(vkey) or vers.get(ver))
                    if vage is not None and vage < cooldown:
                        findings.append(g.Finding("dep-check", "dependency.fresh-release", "dependency", "low",
                                                  f"{eco} {name}=={ver} was released {vage:.1f} days ago "
                                                  f"(cooldown {cooldown:g} d)", mpath, evidence=f"{eco}:{name}=={ver}",
                                                  level=g.level_for(cfg, "dependency.fresh-release", "warn")))
    # undeclared python imports on added lines
    declared = set(manifests(root, None, all_manifests)["pypi"])
    aliases = {norm(x.split("=", 1)[0]): norm(x.split("=", 1)[1]) for x in g.cfg_list(cfg, "GATES_IMPORT_ALIASES")
               if "=" in x}
    stdlib = set(sys.stdlib_module_names)
    local = local_modules(root) | set(g.cfg_list(cfg, "GATES_LOCAL_MODULES"))
    for path, line, mod in imports_in_added(root, base, changed):
        if mod in stdlib or mod in local or mod == "__future__":
            continue
        dist = aliases.get(norm(mod), norm(mod))
        if dist in declared:
            continue
        findings.append(g.Finding("dep-check", "dependency.undeclared-import", "dependency", "medium",
                                  f"import '{mod}' is not stdlib, not a local module and not a declared dependency",
                                  path, line, evidence=f"import {mod}",
                                  level=g.level_for(cfg, "dependency.undeclared-import", "warn")))
    reg.save()
    notes = g.apply_suppressions(findings, root)
    return g.emit("dep-check", findings, root, notes,
                  {"base": base[:12], "deps_checked": checked, "registry_lookups": reg.lookups,
                   "min_age_days": min_age})


if __name__ == "__main__":
    sys.exit(main())
