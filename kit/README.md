# llm-code-gates kit

Quality gates for LLM-written code. It drops into any repo that uses the `Taskfile.yml` check contract
(`check:fast` / `check` / `ci` / `image`) without renaming a contract task. The contract tasks simply call the
kit's namespaced tasks.

- **Deterministic gates block.** They catch test tampering, hallucinated or brand-new dependencies, LLM-typical
  insecure patterns (vendored Semgrep rules), copyleft text, scope violations, coverage drop, and tests that don't
  constrain new code (diff-scoped mutation).
- **LLM review is advisory.** It uses a copy-pasteable prompt library with JSON schemas and runs against any
  OpenAI-compatible endpoint. The pipeline is find → verify → dedup → floors → suppressions → baseline. It exits 0
  unless a judge profile promotes a category to blocking, and that should only happen after the category has
  measured precision ≥ 90%.
- **A stub judge** makes everything testable offline, with no model at all.

```
 L0 agent hook (< 60 s)    task check:fast ─► gates:fast           test-tamper · dep-check · semgrep(changed) · scope
 L2 pre-push   (< 2 min)   task check      ─► gates:deterministic  + full semgrep · licence · duplication · coverage-drop
 L3 server CI  (< 10 min)  task ci         ─► gates:server         diff-mutation (blocks) · llm-review (advisory)
 L5 scheduled              full mutation run (mutmut/Stryker/cargo-mutants), dependency re-audit — repo's own tasks
```

## Requirements (stated minimums; nothing here is installed by the kit)

| Component | Minimum | Verified with | Needed for |
|---|---|---|---|
| Python | 3.11 (`tomllib`) | 3.12.3 | everything (kit is stdlib-only) |
| git | 2.30 | 2.43.0 | everything |
| go-task | 3.x with `includes` + `vars` | 3.54.0 | Taskfile integration |
| semgrep CE | 1.178.0 (LGPL-2.1 engine; kit rules are MIT) | 1.178.0 | `semgrep`, `semgrep-changed` |
| pytest + coverage.py | 8.0 / 7.0 | 9.1.1 / 7.16.2 | python stack: `coverage-drop`, `diff-mutation` |
| Network | HTTPS to pypi.org / registry.npmjs.org / proxy.golang.org | — | `dep-check` (metadata only; cache 24 h; fail-open → warn) |
| CPU / RAM for L3 | 1 core, RAM of your test suite | 16 cores / 31 GB box, niced | `diff-mutation` reruns the tests ≤ 20 times |
| Judge `stub` | none | — | offline pipeline tests |
| Judge `local-8gb` | 8 GB VRAM, 16 GB RAM, 8k context **set on the server** (`num_ctx`) | NOT RUN | ~4B model, one narrow prompt, unverified, advisory |
| Judge `local-48gb-plus` | 48 GB VRAM, 64 GB RAM, 32k context | NOT RUN | 30–120B model, all prompts + verifier |
| Judge `cloud-openai-compatible` | an API key; owner consent that code leaves the host | NOT RUN | frontier model |
| Docker (optional) | 25+ | Dockerfile linted only | pinned tool image (`Dockerfile`) |

Stack profiles: `python` (verified), `typescript` and `go` (templates, **not verified**).

## Install (into a repo that follows the contract)

1. **Vendor the kit**: copy this directory to `gates/` at the repo root. Then run `bash gates/detect-env.sh`
   (read-only), which prints the tools found, any GPU/VRAM, endpoint reachability, and suggested profiles.
2. **Optional site settings**: put them in `.gates/site.env`, one `NAME=value` setting per line (no credentials). Examples:
   `GATES_LICENCE_OWNER=Example Org`, `GATES_HOST_VRAM_GB=8`, `GATES_JUDGE_BASE_URL=https://gateway.example/v1`.
3. **Render**: `python3 gates/render.py --stack python --judge stub`. This writes `.gates/config.env`,
   `.gates/judge.json` and `.gates/.gitignore`. Commit them. `python3 gates/render.py --check` validates every
   profile, prompt and schema.
4. **Wire the contract.** Add the include, then append one line to each contract task. Never rename them.
   ```yaml
   includes:
     gates:
       taskfile: ./gates/Taskfile.gates.yml
       dir: .
       vars: {BASE_REF: '{{.BASE_REF}}'}
   tasks:
     check:fast:
       cmds:
         - ...existing commands...
         - task: gates:fast
     check:
       cmds:
         - ...existing commands...
         - task: gates:deterministic
     ci:
       cmds:
         - task: check
         - ...existing commands...
         - task: gates:server
   ```
   **Exclude the vendored kit from repo-wide tools.** The kit carries its own `ruff.toml`, its own tests and a
   deliberately insecure Semgrep test fixture (`gates/semgrep/llm-python.py`). For example:
   - `[tool.ruff] extend-exclude = ["gates"]` in `pyproject.toml`;
   - `--exclude gates` on a repo-wide `semgrep scan`;
   - type-check only your own package.
   The kit's checks skip `gates/` and `.gates/` by themselves.
5. **Run the self-test**: `task gates:selftest` (offline). Then `task check:fast BASE_REF=origin/main`.
6. **Agent hook (L0)**: no change needed. #3's `agent-gate.sh` runs `task check:fast` on Stop and `task check`
   before `git push`, so a kit gate failure keeps the agent working and blocks the push.
7. **CI**: copy the two reporting steps from `ci/forgejo-step.yml` (Forgejo) or `ci/github-step.yml`. The checks
   stay in the Taskfile.

Outputs go to `.gates/out/` (gitignored):
- `<check>.jsonl` and `<check>.sarif` per check;
- `gates-<layer>.sarif` (merged) and `summary-<layer>.json` (per-check exit code and wall time);
- `llm-review.md` (human summary) and `llm-review.events.jsonl` (every model call and every filtering decision).

## Checks and rule ids

| Check | Rules (default level) | Layer |
|---|---|---|
| `test-tamper` | (assertion counts are × `parametrize` rows) test-file-deleted, test-removed, assertions-removed, assertion-weakened, tautology, test-skipped, test-config-weakened (block); expectation-changed (warn); test-removed-with-code (inform) | L0+ |
| `dep-check` | not-on-registry, version-not-found, too-new < 30 d (block); fresh-release < 7 d, undeclared-import, registry-unreachable (warn) | L0+ |
| `semgrep` | 12 vendored rules `gates.py.*` (ERROR → block, WARNING → warn). Only findings on **added lines** block; pre-existing ones are inform | L0 (changed files), L2 |
| `scope-check` | out-of-scope-file when a scope is declared (block); out-of-scope-test, large-change (warn) | L0+ |
| `licence-check` | copyleft-snippet, denied-dependency (block); foreign-copyright, unknown-dependency (warn) | L2 |
| `dup-check` | copied-block ≥ 6 normalised lines (warn) | L2 |
| `coverage-drop` | coverage-drop > 0.5 pt vs BASE (block); diff-coverage < 70% (warn) | L2 |
| `diff-mutation` | mutation-score < 0.6 with ≥ 4 mutants on added lines the tests execute (block); surviving-mutant, unexecuted-lines (inform) | L3 |
| `llm-review` | `llm.<category>`: warn (confirmed) / inform (uncertain); block only for promoted categories | L3 (L2 by hand) |

Override any level in `.gates/site.env` and re-render. For example, `GATES_LEVEL_DEPENDENCY_TOO_NEW=warn` (the rule
id upper-cased, with `.` and `-` turned into `_`).

**Suppressions** go in `.gates/suppressions.json`. Every entry needs a `reason` and an `expires` date. Expired
entries stop suppressing, and the run reports them:
```json
{"suppressions": [{"rule": "gates.py.subprocess-shell-injection", "path": "scripts/release.py",
                   "reason": "constant command, reviewed 2026-10-15", "expires": "2027-01-15"}]}
```
A `fingerprint` can be given instead of `rule`/`path`. Fingerprints are stable across line moves.

**Baselines**: `python3 gates/review/llm_review.py --write-baseline` on `main` records the existing LLM findings,
and later runs report only new ones. Semgrep is diff-aware already.

**Scope**: write the task statement to `.gates/task.md` with a line such as `Scope: app/pricing.py, docs/**`.
`scope-check` blocks on other files (tests of in-scope modules are allowed). Set `GATES_TASK_TRUSTED=1` only when a
human wrote the task text: that enables the LLM `find-scope` prompt.

## LLM review

- **Prompts** live in `prompts/*.md` (one per file: System + User blocks, severity ladder, rationale per element,
  revision log). **Schemas** live in `schemas/*.json`. Every input is wrapped in nonce-tagged blocks and treated as
  untrusted data.
- **Endpoint**: set `GATES_JUDGE_BASE_URL`, `GATES_JUDGE_MODEL` and `GATES_JUDGE_API_KEY`, either in the
  environment or in a 0600 file you source. Never commit them.
  - A private CA goes in `GATES_JUDGE_CA_FILE`. TLS verification is never disabled.
  - The client honours the standard `https_proxy` / `no_proxy` variables. Add the gateway host to `no_proxy` if it is
    local.
  - The key is sent only to `base_url` and is never logged. Long token-like strings in findings are redacted.
- **Failure behaviour**: if the endpoint is down or the key is wrong, the run reports "review unavailable" and exits 0.
- **Profiles** set the prompts, samples, votes, verifier, floors, time budget and `blocking_categories` (default `[]`).
  - `render.py` refuses a small-tier profile that uses prompts the evidence says a ~4B model cannot do reliably
    (`verify-finding`, `find-security`, `find-scope`, `find-test-adequacy`).
  - It also refuses blocking without a verifier.
- **Promoting a category to blocking** needs all of the following:
  - ≥ 35 labelled findings in that category with 0 false positives (or 53 with 1), which gives a Wilson 95% lower
    bound ≥ 0.90;
  - `verify: true`, `samples ≥ 3`, `min_votes ≥ 2`;
  - an override log reviewed monthly, using Tricorder's rule: ≥ 10% "not useful" puts it on probation, > 25% turns
    it off.

## Docker image (optional)

`Dockerfile` builds a tool image in which every binary is pinned by sha256 and every wheel by `--require-hashes`.
Build it with `docker build -t llm-code-gates-tools:0.1 -f gates/Dockerfile gates`. Run the gates inside it with
CPU and memory limits:
`docker run --rm --cpus 2 --memory 3g -v "$PWD":/work -w /work llm-code-gates-tools:0.1 task check`.

## Limits (read before trusting a green run)

- The deterministic gates see form, not intent. A wrong-but-tested change passes them.
- The LLM review sees only the diff. Its findings are opinions with a failure scenario attached, and they can be
  wrong.
- `licence-check` sees declared licence text only. Code copied without its header needs a snippet-fingerprint
  database (ScanCode/SCANOSS), which this kit does not include.
- `dep-check` proves that a package exists and is old enough, not that it is benign. Pair it with osv-scanner and
  a malicious-package feed.
- `diff-mutation` is capped at 20 mutants. A high score on a few mutants is weak evidence, and equivalent mutants
  can make a score look low.
- Safety-critical, regulated or high-blast-radius changes still need a human reviewer.

Licence: MIT. The kit's Semgrep rules were written for this kit. No Semgrep Registry rules are included,
because their licence forbids redistribution.
