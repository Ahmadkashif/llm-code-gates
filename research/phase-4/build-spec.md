# Phase 4 — Build spec (checkpoint; waived by the "Research autonomously" directive, posted to issue #15)

The kit is `../kit/`, vendored into a repo as `gates/`. Its shape follows the brief's proposal, with the
deviations listed at the end.

| File | Purpose | Expected output | How it is checked |
|---|---|---|---|
| `lib/gateslib.py` | git diff helpers, the Finding record, suppressions with expiry, baselines, JSONL/SARIF writers, YAML-subset loader, JSON-Schema-subset validator | — | `tests/test_lib.py`: YAML equals PyYAML on every profile and the Taskfile; the validator agrees with `jsonschema` |
| `checks/test_tamper.py` | AST diff of tests vs BASE_REF (Python); count diff for JS/TS/Go; test config weakening | findings `test-integrity.*` | corpus K01–K05, K17 fire; K13/K14/K16 (move, delete-with-code, parametrize) do not block |
| `checks/dep_check.py` | new deps must exist on PyPI/npm/Go proxy and be ≥ 30 days old; undeclared imports | `dependency.*` | corpus K06/K07 fire; K15 clean; live PyPI in phase 6 |
| `checks/semgrep_gate.py` + `semgrep/llm-python.yml` | 12 MIT rules for LLM-typical patterns; only added lines block | `gates.py.*` | `semgrep --test` 12/12; corpus K09/K10 fire, K18 clean |
| `checks/scope_check.py` | files outside the declared task scope | `scope.*` | corpus K11 |
| `checks/licence_check.py` | copyleft markers on added lines; dependency licence deny list | `licence.*` | corpus K08 |
| `checks/dup_check.py` | copied blocks ≥ 6 normalised lines | `duplication.copied-block` (warn) | phase-6 sample |
| `checks/coverage_drop.py` | total coverage vs a `git archive` of BASE; diff coverage | `test-adequacy.coverage-*` | `tests/test_heavy.py` |
| `checks/diff_mutation.py` | AST mutants on added lines only, ≤ 20, niced, time-boxed; native-tool delegation for other stacks | score + survivors | `tests/test_heavy.py`: weak tests block, strong tests pass |
| `review/llm_review.py`, `client.py`, `parse.py` | the find → ground → vote → verify → dedup → floor → suppress → baseline pipeline against any OpenAI-compatible endpoint | `.gates/out/llm-review.{jsonl,events.jsonl,sarif,md}`; exit 0 unless a promoted category | `tests/test_review.py` |
| `review/stub_judge.py`, `review/mock_openai_server.py` | offline judge; local HTTP endpoint with fault injection | — | `tests/test_review.py`: think blocks, 503 retry, garbage → repair, wrong key → unavailable, key never in outputs |
| `prompts/*.md`, `schemas/*.json` | 7 prompts (v2) + 2 schemas | — | `render.py --check`, `tests/test_review.py` (required sections, loadable) |
| `profiles/stacks/{python,typescript,go}.yml` | commands per language | rendered into `.gates/config.env` | python verified in phase 6; TS/Go templates only |
| `profiles/judges/{stub,local-8gb,local-48gb-plus,cloud-openai-compatible}.yml` | minimum VRAM/RAM/context, prompts, samples/votes, floors, blocking categories (default `[]`) | rendered into `.gates/judge.json` | `tests/test_render.py`: small-tier prompt guard, VRAM guard, blocking needs verify |
| `render.py` | #3's pattern: stdlib, budget checks, `--check` | `.gates/{config.env,judge.json,.gitignore}` | `tests/test_render.py` |
| `detect-env.sh` | read-only host/repo report, suggests profiles | text | shellcheck clean; run in phase 6 |
| `run.py` | runs a layer's checks, no fail-fast, per-check wall time, merged SARIF | `summary-<layer>.json`, `gates-<layer>.sarif` | phase 6 timings |
| `Taskfile.gates.yml` | `gates:fast/deterministic/mutation/llm-review/server/report/selftest/render` | — | phase 6 (Q12) |
| `Dockerfile`, `docker/*` | pinned tool image (binaries by sha256, wheels by `--require-hashes`) | image | hadolint clean; hash locks resolve (pip `--dry-run --require-hashes`); **build/run NOT RUN** (Q6) |
| `ci/forgejo-step.yml`, `ci/github-step.yml`, `ci/actionlint.yaml` | reporting steps (log + artifact; GitHub also step summary + SARIF); SHA-pinned | — | actionlint + zizmor (`proof-linux/q16-*`) |
| `corpus/cases.py`, `corpus/registry-fixture.json` | the kit's own labelled seeded cases | — | `tests/test_corpus.py` |
| `tests/` | stdlib unittest, offline | — | `task gates:selftest` |

**Deviations from the brief's proposed shape, with reasons:**
- Added `run.py`. Task stops at the first failing command, and a gate layer should report every check plus a wall
  time each.
- Added `lib/`, a single shared stdlib module.
- Added `docker/`, which holds the hash locks and the binary list (hadolint cannot parse RUN heredocs).
- The prompt library has 7 prompts, not "per dimension" only. The critique split tests into integrity and
  adequacy, and added a narrow single-pass prompt for 4B models.
- `coverage-drop` runs BASE via `git archive` into a temp dir instead of `git worktree`, so `.git` is never written.
- Profiles are YAML parsed by a stdlib subset loader, checked against PyYAML in tests, so no dependency is added.
- The LLM review in CI defaults to option (c): stub/keyless. The user decides (a)/(b)/(c).

**Verification plan (phase 6):**
- Build a brand-new sample service with its own contract Taskfile and add the kit following only this README.
- Commit ≥ 20 labelled change sets before any gate runs: ≥ 10 defective covering each RQ1 category the kit claims,
  ≥ 10 clean, and some produced by a real `claude -p` session.
- Run `task check:fast`, `task check` and `task ci` on each, recording catches, misses, FPs and wall time per gate.
- Run the stub review 3× and the mock-endpoint run.
- Run a real headless Claude Code L0 session.
- NOT RUN, with commands to finish them: local-8gb, cloud, Docker, Forgejo PR.
