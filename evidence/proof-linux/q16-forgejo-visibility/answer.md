# Q16 — where the advisory report is visible in a Forgejo PR without a token

Status: **answered from primary docs (Phase 2 notes, rq03 Part C); snippets linted (ci-snippets-lint.txt);
live Forgejo PR NOT RUN** (#3's lab VMs are stopped; resuming them is a live-host change — commands in STATUS.md).

| Channel | Token needed? | Works on Forgejo? | Kit support |
|---|---|---|---|
| Job log (PR check → details) | no | yes | `llm_review.py` prints the summary to stdout; `task gates:report` cats `llm-review.md` |
| Check status | no | yes | deterministic gates fail the required check; LLM review exits 0 unless a category is promoted |
| Artifact | no | yes, via `code.forgejo.org/forgejo/upload-artifact@v4|v5` (upstream `actions/upload-artifact` v4+ fails) | `ci/forgejo-step.yml` uploads `.gates/out/` (JSONL + SARIF + md), SHA-pinned (v5 = cb8afe72…) |
| Job summary (`$FORGEJO_STEP_SUMMARY` / `$GITHUB_STEP_SUMMARY`) | no | only Forgejo ≥ v17.0 + Runner ≥ 13.2 (PR #14076 merged 2026-09-07; v16.0.6 stable has none) | `llm_review.py` appends `llm-review.md` when either variable is set |
| SARIF / code-scanning UI | — | **no** (Forgejo has none) | SARIF still produced for download / other tools |
| Inline PR comments | **yes** (bot token) | — | out of scope (backlog 18) |

Gotchas confirmed: job-level `continue-on-error` and `permissions:` are ignored (the advisory step must exit 0
itself — it does); runner v13 removed `::set-output`.
