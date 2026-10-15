# Phase 2 — Discovery (2026-10-15)

Method: four parallel discovery passes (one per RQ cluster), each writing source-level notes with URL, access date
(2026-10-15), status (VERIFIED / VERIFIED metadata-only / UNVERIFIED), verbatim quotes and a one-line critique.
~300 web/API calls in total; arXiv numbers come from `export.arxiv.org/api/query` abstracts or locally extracted
PDF text; tool versions from the GitHub releases / PyPI / npm / Go-proxy / crates.io APIs. Prior evidence from
sweep-02 and sweep-04 was re-checked by spot-fetching (Tricorder, Spracklen, Churilov, Djire, Xiao, Pearce, Perry,
Fu, Krishna, Huang, Olausson, Pan — all matched; one discrepancy: SWE-Bench+ v2 says 31.08% weak-test patches,
another PDF version says 24.70% — cite the version).

Notes (the evidence base for every number below):
- `notes/rq01-taxonomy-rq11-limits.md` — RQ1 base rates per category, RQ11 limits
- `notes/rq03-tools-rq09-refimpls.md` — RQ3 tool versions/licences, RQ9 reference implementations, Q16 Forgejo
- `notes/rq04-07-judge-prompts-fp-loops.md` — RQ4 judge reliability, RQ5 prompt structure, RQ6 FP control, RQ7 loops
- `notes/rq08-provenance-regulation.md` — RQ8 trailers, attestations, SBOM, 2026 regulation
- `notes/rq10-selfhosting.md` — RQ10 capability per judge tier, thinking control, structured output, memory

## Headlines per RQ

**RQ1 Taxonomy (base rates; every number is setting-specific).**
Hallucinated packages 4.62–6.10% of samples for 2026 frontier models (Churilov 2026, preprint replication) vs
5.2% commercial / 21.7% open-source in 2024 (Spracklen, USENIX Sec 2025); 53 names all models invent are still
registrable. Plausible-but-wrong: 29.6% of test-passing SWE-bench Verified patches behave differently from ground
truth (PatchDiff, ICSE'26); 19.71% of passing patches fail strengthened tests. Scope expansion: permissive agents act
out of scope in 5.4–27.7% of runs (OVEREAGER26, preprint). Test gaming: GPT-5 cheats on 54–76% of impossible
SWE-bench tasks, Claude models mainly by modifying tests (ImpossibleBench 2025); Claude 3.7 hacked 78% of impossible
Claude Code tasks vs 51% for Claude 4 (vendor system card). Insecure code: ~50% of functionally correct generated
backends exploitable (BaxBench, ICML 2025). Licence: 0.88–2.01% of outputs strikingly similar to OSS (LiCoEval,
ICSE'25). Dead code / exception handling: SonarQube-based, vendor-adjacent only (Sabra 2025). Duplication: GitClear
(vendor, 403, secondary only) vs no general churn increase (Xiao et al., TSE). **Gap: no field study of deleted or
weakened assertions in real PRs; no direct study of swallowed-exception prevalence.**

**RQ3 Tools.** #3 pins re-checked: gitleaks v8.30.1, actionlint v1.7.12, pre-commit-hooks v6.0.0 current; zizmor
v1.30.1 one minor behind (v1.31.0 released on the access date — kept back by the 14-day cooldown); osv-scanner
v2.7.0; semgrep 1.181.0 latest (kit verified with 1.178.0); syft v1.54.1; grype v0.120.1; task v3.54.0.
**Trivy excluded**: GHSA-69fq-xp46-6x23 / CVE-2026-33634 (malicious v0.69.4, 76/77 trivy-action tags rewritten,
2026-03-19). **Semgrep Registry rules are NOT redistributable** (Semgrep Rules License v1.0: internal use only), so
the kit writes its own MIT rules. **CodeQL** cannot be used on private non-OSS code outside GHAS/Code Security.
Diff-scoped mutation natively: Stryker.NET `--since`, cargo-mutants `--in-diff`, gremlins `--diff`; StrykerJS and
mutmut are incremental only; PIT git-scoping needs commercial arcmutate.

**RQ4 Judges.** Human–LLM agreement on "does this change fix the warning": Krippendorff α 0.15 vs 0.80 human–human
(Ahmed 2024, n=1,306). Order swaps move accuracy up to 14%; non-thinking judges 53–59% on 50%-chance pairwise
(CodeJudgeBench). Real-PR defect detection F1 0.066 vs 0.847 synthetic (BiggerNotBetter); frontier models find
15–31% of human-flagged PR issues (SWE-PRBench). Renaming flips 17–26% of vulnerability verdicts (Ullah, S&P 2024);
framing attacks in PR metadata 32/33 (Alexopoulos 2026). T=0 is not deterministic (Ouyang 2023; He 2025: 80 unique
outputs/1,000). Industrial acceptance: Google AutoCommenter useful 54%→66% after suppressing 17 categories; Meta
19.7% actionable-applied; Beko 73.8% resolved but PR closure 5h52→8h20; Mozilla/Ubisoft 8.1%/7.2%.

**RQ5 Prompt structure.** Hypothesis + trigger path cut FPR ~36% (VulAgent); refute-first verification killed
79–83% of candidates and exposed 10-agent consensus on a non-existent bug (RefuteOrPromote); per-concern union raises
recall (82.7%) at precision 48.8% (MultiVer); few-shot beats zero-shot, persona adds nothing (Pornprasit 2024);
format-first may hurt reasoning (Tam 2024, contested); diff-only beat fuller context (SWE-PRBench); CoT hurts < 10B
(Wei 2022). No study isolates "no findings is valid".

**RQ6 FP control.** Tricorder < 10% effective FP at review time; ≥ 10% probation; > 25% off (re-verified). Verbalised
confidence is overconfident (Xiong 2024); code LMs uncalibrated without labelled data (Spiess, ICSE 2025). Small-judge
panels beat one large judge at 7× lower cost (PoLL, non-code). New-code-only baselines are standard (Semgrep diff-aware,
SonarQube new code, GitHub code scanning). Wilson: showing precision ≥ 0.90 at 95% needs n = 35 findings with 0 FP,
53 with 1, 69 with 2, 113 with 5.

**RQ7 Loops.** Self-debugging gains end mostly within 3 turns (Self-Debugging); models lose 60–80% of debugging
ability in 2–3 attempts, fresh restarts help (DDI 2025); more initial samples often beat deeper repair (Olausson,
ICLR 2024); plausible ≠ correct (Qi 2015: 2/105; PatchDiff 29.6%); LLM-written oracles encode the bug (Konstantinou
2024). Supports agent-gate's "give up after 3".

**RQ8 Provenance.** No law in force on 2026-10-15 requires recording which model/prompt produced a code change. EU AI
Act Art. 50(2) binds the provider and the Commission FAQ excludes source code from marking; CRA/DORA/FDA/PCI/SSDF are
origin-neutral; US M-22-18 self-attestation rescinded (M-26-05, 2026-01-23). Project policies do: Linux kernel
`Assisted-by:` (simplified Aug 2026), Mesa `Assisted-by`/`Generated-by`, Fedora disclosure; QEMU/Gentoo bans. SLSA
attests builds, not authorship; in-toto `test-result/v0.1` fits gate results; keyless Sigstore needs a Fulcio-trusted
OIDC issuer (Forgejo is not one) → offline `cosign attest-blob --key`.

**RQ9 Reference implementations.** Self-hostable with own model: PR-Agent (MIT, now The-PR-Agent/pr-agent),
Kodus (AGPL, Forgejo support), SonarQube server (+ AI CodeFix with own Azure model). Enterprise-only self-host:
CodeRabbit, Greptile, Qodo. Not self-hostable: Copilot code review, Codacy, Semgrep Assistant. Discontinued: Amazon
CodeGuru Reviewer (maintenance mode 2025-11-07). No independent reviewer benchmark; vendor-run benchmarks swing.

**RQ10 Self-hosting.** Qwen3-4B-Instruct-2507: non-thinking only; LiveCodeBench v6 35.1, Aider 12.9 (self-reported).
gpt-oss-120b SWE-bench Verified 62.4, fits one 80 GB GPU; Q4_K_M weights 2.5 GB (4B) / 19 GB (30B) / 43 GB (70B);
Ollama default context 4096 silently truncates. Ollama `format` = JSON schema; vLLM `response_format` json_schema
(guided_* removed v0.12.0).

**RQ11 Limits.** Intent errors (code LLMs write instead of asking in > 60% of ambiguous cases, HumanEvalComm TOSEM),
safety-critical certification ("no path", Wei 2026; MISRA 0/n), automation bias (METR RCT: −19% actual vs +20%
perceived; Perry CCS 2023).

**Q16 Forgejo.** Visible without a token: the job log; the check status; an artifact via
`code.forgejo.org/forgejo/upload-artifact@v4|v5` (upstream v4+ fails); job summaries (`$FORGEJO_STEP_SUMMARY` /
`$GITHUB_STEP_SUMMARY`) only from Forgejo v17.0 + Runner 13.2 (merged 2026-09-07; v17 not tagged when checked; stable
v16.0.6 has none). Step-level `continue-on-error` works; job-level and `permissions:` are ignored. No SARIF UI.
