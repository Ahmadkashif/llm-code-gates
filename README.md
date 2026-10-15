# llm-code-gates

This repo holds a quality-gate kit for **LLM-written code**, the research behind it, and the evidence that it works.
It is a working proof of concept, verified offline on a synthetic sample service. It is not a product.

- **`kit/`** is the template. It drops into any repo that uses a `Taskfile.yml` check contract (`check:fast` /
  `check` / `ci` / `image`) and **renames no contract task**: the contract tasks call namespaced `gates:*` tasks.
  - **Deterministic gates block.** They catch:
    - test tampering against `BASE_REF` (deleted, weakened, skipped or tautological tests, test-config deselection);
    - hallucinated and brand-new dependencies (PyPI / npm / Go-proxy metadata);
    - 12 vendored MIT Semgrep rules for LLM-typical patterns;
    - copyleft text and scope violations;
    - coverage drop, and diff-scoped mutation testing.
  - **LLM review is advisory.** It uses 7 copy-pasteable prompts with JSON schemas and runs against any
    OpenAI-compatible endpoint. The pipeline is find → ground → vote → verify → dedup → floors → suppressions (with
    expiry) → baseline. It writes JSONL + SARIF + markdown and exits 0 unless a judge profile promotes a category to
    blocking (default: none).
  - **A stub judge** and a **mock OpenAI-compatible server** make everything testable offline, with no model at all.
- **`examples/parcel-quote/`** is a small Python HTTP service written from scratch to verify the kit. It has its own
  contract Taskfile and the kit wired in (`gates/` is a symlink to `../../kit`).
  `verification/` holds **31 pre-registered change sets**: 17 defective, 14 clean, 3 of them produced by real Claude
  Code sessions. Each is a `.patch` against the adoption commit, with `labels.json` committed before any gate ran.
- **`evidence/`** holds command transcripts per question (`proof-linux/`), the corpus runner, per-change-set
  results and logs, and the scoring.
- **`research/`** holds the research: scope, discovery notes (about 200 sources with access dates), the deep dive,
  the prompt critique (v1 drafts plus the recorded adversarial critique), synthesis, build spec, sources and backlog.

## Quick start (offline)

The example is meant to be its own repository. Copy it out, resolving the `gates` symlink, and `git init` it:
```bash
cp -rL examples/parcel-quote /tmp/parcel-quote && cd /tmp/parcel-quote
git init -q -b main && git add -A && git -c user.name=me -c user.email=me@example.invalid commit -qm base
python3 -m venv /tmp/pq-venv && . /tmp/pq-venv/bin/activate && pip install -r requirements-dev.txt  # venv outside the repo
# tools on PATH: task, semgrep (>= 1.178), gitleaks, osv-scanner, actionlint, zizmor (versions in kit/README.md)
bash gates/detect-env.sh                       # read-only report + suggested profiles
python3 gates/render.py --check                # validate profiles, prompts, schemas
task gates:selftest                            # the kit's own tests (stub judge + mock endpoint, offline)
task check:fast BASE_REF=HEAD                  # L0 — what the agent hook runs
git apply verification/changesets/D04.patch    # weakened assertions ...
task check:fast BASE_REF=HEAD                  # ... are blocked by gates:fast (test-integrity.assertion-weakened)
```
To add the kit to your own repo, follow `kit/README.md`. That README is the only document used for the sample
integration.

## What was verified (smoke test on one machine; n stated; not a benchmark)

| Question | Result | Evidence |
|---|---|---|
| Q12 Kit added without renaming any contract task; layer budgets | **VERIFIED.** The wiring is 9 lines (an `includes:` block plus one `task: gates:*` line in each of `check:fast`, `check` and `ci`). Max wall time over 31 change sets: `check:fast` 4.8 s (< 60), `check` 32.5 s (< 120), `ci` 53.2 s (< 600; image build skipped) | `evidence/proof-linux/q12-contract/`, `evidence/phase-6/results-summary-v0.2.md` |
| Q13 Deterministic checks fire on seeded cases with zero FP on clean ones | **VERIFIED for the kit corpus** (20/20 cases) and the 12 Semgrep rule tests. **Sample corpus, pre-registered v0.1:** 16/17 defective blocked; 3/14 clean blocked (FPs). **v0.2, after one documented tuning pass on the same corpus (optimistic):** 16/17 blocked; kit gates block 0/14 clean; 1/14 clean is still blocked by the repo's own osv-scanner task | `evidence/proof-linux/q13-deterministic/`, `evidence/phase-6/log.md` |
| Q14 `llm_review` against any OpenAI-compatible endpoint; full pipeline; JSONL + SARIF + summary; exit only for promoted categories | **VERIFIED against a local mock endpoint** with fault injection: retry on 503, think blocks, non-JSON → repair, wrong key → "unavailable" with exit 0, the key never appears in outputs, a promoted category → exit 1. **Not verified with a real model** | `evidence/proof-linux/q14-llm-review/` |
| Q15 Stub judge makes the kit testable offline | **VERIFIED.** 28/28 kit tests pass under a network guard; the 3 stub repeats are identical | `evidence/proof-linux/q15-stub-offline/` |
| Q16 Advisory report visible in a Forgejo PR without a token | **Answered from Forgejo docs; snippets linted.** Visible in the job log, the check status and an artifact (Forgejo's fork of upload-artifact); job summary only on Forgejo ≥ v17 with Runner ≥ 13.2; no SARIF UI. **Live PR NOT RUN** | `evidence/proof-linux/q16-forgejo-visibility/` |
| Q17 L0 in a real Claude Code session | **VERIFIED.** A kit gate (deleted test) blocked `git push` via the PreToolUse hook, and the Stop hook blocked finishing 3× before handing over to a human. In a second session the agent restored the test and the push succeeded | `evidence/proof-linux/q17-claude-code-l0/` |
| Q18 Measured per gate / per judge | **Deterministic gates and stub: measured** (per-gate tables). **local-8gb, local-48gb-plus and cloud: NOT RUN** | `evidence/phase-6/results-summary-v0.{1,2}.md` |

All numbers are a smoke test on one 16-core machine (n = 31 change sets: 17 defective, 14 clean). They are not a
benchmark. The stub judge measures the review **pipeline**, never model quality.

## NOT RUN (each needs the owner's approval or infrastructure that was not available)

| Item | Why | How to finish |
|---|---|---|
| `local-8gb` judge (≈4B model behind a home LLM gateway) | The machine used had no GPU and no gateway. A key and a GPU window need approval | `research/` STATUS commands: render with `--judge local-8gb`, set `GATES_JUDGE_*`, run `gates/review/llm_review.py` 3× per change set |
| `local-48gb-plus` and cloud judges | No endpoint; code leaves the host only with consent | same loop with `--judge local-48gb-plus` / `cloud-openai-compatible` |
| Forgejo PR (red PR blocked, advisory review visible) | The self-hosted Forgejo lab was stopped; resuming it is a live-host change | push `examples/parcel-quote` with `kit/ci/forgejo-step.yml` steps to a Forgejo with a `ci` runner; open PRs from D07 (red) and C04 (green) |
| Tool image (`kit/Dockerfile`) | Live Docker use not approved | `docker build -t llm-code-gates-tools:0.1 -f kit/Dockerfile kit && docker run --rm --cpus 2 --memory 3g -v "$PWD/examples/parcel-quote":/work -w /work -e SKIP_IMAGE=1 llm-code-gates-tools:0.1 task ci BASE_REF=HEAD` |

## What is deliberately excluded from this repo

- The private research brief and plan. They describe a private machine.
- Machine identifiers. Local paths, user names and the host name in transcripts are replaced by `<research>`,
  `<home>`, `<user>` and `<host>`.
- The sample service's git history. Change sets are shipped as patches.
- `.gitleaksignore` lists two hits. Both are the **deliberately seeded synthetic secret** of change set D17 ("hard-coded
  secret"), which exists to prove the repo's gitleaks task catches it. The value was generated for the test and is
  not valid anywhere.

## Licence

MIT (see `LICENSE`). The Semgrep rules in `kit/semgrep/` were written for this kit. No Semgrep Registry rules are
included, because the Semgrep Rules License v1.0 forbids redistribution.
