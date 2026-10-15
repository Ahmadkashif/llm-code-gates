#!/usr/bin/env python3
"""dup-check: blocks of >= GATES_DUP_MIN_LINES added lines that duplicate code elsewhere in the repo.

Rule  duplication.copied-block   (default warn; duplication is a maintainability signal, not a defect)
Normalisation: strip whitespace, drop blank and comment-only lines. Test files are ignored on both sides.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import gateslib as g  # noqa: E402

EXT = (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rs")


def normalised(text: str):
    out = []
    for i, l in enumerate(text.splitlines(), 1):
        s = l.strip()
        if not s or re.match(r"^(#|//|/\*|\*)", s) or s in ('"""', "'''"):
            continue
        out.append((i, s))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default=os.environ.get("BASE_REF", "origin/main"))
    a = ap.parse_args(argv)
    root = g.repo_root()
    cfg = g.config(root)
    base = g.resolve_base(a.base, cwd=root)
    k = int(cfg.get("GATES_DUP_MIN_LINES", "6"))
    files = [p for p in g.repo_files(cwd=root)
             if p.endswith(EXT) and not g.is_test_path(p) and (root / p).is_file()]
    index: dict[str, list[tuple[str, int]]] = {}
    norm = {}
    for p in files:
        n = normalised((root / p).read_text(errors="replace"))
        norm[p] = n
        for j in range(len(n) - k + 1):
            h = hashlib.sha1("\n".join(s for _, s in n[j:j + k]).encode()).hexdigest()
            index.setdefault(h, []).append((p, n[j][0]))
    F = []
    added = g.added_lines(base, cwd=root, paths=[p for p in g.changed_files(base, cwd=root) if p in norm])
    for p, lines in added.items():
        n = norm.get(p, [])
        reported_until = 0
        for j in range(len(n) - k + 1):
            win = n[j:j + k]
            if win[0][0] <= reported_until or not all(ln in lines for ln, _ in win):
                continue
            h = hashlib.sha1("\n".join(s for _, s in win).encode()).hexdigest()
            others = [(q, ln) for q, ln in index.get(h, []) if not (q == p and ln == win[0][0])]
            if others:
                q, ln = others[0]
                F.append(g.Finding("dup-check", "duplication.copied-block", "duplication", "low",
                                   f"{k}+ added lines duplicate {q}:{ln}", p, win[0][0], f"{q}:{ln}",
                                   level=g.level_for(cfg, "duplication.copied-block", "warn")))
                reported_until = win[-1][0]
    notes = g.apply_suppressions(F, root)
    return g.emit("dup-check", F, root, notes, {"base": base[:12], "files_indexed": len(files), "window": k})


if __name__ == "__main__":
    sys.exit(main())
