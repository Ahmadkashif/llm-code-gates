# Phase 4 — Synthesis (2026-10-15)

Inputs: `../phase-2/discovery.md` + notes, `../phase-3/deep-dive.md`, `../phase-3/prompt-critique-v1.md`.

## 1. Cross-cutting patterns

1. **Deterministic checks win wherever the defect has a syntactic or registry signature.** Examples: hallucinated
   packages (registry 404), test tampering (AST diff of tests), copied vulnerable patterns (Semgrep), secrets
   (gitleaks), copyleft headers. The evidence that LLM judges are weak at exactly these, combined with ~0 FP for the
   deterministic versions on the corpus, makes "LLM for these" a regression. Examples of that weakness: renaming
   flips 17–26% of verdicts, and vulnerability detection is near random on PrimeVul.
2. **What only an LLM can see is also what it is worst at.** That covers intent mismatch, scope creep and
   plausible-but-wrong logic. Frontier models find 15–31% of human-flagged PR issues, and real-PR F1 is 0.066. The
   LLM layer therefore *informs*; it cannot be the safety net.
3. **Precision is a pipeline property, not a prompt property.** The things that measurably cut FPs are grounding,
   a required trigger path (−36% FPR), refute-first verification (79–83% of candidates killed), votes across
   samples, and new-code-only baselines. Persona or wording tweaks are not on that list. All of these are built
   into `review/llm_review.py`.
4. **Placement beats accuracy.** Infer at diff time had a 70% fix rate, against 0% for the same analysis run in
   batch. Google's compile-time findings were judged "real" in 74% of cases, against 21% in checked-in code. So the
   cheap deterministic gates run at L0, inside the agent loop, where the agent fixes them immediately.
5. **The agent is the adversary as much as the author.** ImpossibleBench (54–76% cheating; Claude models modify
   tests), framing attacks on LLM reviewers (32/33), and self-preference when the model erred all point the same
   way. So:
   - gates must not trust the task text, the PR description or code comments;
   - the strongest gates are the ones that compare against `BASE_REF`, which the agent cannot edit.

## 2. Contradictions between sources (recorded, not resolved)

- **Structured output vs reasoning quality.** Tam et al. 2024 found format restrictions hurt reasoning; the .txt
  rebuttal measured 0.77 vs 0.73 in favour of structured output. Resolution in the kit: analysis comes first inside
  the JSON, is short for small models, and `<think>` blocks are stripped.
- **AI-driven code churn.** GitClear (vendor, 8× duplication) and Xiao et al. (TSE, no general churn increase)
  disagree. Duplication stays warn-level.
- **Self-preference.** Panickssery and Wataoka report it; Chen 2025 says most of it is legitimate; Roytburg (ICML
  2026) says only 51% of earlier findings survive a null test. The kit's response holds either way: use a
  different-family verifier where possible, and never let the authoring agent's model be the only judge.
- **SWE-Bench+.** One version reports a 31.08% weak-test share, another 24.70%. Cite the version.

## 3. Blocking-threshold proposal (open question 4 — the user decides)

**Proposal.** An LLM finding category may block unattended only when all of the following hold:
1. **Measured precision ≥ 90%** on ≥ 35 labelled findings of that category with 0 false positives, or 53 with ≤ 1,
   69 with ≤ 2, 113 with ≤ 5. That is the Wilson 95% lower bound ≥ 0.90. This is Tricorder's < 10% effective-FP
   threshold for code review, made statistically checkable.
2. Labels come from a mix of the target repos' real changes and seeded defects, and a human who did not write the
   code assigns them.
3. Verification is on, with `samples ≥ 3` and `min_votes ≥ 2`. Only *confirmed* findings block. The harness already
   enforces this: uncertain/unverified findings are inform-level only.
4. A live "not useful" rate is tracked from overrides and suppressions: ≥ 10% means probation, > 25% means the
   category is demoted to warn automatically (Tricorder §IV-E). Coverity's "> 30% causes problems" is the outer
   bound.
5. The category is never security-for-blocking on a small (~4B) judge (PrimeVul: near random).

**Expected outcome today.** No category qualifies: no labelled real-model data exists yet (`local-8gb` NOT RUN).
Deterministic kit rules block from day one, but the corpus shows they need the same loop.
- **v0.1 (pre-registered):** they blocked 3/14 clean change sets (parametrize refactor, an untested manual
  script, a legitimate test update outside the declared scope).
- **v0.2 (post-hoc tuning on the same corpus, so optimistic):** 0/14. The only remaining clean-set block came
  from the repo's own osv-scanner task.

See `../phase-6/log.md`. Any deterministic rule that shows > 10% not-useful in production should be demoted the
same way.

## 4. Layered architecture (mapped onto #3's L0–L5 and Taskfile tasks)

| Layer | Contract task | Kit task | Runs | Blocks? | Budget (measured, smoke test) |
|---|---|---|---|---|---|
| L0 agent hook | `check:fast` | `gates:fast` | test-tamper, dep-check, semgrep on changed files, scope-check | yes — the agent keeps working (Stop hook exit 2) | < 60 s (see phase-6) |
| L1 pre-commit | prek hooks | — (gitleaks staged) | unchanged from #3 | yes | < 10 s |
| L2 pre-push | `check` | `gates:deterministic` | + full semgrep, licence, duplication (warn), coverage drop | yes — the push is refused | < 2 min |
| L3 server CI | `ci` | `gates:server` | diff-scoped mutation (block), LLM review (advisory, exit 0) | deterministic: required check; LLM: never by default | < 10 min |
| L4 CD | release | — | unchanged | — | — |
| L5 scheduled | (repo) | — | full mutation run (mutmut / Stryker / cargo-mutants), dependency re-audit, re-baseline | opens an issue | < 60 min |

Why the LLM review is not at L0:
- On the 8 GB tier, a single 8k-context call to a 4B model on an RTX 4000-class GPU is not measured here (NOT RUN),
  but it would consume most of the 60 s budget with nothing else running.
- agent-gate.sh caches a pass per HEAD+diff fingerprint, and a non-deterministic gate makes that cache unsound.

## 5. The ci-lane secret conflict (open question 2 — options with trade-offs; the user decides)

| Option | What | For | Against |
|---|---|---|---|
| (a) low-value review key in the ci lane | rate-limited, review-only key as a repo/runner variable | simplest; review on every PR | breaks #3's "ci lane holds no secrets"; any branch's workflow can read it (Forgejo has no environment-scoped secrets); a leaked key costs GPU time on a shared box |
| (b) separate `review` lane | own runner registration, egress only to the gateway, key visible to that lane only, never a required check | keeps the ci lane secret-free; review stays server-side and visible in the PR | one more runner to operate; a same-repo branch can still target `runs-on: review` (Forgejo has no environment scoping), so the key is reachable by anyone who can push a branch |
| (c) LLM review only at L0/L2 on the developer machine; CI deterministic only (stub/no judge) | the developer's local env holds the key | no secret in CI at all; matches "advisory until proven"; zero CI coupling to the GPU | review isn't visible in the PR unless the developer pastes it; unattended agents on the server get no LLM review |

**Recommendation** (not a decision): **(c) now, (b) once a category is close to the blocking threshold.** The kit's
default `ci/forgejo-step.yml` implements (c). (b) is sketched as commented YAML. (a) is documented with its warning.

## 6. Rollout plan

1. **Week 0.** Vendor the kit and render with `--judge stub`. Turn on `gates:fast` and `gates:deterministic` as
   blocking.
   - Watch the override and suppression log.
   - Expect `expectation-changed` and `undeclared-import` warnings, which are warn-level by design.
2. **Week 1–2.** Turn on `gates:server`: diff-mutation blocking at 0.6 with ≥ 4 mutants, and LLM review advisory
   with the stub in CI. Run real-model review locally (option c) on willing developers' machines.
3. **Week 2–6.** Label LLM findings: confirmed-useful / not-useful / wrong. This needs ≥ 35 per category before any
   promotion is discussed. Re-baseline on main weekly.
4. **Later.**
   - Promote at most one category at a time (most likely `test-integrity`, which is also covered deterministically).
   - Consider the (b) review lane.
   - Re-measure monthly. Demote at > 25% not-useful.
5. **Never by default.** Auto-fix loops on protected branches, and LLM blocking on a small-tier judge.

## 7. Open questions carried to STATUS.md

The brief's open questions remain:
- Q1: keyward key and GPU window;
- Q2: the ci-lane secret (options above);
- Q3: cloud judge;
- Q4: threshold (proposal above);
- Q5: second stack;
- Q6: where the tool container may run;
- Q7: Forgejo lab resume;
- Q8: Mac stray plan.

New:
- (Q9) This run's machine has no gateway or GPU. Should the `local-8gb` measurement run on the box where #7 lives?
- (Q10) Should the kit be offered upstream into #3's repo-template as an optional include?
