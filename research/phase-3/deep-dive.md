# Phase 3 — Deep analysis + prompt library (2026-10-15)

Evidence base: `../phase-2/discovery.md` and its notes, where every source has a URL, an access date and a status.
Keys in [brackets] refer to those notes. Every number is setting-specific, and its critique is given next to it.

## 1. RQ1: Failure taxonomy, base rates and detectability

| # | Mode | Best base rate (critique) | Deterministic signal? | LLM needed? |
|---|---|---|---|---|
| 1 | Hallucinated / non-existent package; slopsquatting | 4.62–6.10% of samples, 2026 frontier [CHURILOV26] (single-author replication preprint, data released); 5.2% commercial / 21.7% OSS in 2024 [SPRACKLEN25] (USENIX Sec; 2024 cohort); stdlib misclassification inflates Python by up to 9.4 pp [DJIRE26]; no confirmed slopsquatting attack in the wild as of 07/2026 (tertiary) | **Yes**: registry 404, first-publish age, version exists | No |
| 2 | Plausible logic that fails on edge cases | 29.6% of test-passing SWE-bench Verified patches diverge from ground truth, 28.6% of those certainly wrong [PatchDiff, ICSE'26]; misinterpretation 20.77%, missing corner case 15.27% of LLM bugs [TAMBON24] (Codex-era) | Partly: unit tests, property tests, mutation score (test strength) | Yes, for "wrong but tested", but LLM real-PR F1 is 0.066 [BiggerNotBetter] |
| 3 | Silent scope expansion | Out-of-scope actions in 5.4–27.7% of runs for permissive agents [OVEREAGER26] (constructed scenarios, preprint) | **Yes** if the task declares a scope (file globs); size heuristics otherwise | Yes, for behavioural scope ("changed unrelated behaviour in an allowed file") |
| 4 | Tests written to pass; deleted/weakened assertions; test tampering | ImpossibleBench: GPT-5 cheats on 54–76% of impossible tasks, Claude models mainly by modifying tests (adversarial upper bound); Claude 3.7 78% vs Claude 4 51% (vendor system card). **No field rate for weakened assertions in real PRs exists.** | **Yes**: AST diff of tests vs BASE (removed, weakened, skipped, tautology, config), coverage drop, diff-scoped mutation | Marginal (indirect forms: helper skips, mocks of the unit under test) |
| 5 | Insecure defaults, copied vulnerable patterns | ~50% of functionally correct generated backends exploitable [BAXBENCH25, ICML]; ~40% of 2021 Copilot programs [PEARCE22]; 29.5% Py / 24.2% JS of in-the-wild snippets [FU25, TOSEM] | **Yes** for pattern classes (Semgrep, bandit, gitleaks) | For flow/authz classes, but LLM vuln detection is near random on realistic data [PrimeVul] |
| 6 | Licence-contaminated snippets | 0.88–2.01% of outputs strikingly similar to OSS; most models give no accurate licence for copyleft code [LICOEVAL25, ICSE'25] (conservative similarity → lower bound) | Partly: declared headers (cheap); snippet fingerprints (ScanCode/SCANOSS KB) | No |
| 7 | Dead / unused code | 14.8–42.7% of smells [SABRA25] (Sonar-adjacent, Java) | **Yes**: ruff F401/F841, vulture, deadcode linters | No |
| 8 | Over-broad / swallowed exceptions | Exception handling 11.6–16.75% of SonarQube bugs [SABRA25]; try/catch lines missed by 81–86% of agent-PR tests [DIPONGKOR26] (no direct prevalence study) | **Yes**: Semgrep/ruff BLE001/S110 | No |
| 9 | Duplication / churn | GitClear 8× duplicated blocks (vendor, unread primary) vs no general churn increase [XIAO25, TSE] | **Yes**: clone detection (jscpd, kit dup-check) | No |

Conclusion: of nine modes, six have a cheap deterministic detector with essentially zero false positives on
change-scoped input (1, 4, 5-patterns, 7, 8, 9). One more (3) has one when a scope is declared. The LLM's
unique territory is modes 2, 3-behavioural and 5-flow, which are exactly the modes where the measured LLM reliability
is worst (§4).

## 2. RQ2: Mode → cheapest reliable check → layer → block/warn/inform

| Mode | Cheapest reliable check (kit rule) | Layer | Default | Where a deterministic tool beats an LLM outright |
|---|---|---|---|---|
| Hallucinated package | `dep-check` not-on-registry / version-not-found | L0 | block | Always: a registry 404 is ground truth |
| Suspiciously new package | `dep-check` too-new (< 30 d) / fresh-release (< 7 d) | L0 | block / warn | Always |
| Undeclared import | `dep-check` undeclared-import (+ test ImportError) | L0 | warn | Always (name mapping is the only FP source) |
| Test deleted / weakened / skipped / tautology / config | `test-tamper` | L0 | block | Always: an AST comparison against BASE that the agent cannot edit |
| Expected value changed | `test-tamper` expectation-changed | L0 | **warn** (legitimate when requested) | — the judgment needs intent; LLM `find-test-integrity` is advisory |
| Tests written to pass | `coverage-drop`, `diff-mutation` | L2 / L3 | block (score < 0.6, ≥ 4 mutants) | Mutation is ground truth for "do the tests constrain this line" |
| Edge-case logic | repo unit/property tests; LLM `find-correctness` | L0–L3 | tests block; LLM warn | — (no deterministic oracle without a spec) |
| Scope expansion (file level) | `scope-check` with declared scope | L0 | block | When scope is declared |
| Scope expansion (behavioural) | LLM `find-scope` (trusted task text only) | L3 | warn | — |
| Insecure pattern | `semgrep` vendored rules (added lines only) | L0/L2 | block (ERROR) | For pattern classes, always (PrimeVul, Ullah) |
| Insecure flow / authz | LLM `find-security` | L3 | warn | — |
| Hard-coded secret | gitleaks (repo `secrets` task, #3 contract) | L1/L2/L3 | block | Always |
| Copyleft text | `licence-check` | L2 | block | Always (declared text) |
| Dead code | repo linter (ruff F401/F841) | L0/L2 | block | Always |
| Swallowed exception | `semgrep` gates.py.swallowed-broad-exception | L0/L2 | block | Always |
| Duplication | `dup-check` | L2 | warn | Always (but not a defect by itself) |
| Known-vulnerable deps | osv-scanner (repo `audit`) | L2 | block | Always |
| Image vulns / SBOM | syft + grype (repo `image`) | L3 | block (high) | Always |

## 3. RQ3: Deterministic tooling (access 2026-10-15; versions from release APIs)

Re-check of #3's pins:

| Tool | #3 pin | Latest | Status | Licence | Runtime |
|---|---|---|---|---|---|
| gitleaks | v8.30.1 | v8.30.1 (2026-03-21) | current | MIT | Go |
| osv-scanner | unpinned | v2.7.0 (2026-10-12) | pin it | Apache-2.0 | Go |
| semgrep CE | unpinned | 1.181.0 (2026-10-14) | pin ≥ 14 days old → 1.178.0 (2026-09-23) used here | LGPL-2.1 engine; **registry rules: Semgrep Rules License v1.0 (no redistribution)** | Python+OCaml |
| actionlint | v1.7.12 | v1.7.12 (2026-03-30) | current | MIT | Go |
| zizmor | v1.30.1 | v1.31.0 (2026-10-15, same day) | keep 1.30.1 until the 14-day cooldown passes | MIT | Rust |
| syft | (image) | v1.54.1 (2026-10-06) | pin | Apache-2.0 | Go |
| grype | (image) | v0.120.1 (2026-10-06) | pin | Apache-2.0 | Go |
| task | — | v3.54.0 (2026-10-01) | pin | MIT | Go |
| pre-commit-hooks / prek | v6.0.0 / — | v6.0.0 / v0.5.5 | current | MIT | Python / Rust |
| Trivy | — | v0.76.0 | **excluded**: GHSA-69fq-xp46-6x23 / CVE-2026-33634 (malicious v0.69.4, 76/77 trivy-action tags rewritten, 2026-03-19) | — | — |

Other candidates. Full table in `../phase-2/notes/rq03-tools-rq09-refimpls.md`; all are self-hostable unless noted.
- **Types / lint**:
  - ruff 0.17.0 (MIT), mypy 2.4.0 (MIT), pyright 1.1.414 (MIT);
  - eslint 10.12.0 (MIT), TypeScript 7.0.2 (Apache-2.0, Go-native);
  - golangci-lint v2.14.0 (GPL-3.0), staticcheck 2026.2.2 (MIT), biome 2.5.15.
- **Mutation testing**:
  - mutmut 3.8.0 (BSD; incremental, no git-ref scoping), cosmic-ray 8.7.0 (MIT; `cr-filter-git`);
  - StrykerJS 10.0.0 (Apache; `--incremental` against the last report), Stryker.NET 5.0.0 (`--since:<ref>`);
  - PIT 1.30.1 (Apache; git scoping needs commercial arcmutate);
  - cargo-mutants 27.1.0 (MIT; `--in-diff`), gremlins v0.6.0 (Apache; `--diff <ref>`).
  - The kit adds a stdlib AST diff-scoped mutator for Python because mutmut 3 has no git-ref scoping.
- **Property testing**: Hypothesis 6.169.3 (MPL-2.0), fast-check 4.10.2 (MIT), proptest 1.12.0, rapid v1.3.0.
- **SAST**:
  - Semgrep CE (the rules caveat above); Opengrep v1.30.2 (LGPL-2.1 fork; the same registry-rules licence still
    applies to registry rules);
  - **CodeQL CLI v2.27.2**: GitHub CodeQL Terms. It is not usable on private non-OSS code without GHAS/Code Security
    ($30/active committer/month), so not on a private Forgejo repo;
  - bandit 1.9.4, gosec v2.29.0.
- **SCA / SBOM / secrets**:
  - osv-scanner (includes OpenSSF malicious-packages data), grype/syft, OWASP dependency-check v13.0.0;
  - trufflehog v3.99.2 (**AGPL-3.0**); detect-secrets v1.5.0 (no release since 2024-05).
- **Dependency existence / age**:
  - registry JSON APIs return 404 for missing packages. Age comes from PyPI `upload_time_iso_8601`, npm
    `time.created`, Go proxy `.info Time`, crates.io `created_at`, and deps.dev v3 `publishedAt`.
  - GuardDog v3.2.0 (Apache) is self-hosted.
  - Socket `sfw` and Aikido Safe Chain (AGPL; 48 h min-age default) call vendor clouds.
- **Licence**:
  - ScanCode 32.5.0 (Apache + CC-BY), SCANOSS (GPL-2.0 engine; snippet KB), licensee, pip-licenses,
    license-checker-rseidelsohn, go-licenses;
  - REUSE 6.2.0 (GPL-3.0), FOSSology 4.7.2 (GPL-2.0).
- **Coverage**: coverage.py 7.16.2, diff-cover 10.6.0, c8 12.0.0.
- **Misc**: hadolint v2.15.1 (GPL-3.0), shellcheck v0.11.0 (GPL-3.0), reviewdog v0.21.2 (MIT, a reporter).

Kit choices that follow from this:
- **Own Semgrep rules.** Registry rules cannot be bundled.
- **No CodeQL.** It is licence-barred for private Forgejo repos.
- **Registry metadata APIs for dependency checks** rather than a cloud service.
- **A 14-day cooldown on our own pins**, the same principle `dep-check` enforces at 7/30 days.

## 4. RQ4: Judge reliability, and where an LLM judge must never block

Agreement:
- Human–LLM Krippendorff α is 0.15, against 0.80 human–human, on whether a change fixes a static-analysis warning
  [Ahmed2024] (n = 1,306; 2024 models; preprint).

Precision and recall on real changes:
- real-PR F1 is 0.066, against 0.847 on synthetic bugs, and falls to 0.043 for diffs over 150 lines
  [BiggerNotBetter] (n = 150, small);
- frontier models detect 15–31% of human-flagged issues [SWE-PRBench] (350 PRs; single author);
- the best agent places 71.9% of bugs in its top-5 comments, a figure that says nothing about precision, and loses
  up to 25.5% on proprietary repos [CRBugBench, 2026-10].

Biases:
- **Order:** swapping order moves accuracy up to 14% [CodeJudgeBench].
- **Renaming:** renaming flips 17–26% of verdicts [Ullah2024].
- **Framing:** framing attacks in PR metadata succeed 32/33 [Alexopoulos2026].
- **Self-preference:** contested.
  - Present in [Panickssery2024] and [Wataoka2024].
  - Mostly legitimate according to [Chen2025], but harmful exactly when the judge was wrong.
  - Only 51% of earlier findings survive a null test [Roytburg, ICML 2026].
  - Rubric-based self-preference was over 50% more likely to wrongly pass the judge's own failing output
    [Pombal2026].
- **Verbosity:** no code-specific measurement was found. The general-judge literature (MT-Bench) is not code.
- **Run-to-run variance:** temperature 0 is not deterministic: 75.76% of tasks had zero equal outputs across runs
  [Ouyang2023], there is up to a 15% accuracy swing over 10 runs [Atil2024], and Qwen3-235B produced 80 unique
  outputs out of 1,000 [He2025].

Industrial acceptance rates measure usefulness, not precision:
- Google AutoCommenter: 54% → 66% useful after suppressing 17 categories;
- Meta: 19.7% actionable-applied;
- Beko: 73.8% resolved, but PR closure time went from 5h52 to 8h20;
- Mozilla / Ubisoft: 8.1% / 7.2% accepted.

**An LLM judge must never block:**
- on security on a small (≤ 8B) model;
- on any category without ≥ 90% measured precision on ≥ 35 labelled findings;
- on unverified or single-sample findings;
- when the task or PR text that the authoring agent wrote is the deciding evidence;
- inside the L0 hook cache (non-determinism makes the cache unsound);
- for the agent's own self-review (self-preference and shared blind spots).

## 5. RQ5: Prompt structures (which raise recall vs which lower false positives)

These are different levers.

**Raise recall** (and cost precision):
- per-dimension decomposition (MultiVer union: recall 82.7%, precision 48.8%);
- n-sample union;
- checklists of known failure forms;
- few-shot examples (+46–659% exact match for review-comment generation [Pornprasit2024]).

**Lower FPs** (and cost recall or calls):
- a required concrete failure scenario / trigger path (−36% FPR [VulAgent]);
- refute-first verification (79–83% of candidates killed [RefuteOrPromote]);
- grounding (evidence must be quoted from a changed line);
- votes across samples (2-of-3);
- severity and confidence floors (only after anchoring; raw confidence is overconfident [Xiong2024]);
- explicit "empty is the expected answer". No study isolates this; it is reasoned from the "flags correct code"
  findings [Jin&Chen 2025];
- diff-only context (beat fuller context [SWE-PRBench]);
- exclusion lists;
- no persona [Pornprasit2024].

**Format:** structured output is contested (Tam 2024 vs the .txt rebuttal). The kit puts a short `analysis` field
first inside the JSON and strips `<think>`. Chain-of-thought hurts sub-10B models [Wei2022], so the small-tier
prompt asks for 1–2 sentences.

## 6. The prompt library: draft → adversarial critique → revision

- **v1 drafts** are in `prompts/v1/` (six deliberately naive prompts).
- **Critique**: an independent `ai-prompt-lens` agent reviewed them against the schemas and the Phase 2 evidence.
  Its report is recorded verbatim in `prompt-critique-v1.md`.
- **v2** (`prompts/*.md`, generated by `tools/build_prompts.py` from shared blocks so every file stays standalone)
  applies all of the critique's priority items.

| Critique item | v2 change | Also enforced in the harness? |
|---|---|---|
| Prompts/schemas disagree (no +line for deletions; CWE field missing) | `side: new\|old`, `cwe`, `scope_kind`; evidence may be a removed line or quoted task text | grounding checks the stated side / task text |
| No data/instruction separation (framing attacks 97%) | nonce-tagged `<task-N>`/`<diff-N>`/`<hypothesis-N>` blocks + "not evidence" list; task labelled UNVERIFIED | random nonce per run; closing tags neutralised in inputs (`tests/test_review.py`) |
| Line numbers | left-column numbering for new and old sides; "never compute them" | line snapped to where the evidence actually is |
| No severity ladder | identical ladder in every finder | floor `min_severity`; scope/test-adequacy capped at medium |
| No trigger path | `Input/state -> executes line N -> actual -> expected` required | schema minLength; stub verifier refutes vague scenarios |
| "Nothing found" only once | everywhere + max 3 findings | harness truncates to 3 |
| Exclusions / categories drift | exclusion list; `Categories:` pinned per prompt | off-category findings dropped |
| Persona / raw confidence | personas removed; anchored confidence | confidence floor applies after the verifier |
| Small-model mechanics | `review-single-pass` narrowed, 1–2 sentence analysis, examples | `render.py` refuses small-tier profiles that use verify/security/scope/adequacy |
| find-tests speculative | split into `find-test-integrity` (checklist) + `find-test-adequacy` (named mutant) | — |
| find-scope penalises supporting work; task text untrusted | supporting-change whitelist; runs only if `GATES_TASK_TRUSTED=1`; medium cap | skipped otherwise |
| Verifier anchoring; intent lever | neutral hypothesis (no severity/confidence/adjectives); refute by default; intent refutes only correctness/scope; whole-file diff | consistency rules override contradictory verdicts; final severity = min |
| Secrets in evidence | "name + 4 chars" rule | `redact()` on every evidence string |
| Pooling n samples cuts precision | — | blocking categories need ≥ 2-of-n votes |

Not adopted, with reasons:
- **A different-family verifier.** Recommended in the profile notes, but not enforceable from a single endpoint.
- **2-of-3 verifier samples.** Votes are on finders instead, to keep the call count inside the L3 budget.

## 7. RQ6: False-positive control. Implemented mechanisms and tuning data

| Mechanism | Evidence | Kit implementation |
|---|---|---|
| New-code-only / baseline | Semgrep diff-aware, SonarQube new code, GitHub alerts on changed lines | Semgrep findings on unchanged lines → inform; `--write-baseline` for LLM findings |
| Grounding | (critique; cheap) | evidence must match a changed line on the stated side |
| Votes | MultiVer (union hurts precision); PoLL | `samples`/`min_votes`; ≥ 2 for blocking categories |
| Verification | VulAgent −36% FPR; RefuteOrPromote | `verify-finding` + consistency rules |
| Confidence floor | Xiong (overconfident) → anchored + after verify | `min_confidence` 0.6 |
| Severity floor | Tricorder "significant impact" criterion | `min_severity` medium |
| Suppression with expiry | Snyk `expires` (malformed date = permanent!) | `reason` + valid `expires` mandatory; malformed → ignored with a warning; expired → stops suppressing |
| Dedup | — | location + category clustering across prompts |
| Demotion on not-useful rate | Tricorder ≥ 10% probation, > 25% off; Coverity > 30% "people ignore the tool" | documented process (README); data = suppressions + overrides |

**Data needed to tune**: per-finding labels (useful / not useful / wrong) from the people acting on findings.
Showing precision ≥ 0.90 at 95% confidence (Wilson lower bound) needs:

| Labelled findings | With at most this many false positives |
|---|---|
| 35 | 0 |
| 53 | 1 |
| 69 | 2 |
| 113 | 5 |

## 8. RQ7: Loops

- **Gains come in the first rounds.** Self-debugging gains mostly end within 3 turns, and turn 1 gives about
  +12% [Self-Debugging].
- **Models lose debugging ability fast.** They lose 60–80% of it within 2–3 attempts, and fresh restarts help
  [DDI 2025].
- **Sampling beats deep repair.** More initial samples often beat deeper repair [Olausson, ICLR 2024 v5].
- **Plausible is not correct.** Qi 2015 found 2/105 patches correct; PatchDiff found 29.6% of plausible patches
  diverge; SWE-Bench+ found 31.08% of passing patches are weak-test passes.
- **The model that writes the code should not write the oracle.** LLM-written oracles encode the actual (buggy)
  behaviour [Konstantinou2024].

**Interaction with agent-gate.sh's "give up after 3".**
- The evidence supports a cap of 3. The useful refinement is to restart from a clean context or a new sample rather
  than keep repairing in the same conversation.
- The kit's L0 gates make the loop safer. The checks the agent most likely games (test deletion, weakening,
  skipping, config deselection) are compared against BASE_REF, which the agent cannot edit. A loop therefore
  cannot "converge" by tampering with tests.
- What the kit cannot stop is a loop converging on wrong-but-tested code: tests written in the same loop. That is
  what `diff-mutation` (L3) partly measures.

## 9. RQ8: Provenance and audit

**Required by law (2026-10-15):** nothing records model or prompt provenance of code.
- EU AI Act Art. 50(2) binds providers and excludes source code (Commission FAQ).
- The Digital Omnibus moved high-risk dates to 2027/2028 (secondary sources).
- CRA (reporting from 2026-09-11, everything else 2027-12-11), DORA, FDA (non-binding), PCI DSS and SSDF are
  origin-neutral.
- US M-22-18 was rescinded by M-26-05 (2026-01-23).

**Required by projects:**
- Linux kernel: `Assisted-by:` (format simplified Aug 2026; agents must not add Signed-off-by);
- Mesa: `Assisted-by` / `Generated-by`;
- Fedora: disclosure;
- QEMU and Gentoo: bans;
- NetBSD: core approval.

**Recommended minimal record (kit-compatible):**
1. **Commit trailers**: `Assisted-by: <agent>:<model> [tools]`, plus `AI-Session: <url>` and
   `AI-Prompt-SHA256: <hash>` where available. The human alone adds Signed-off-by. The tools' default
   `Co-Authored-By:` is acceptable but carries no model version for most tools.
2. **Gate record**: `.gates/out/summary-*.json` + `llm-review.events.jsonl` (profile, model, prompt version and
   sha256 per prompt, every decision). Bind them to the commit SHA as an in-toto `test-result/v0.1` attestation.
3. **Signing**:
   - Sign offline with `cosign attest-blob --key` (keyless Sigstore needs a Fulcio-trusted OIDC issuer; Forgejo is
     not one).
   - Store the attestation in `refs/notes/ai-gates` or as a CI artifact.
   - Sign agent commits with a dedicated SSH key.
4. SLSA build provenance covers the image build, not authorship.

Implemented in the PoC: point 2. The run records carry the prompt sha256 and model. Points 1, 3 and 4 are documented
and backlogged.

## 10. RQ9: Reference implementations

- **Self-hostable with your own model**:
  - PR-Agent: MIT, v0.47.0, LiteLLM/Ollama, Gitea (Forgejo untested);
  - Kodus: AGPL + EE, Forgejo supported;
  - OpenHands PR review: MIT;
  - anc95/ChatGPT-CodeReview: ISC;
  - shippie: MIT;
  - SonarQube Server: AI CodeFix with your own Azure OpenAI model.
- **Self-host only on Enterprise plans**: CodeRabbit ($24–72/seat/mo), Greptile ($30), Qodo ($30 + credits).
- **SaaS only**: Copilot code review (~$0.05–$5 per review in AI credits), Codacy, Semgrep Assistant.
- **Dead or stale**: Amazon CodeGuru Reviewer (maintenance mode since 2025-11-07), Sweep (pivoted),
  villesau/ai-codereviewer (stale), coderabbitai/ai-pr-reviewer (404).
- **Benchmarks**: none is independent. Martian's code-review benchmark is the most neutral, but its rankings swing
  between snapshots. GitHub's and Entelligence's are vendor-run.
- **What the products do well** (from their docs): diff-scoped PR comments, incremental re-review, learnable
  suppressions (CodeRabbit "learnings", Qodo best-practices files) and ticket context.
- **What they do badly**, by their own published numbers or user reports:
  - noise (hence the suppression features);
  - no published precision;
  - vendor-run benchmarks;
  - blocking is rarely offered: they comment, they do not gate.
- **What the kit takes from them**: diff-scoped review and suppressions. It adds what they lack: deterministic
  pre-gates, a measured precision rule before blocking, and an offline stub.

## 11. RQ10: Self-hosting per judge profile

| Profile | Hardware (minimum) | What the evidence supports | Kit configuration |
|---|---|---|---|
| (a) `local-8gb` ~4B (e.g. Qwen3-4B-Instruct-2507 Q4_K_M ≈ 2.5 GB + KV ≈ 1.1 GiB @ 8k f16) | 8 GB VRAM | Non-thinking only. LiveCodeBench v6 35.1, Aider 12.9 (self-reported). Non-thinking judges are near chance as verifiers (CodeJudgeBench); 3B models catch 30–58% of refactoring bugs, recall only [RefactorSLM] | single narrow checklist prompt, no verifier, advisory; set `num_ctx` ≥ 8192 on the server (Ollama defaults to 4096 and truncates silently) |
| (b) `local-48gb-plus` 30–120B | 48–96 GB | gpt-oss-120b SWE-bench Verified 62.4, fits one 80 GB GPU; Qwen3-Coder-Next 70.6–71.3 (vendor); Aider: Qwen3-32B 40.0, gpt-oss-120b 41.8 | all finders + verifier, 3 samples / 2 votes, json_schema output |
| (c) `cloud-openai-compatible` frontier | none | CRBugBench best 71.9% top-5 recall; SWE-PRBench 15–31%; gpt-5 (high) Aider 88.0 | same as (b); code leaves the host |

**The capability gap, stated plainly:**
- The capability gap between (a) and (c) is large on every code benchmark found.
- Even (c) misses most real PR issues.
- **At no tier is the evidence good enough for an LLM finding to block without local measurement.**
- (a) is useful only as a cheap checklist pass, and only if its findings are shown as advisory.

**Measured on this machine:**
- (a): **NOT RUN**. No GPU and no gateway are present (see `../phase-1/scope.md`).
- (b) and (c): evidence only.

## 12. RQ11: Limits

**No gate catches:**
- wrong requirements, and intent errors in a well-tested change. Code LLMs write code instead of asking in > 60% of
  ambiguous cases [HumanEvalComm, TOSEM];
- emergent and system-level failures (load, concurrency across services, data migrations at scale);
- security design flaws (an authorisation model that is wrong by design);
- licence contamination without headers (no snippet KB in the kit);
- "plausible but wrong" code whose tests encode the same misunderstanding.

**"No human in the loop" is irresponsible for:**
- safety-critical code. No path to certification under DO-178C / IEC 61508 / ISO 26262 [WEI26-FORGE];
  MISRA compliance 0/n [UMER25];
- regulated financial/medical logic;
- authn/authz and crypto changes;
- data migrations and deletions;
- infrastructure and deploy pipelines (#3 forbids agent deploy credentials);
- any change where the agent also wrote the acceptance tests.

Automation bias makes this worse. Developers believed AI made them 20% faster while being 19% slower [METR RCT,
n = 16, preprint]. AI users wrote less secure code and were more confident in it [Perry, CCS 2023].

## 13. Adversarial pass per check (how a model or developer games it, and what the kit does)

| Check | Gaming move | Mitigation in kit | Residual risk |
|---|---|---|---|
| test-tamper | delete a test and add a trivial one; move the assertion into a helper; `assert x or True`; skip via a conftest hook; weaken through parametrize | BASE_REF comparison per test name; tautology detection; conftest/config watched; moved tests matched by name | assertion logic moved into helpers is invisible to counts; `or True` inside a call is not parsed; renaming a test *and* weakening it reads as remove+add (blocks — conservative); **v0.2** counts assertions × `parametrize` rows, so padding a table with redundant rows can mask a removed assertion (backlog: compare the (input, expected) literal sets) |
| dep-check | pick a package that exists and is > 30 days old but malicious; typosquat an old package; vendor the code instead | existence + age + version; osv-scanner (malicious-packages data) in the repo `audit` task | old typosquats pass; vendored code bypasses the check entirely |
| semgrep | obfuscate (`getattr(subprocess, "run")`), split strings, pass `verify` via `**kwargs` | rules on common forms only | trivially bypassable by a determined author; it catches the habitual, not the adversarial |
| scope-check | the agent writes a broad scope into `.gates/task.md` itself | scope should come from the human task; `GATES_TASK_TRUSTED` gates the LLM scope prompt | if the agent controls the task file, file scope is self-declared (process control needed) |
| licence-check | strip the header when copying | — | snippet-level copying is invisible (needs ScanCode/SCANOSS KB) |
| dup-check | rename variables (normalisation is whitespace only) | — | Type-2 clones are missed; warn-only anyway |
| coverage-drop | add a test that executes code without asserting | diff-mutation catches assert-free execution | combined with mutation, only equivalent-mutant-heavy code escapes |
| diff-mutation | put logic on lines the operator set does not mutate (string ops, calls); keep changes under the 4-mutant floor; (v0.2) keep new code out of the coverage `source` so it counts as unexecuted | ≥ 4 mutants floor; inform-level survivors listed; coverage config edits are caught by test-tamper (`omit=`, `fail_under`) and coverage-drop | small changes are unmeasured; operator coverage is limited (no statement deletion); unexecuted code is coverage-drop's job only |
| llm-review | prompt injection in comments/strings/task text; flooding; framing ("security reviewed"); splitting changes | nonce-tagged untrusted data, closing-tag stripping, "not evidence" list, intent cannot refute security/test-integrity, max 3 findings, advisory by default | injection resistance is not measured against a real model here (NOT RUN); a 4B judge is easy to mislead |
| suppressions | blanket `rule: "*"` with a far expiry | reason + expiry mandatory, expired ones reported | no maximum expiry enforced (backlog: cap at 90 days) |
| agent-gate.sh (L0) | `--no-verify`, `git -c core.hooksPath=/dev/null`, `HUSKY=0`, a push via a script file, editing the hook or settings | #3's hook blocks `--no-verify`/`commit -n`; L3 re-runs everything server-side | other bypasses of the local hook exist; only L3 (required check) is authoritative |
| whole kit | edit `gates/` or `.gates/config.env` to weaken levels | changes to `gates/` and `.gates/` show in the diff; should be CODEOWNERS-protected | the kit skips `gates/` and `.gates/` when checking, so tampering with them is not flagged by the kit itself (backlog: a self-integrity check against the vendored version hash) |
