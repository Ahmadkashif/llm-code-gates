# Phase 6 — verification log (2026-10-15)

Machine: 16-core / 31 GB Linux workstation, no NVIDIA GPU, no LLM gateway. Tools came from project-local,
checksum-verified binaries and venvs under `../tools/`. Heavy work was run with `nice`. Nothing was installed on the
host, no container was built or run, and no service was touched.

## Order of work (and what each step taught)

1. **Sample service written from scratch** (`../sample-service/`, its own git repo).
   - It is a stdlib Python HTTP service, parcel-quote: `/up`, `POST /v1/quote` (weight bands × zone, quantity and
     promo discounts, Decimal money), `GET /v1/quote/<id>` (SQLite), a token-bucket rate limiter.
   - 29 tests: unit, a Hypothesis property test, and integration tests against a real HTTP server.
   - Its own `Taskfile.yml` implements `check:fast` / `check` / `ci` / `image`.
   - Not derived from the kit corpus or #3's template; only #3's `agent-gate.sh` and the settings example were
     copied, as the integration point.
2. **Baseline before the kit** (`proof-linux/q12-contract/00-baseline-before-kit.txt`): all green. `check:fast`
   0.9 s, `check` 11.9 s, `ci` 14.4 s (image skipped: `SKIP_IMAGE=1`, no Docker approval). Getting there surfaced
   three template-level problems, recorded in backlog items 20–22:
   - unit-only coverage (77%) is below an 85% floor that counted integration tests; the floor was set to 75;
   - osv-scanner's transitive resolution of `requirements-dev.txt` assumed pygments 2.9.0 (2 CVEs); fixed by pinning
     the transitive dependency;
   - `zizmor --offline .forgejo/workflows/` collects no inputs (exit 3) and needs the file list;
   - actionlint needs the Forgejo runner labels in a config.
3. **Kit added following only `kit/README.md`** (`proof-linux/q12-contract/01..03`). Two README/kit defects were
   found and fixed. These are the value of a "README-only" install test:
   - (a) the repo's own `ruff check .` linted the vendored kit and failed. Fix: README step 4 now says to exclude
     `gates/` from repo-wide tools, and the kit got its own `ruff.toml` and real lint fixes (B023, B904, …);
   - (b) the kit's checks scanned the vendored kit itself. The copyleft regex inside `licence_check.py` blocked, and
     the kit's Docker hash locks triggered fresh-release warnings. Fix: `gateslib.skipped()` excludes `gates/` and
     `.gates/` from every check.

   After the fixes: `task gates:selftest` passes 27/27 tests (72 s), and `task check` passes 23 s in total, with
   `gates:deterministic` taking 10.0 s. No contract task was renamed. The wiring is 9 added lines
   (`02-taskfile-wiring.diff`).
4. **Change sets** (`make_changesets.py`):
   - 28 hand-written: 17 defective covering every RQ1 category the kit claims, plus 11 clean.
   - 3 produced by real headless Claude Code sessions (`claude -p --model haiku`, $1 budget cap, scratch clones,
     hooks off, allowed tools limited to Read/Edit/Write/Glob/Grep and pytest/git-diff/status). These were reviewed
     line by line before labelling; all three were correct, so they are labelled clean.
   - Labels were committed to `main` at `ba3e9ee` (2026-10-15T13:16) **before any gate ran on any change set**
     (`proof-linux/q18-measurement-preregistration.txt`).
5. **Corpus run** (`run_corpus.py`): for each change set in a fresh worktree,
   - the contract tasks (`check:fast`, `check`, `ci`);
   - each kit layer (`gates:fast`, `gates:deterministic`, `gates:server`), and each repo task on its own;
   - the stub LLM review, 3 times.

   Scored by `score_corpus.py` → `results-summary.md`.
6. **Q14/Q15/Q17 proofs.**
   - Q14: the real HTTP client against a local mock endpoint with injected faults.
   - Q15: offline under an audit-hook network guard. The first attempt failed 1 test because the dead proxy also
     captured loopback calls; fixed with `no_proxy`, and the proxy behaviour is now documented in the README.
   - Q17: two real headless Claude Code sessions with `agent-gate.sh`.

## Results v0.1 (pre-registered run; `results-summary-v0.1.md`)

Smoke test, n = 31 (17 defective, 14 clean).
- **Contract (what the agent or CI experiences):** 16/17 defective change sets blocked. 11 were first blocked at
  L0 `check:fast` and 5 at L2 `check`.
- **The one miss was predicted.** D13 is an uncovered edge-case bug (unbounded token-bucket refill). Its label said
  "EXPECTED MISS by deterministic gates".
- **3/14 clean change sets were blocked (false positives):**
  - **C05**: a table-driven `parametrize` refactor reduced the textual assert count from 4 to 1, so
    `test-integrity.assertions-removed` fired. The adversarial pass had predicted this.
  - **C07**: a new manual script `scripts/smoke.py` with no tests. `diff-mutation` scored 0/10 on code that no
    test executes, and the repo's own `audit` task (osv-scanner transitive resolution of `httpx`) reported old
    anyio/idna. That second cause is a repo-task finding, not a kit one.
  - **A3** (agent): the requested multiplier change legitimately updated `tests/test_app.py`. The declared scope
    named only `quotesvc/pricing.py`, so `scope.out-of-scope-file` fired.
- **LLM review (stub):** advisory, never blocked. The 3 repeats were identical on 31/31 change sets.

## Tuning iteration → kit v0.2 (post-hoc; labelled as such everywhere)

This is the Tricorder loop: an analyzer with effective false positives is fixed before it is trusted. Each change is
principled, not fitted to one case, and has a kit regression test (K19, K20, `test_mutation_skips_unexecuted_script`):
1. `test-tamper` counts assertions × `parametrize` rows (C05). The new residual gaming risk is recorded in the
   adversarial table.
2. `scope-check`: test files outside the declared scope → `scope.out-of-scope-test` **warn**. Non-test files still
   block (A3).
3. `diff-mutation` mutates only added lines that the test suite executes. Unexecuted lines → inform, because
   `coverage-drop` owns untested code (C07).

The v0.2 re-run uses the *same* 31 change sets: their commits were cherry-picked onto the kit-v0.2 main as `cs2/*`,
with identical diffs. The labels are unchanged. Because the tuning saw these change sets, v0.2 numbers are optimistic
by construction. Only the v0.1 numbers are a pre-registered measurement.
