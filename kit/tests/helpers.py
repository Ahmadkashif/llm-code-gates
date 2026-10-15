"""Test helpers: build throwaway git repos from corpus cases and run kit checks in them."""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "lib"))
sys.path.insert(0, str(KIT / "review"))
sys.path.insert(0, str(KIT / "corpus"))

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV}).stdout


def write(repo: Path, files: dict):
    for p, c in files.items():
        f = repo / p
        if c is None:
            f.unlink(missing_ok=True)
            continue
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(c)


def registry_fixture(tmp: Path) -> Path:
    data = json.loads((KIT / "corpus" / "registry-fixture.json").read_text())
    recent = (dt.datetime.now(dt.UTC) - dt.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = json.dumps(data).replace("2099-01-01T00:00:00Z", recent)
    p = tmp / "registry.json"
    p.write_text(text)
    return p


def make_repo(base: dict, change: dict | None = None, config: dict | None = None, commit_change=True) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="gates-test-"))
    repo = tmp / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    write(repo, base)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    git(repo, "checkout", "-qb", "change")
    cfg = {"GATES_REGISTRY_FIXTURE": str(registry_fixture(tmp)), **(config or {})}
    (repo / ".gates").mkdir()
    (repo / ".gates" / "config.env").write_text("".join(f"{k}={v}\n" for k, v in cfg.items()))
    (repo / ".gates" / ".gitignore").write_text("out/\ncache/\n")
    if change:
        write(repo, change)
        if commit_change:
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "change")
    return repo


def run_check(repo: Path, script: str, *args, env=None):
    p = subprocess.run([sys.executable, str(KIT / script), "--base", "main", *args], cwd=repo, capture_output=True,
                       text=True, env={**os.environ, **GIT_ENV, **(env or {})}, timeout=600)
    return p


def findings(repo: Path, check: str) -> list[dict]:
    f = repo / ".gates" / "out" / f"{check}.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text().splitlines() if '"event": "finding"' in l]


def cleanup(repo: Path):
    shutil.rmtree(repo.parent, ignore_errors=True)


def have_semgrep() -> bool:
    return shutil.which(os.environ.get("GATES_SEMGREP", "semgrep")) is not None
