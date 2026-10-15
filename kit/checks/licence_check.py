#!/usr/bin/env python3
"""licence-check: copyleft / foreign-copyright text pasted into the change, and new dependencies whose
declared licence is on the deny list.

Rules
  licence.copyleft-snippet     added lines carry a copyleft licence marker (GPL/AGPL/SSPL/...)   block
  licence.foreign-copyright    added "Copyright (c) <holder>" not matching GATES_LICENCE_OWNER   warn
  licence.denied-dependency    new dependency licence matches GATES_LICENCE_DENY                 block
  licence.unknown-dependency   new dependency has no machine-readable licence                    warn
Snippet-level provenance (code copied WITHOUT its header) needs a fingerprint database (ScanCode/SCANOSS);
this check only sees what is declared. See the kit README limits.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gateslib as g  # noqa: E402
import dep_check as dc  # noqa: E402

COPYLEFT = re.compile(r"SPDX-License-Identifier:\s*\(?\s*(A?GPL|LGPL|SSPL|EUPL|OSL|CC-BY-SA|CPAL|RPL)[-\w.+]*"
                      r"|GNU (Affero |Lesser )?General Public License|Server Side Public License"
                      r"|under the terms of the GNU", re.I)
COPYRIGHT = re.compile(r"Copyright\s*(\(c\)|©)?\s*(\d{4}([-, ]+\d{4})*)?\s*,?\s*(?P<holder>[A-Z][^\n*#/]{2,80})")


def pypi_licence(info: dict) -> str:
    return info.get("licence") or ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=os.environ.get("BASE_REF", "origin/main"))
    a = ap.parse_args(argv)
    root = g.repo_root()
    cfg = g.config(root)
    base = g.resolve_base(a.base, cwd=root)
    owner = cfg.get("GATES_LICENCE_OWNER", "").lower()
    deny = re.compile("|".join(re.escape(x) for x in g.cfg_list(cfg, "GATES_LICENCE_DENY", "AGPL,GPL,SSPL,EUPL"))
                      or "$^", re.I)
    F = []
    changed = g.changed_files(base, cwd=root)
    text_paths = [p for p in changed if not p.endswith((".png", ".jpg", ".gif", ".lock")) and
                  p.rsplit("/", 1)[-1] not in ("LICENSE", "LICENCE", "COPYING", "NOTICE", "THIRD_PARTY_NOTICES")]
    for path, lines in g.added_lines(base, cwd=root, paths=text_paths).items():
        for ln, text in lines.items():
            if COPYLEFT.search(text):
                F.append(g.Finding("licence-check", "licence.copyleft-snippet", "licence", "high",
                                   "copyleft licence text added — code copied from a copyleft project?", path, ln,
                                   text.strip()[:200], level=g.level_for(cfg, "licence.copyleft-snippet", "block")))
            m = COPYRIGHT.search(text)
            if m and m.group("holder") and owner and owner not in m.group("holder").lower():
                F.append(g.Finding("licence-check", "licence.foreign-copyright", "licence", "medium",
                                   f"copyright notice for '{m.group('holder').strip()}' added", path, ln,
                                   text.strip()[:200], level=g.level_for(cfg, "licence.foreign-copyright", "warn")))
    # dependency licences (PyPI only in this PoC; npm/go: use license-checker / go-licenses in the stack profile)
    mpaths = [p for p in changed if dc.is_manifest(p)]
    before, after = dc.manifests(root, base, mpaths), dc.manifests(root, None, mpaths)
    reg = dc.Registry(root, cfg)
    for name in [n for n in after["pypi"] if n not in before["pypi"]]:
        lic = licence_of(reg, name)
        if lic is None:
            continue  # does not exist: dep-check reports it
        if not lic:
            F.append(g.Finding("licence-check", "licence.unknown-dependency", "licence", "low",
                               f"pypi:{name} declares no licence", evidence=name,
                               level=g.level_for(cfg, "licence.unknown-dependency", "warn")))
        elif deny.search(lic) and not re.search(r"\bLGPL|Lesser", lic, re.I) or re.search(r"\bAGPL|Affero", lic):
            F.append(g.Finding("licence-check", "licence.denied-dependency", "licence", "high",
                               f"pypi:{name} licence '{lic}' is on the deny list", evidence=name,
                               level=g.level_for(cfg, "licence.denied-dependency", "block")))
    notes = g.apply_suppressions(F, root)
    return g.emit("licence-check", F, root, notes, {"base": base[:12]})


def licence_of(reg, name):
    if reg.fixture is not None:
        e = reg.fixture.get(f"pypi:{name}")
        return None if not e or not e.get("exists") else e.get("licence", "")
    import json
    import urllib.request
    try:
        req = urllib.request.Request(f"https://pypi.org/pypi/{name}/json", headers={"User-Agent": dc.UA})
        with urllib.request.urlopen(req, timeout=reg.timeout) as r:
            info = json.loads(r.read())["info"]
    except Exception:  # noqa: BLE001 - missing or unreachable: dep-check owns that verdict
        return None
    lic = info.get("license_expression") or ""
    if not lic:
        cls = [c.split("::")[-1].strip() for c in info.get("classifiers", []) if c.startswith("License ::")]
        lic = ", ".join(cls) or (info.get("license") or "")[:80]
    return lic


if __name__ == "__main__":
    sys.exit(main())
