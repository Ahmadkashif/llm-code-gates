# Phase 2 notes: RQ4 (judge reliability), RQ5 (prompt structure), RQ6 (FP control), RQ7 (loops)

Access date for all sources: 2026-10-15. Status key:
- **VERIFIED**: I read the quoted text myself (arXiv API abstract, PDF text via pdftotext, or the primary web page).
- **VERIFIED (metadata only)**: bibliographic record confirmed, body not read.
- **UNVERIFIED**: seen only in search snippets or secondary summaries.

Quotes are verbatim from the arXiv Atom API abstract (export.arxiv.org) unless marked "[PDF]" (read from pdftotext of the arXiv/author PDF) or "[web]" (read from the page through WebFetch, which may paraphrase between quoted fragments; quoted fragments are exact).

Spot-check of prior VERIFIED items (done this session):
- **Tricorder ICSE 2015** [PDF, cs.umd.edu mirror]: "We still enforce a very low effective false positive rate here (< 10%)"; "A rate ≥ 10% puts the analyzer on probation ... If the rate goes above 25%, we may decide to turn the analyzer off immediately"; not-useful rate = "NOT USEFUL/(NOT USEFUL + PLEASE FIX + APPLY FIX)"; overall "in recent months it is typically at around 5%. When we remove analyzers that are on probation, the number goes down to under 4%." CONFIRMED.
- **Huang et al. 2310.01798** (ICLR 2024): "LLMs struggle to self-correct their responses without external feedback, and at times, their performance even degrades after self-correction." CONFIRMED.
- **Olausson et al. 2306.09896 v5** (ICLR 2024): "when the cost of carrying out repair is taken into account, performance gains are often modest, vary a lot between subsets of the data, and are sometimes not present at all." CONFIRMED.
- **Pan et al. 2407.04549**: reward hacking severity affected by "model size and context sharing between the generator and the evaluator." CONFIRMED.

---

## RQ4: Is an LLM judge reliable enough for code?

### A. Agreement with humans on code tasks

**[Ahmed2024] Ahmed, Devanbu, Treude, Pradel. "Can LLMs Replace Manual Annotation of Software Engineering Artifacts?" arXiv 2408.05534 (v2, 2025-02-04).** https://arxiv.org/abs/2408.05534. Status: VERIFIED (abstract + PDF Table I).
- Abstract: "applying six state-of-the-art LLMs to ten annotation tasks from five datasets ... such as ... deciding whether a code change fixes a static analysis warning. Our results show that replacing some human annotation effort with LLMs can produce inter-rater agreements equal or close to human-rater agreement."
- [PDF] Static-analysis-warning task (Kang et al. dataset, "1,306 samples", two human annotators): human-human Krippendorff's α **0.80**, human-model **0.15**, model-model **0.12** (Table I, top-3 models Claude/Gemini/GPT-4). "[F]or the static analysis warnings rating task, we have only two human raters, and they are in strong agreement (Krippendorff's α 0.80). However, human-model (0.15) and model-model (0.12) agreements are low."
- [PDF] Causality task: "mean human-model agreement (0.22) is much less than human-human (0.44)."
- [PDF] Name-value inconsistencies: "human-model and human-human agreement are quite similar for this task (mean Krippendorff's α 0.49 vs. 0.52)."
- Critique: preprint; GPT-4/Claude-3.5/Gemini-1.5 cohort (2024). Key takeaway for gates: the one task closest to "is this warning a real defect that got fixed?" is the one where LLMs fail (α 0.15).

**[WangR2025] Wang, Guo, Gao, Fan, Chong, Xia. "Can LLMs Replace Human Evaluators? An Empirical Study of LLM-as-a-Judge in Software Engineering." arXiv 2502.06193; ISSTA 2025.** https://arxiv.org/abs/2502.06193. Status: VERIFIED (abstract).
- "output-based methods reach the highest Pearson correlation of 81.32 and 68.51 with human scores in code translation and generation, achieving near-human evaluation, noticeably outperforming ChrF++ ... at 34.23 and 64.92."
- Critique: correlation on graded quality scores, not binary defect detection; generation tasks, not review.

**[CodeJudgeBench] Jiang, Chen, Cao, Lee, Tan. "CodeJudgeBench: Benchmarking LLM-as-a-Judge for Coding Tasks." arXiv 2507.10535 (v2 2025-08-14); ACL 2026 (per search snippet, venue UNVERIFIED).** https://arxiv.org/abs/2507.10535. Status: VERIFIED (abstract + PDF Table 3).
- "benchmarking of 26 LLM-as-a-Judge models, we find that recent thinking models significantly outperform non-thinking models ... even relatively small thinking models, such as Qwen3-8B, can outperform specially trained LLM-as-a-Judge models up to 70B in size. Nevertheless, all models still exhibit significant randomness ... simply changing the order in which responses are presented can substantially impact accuracy." "pair-wise comparison outperforms scalar point-wise judging."
- [PDF] Position: "model performance varies substantially depending on the order, with discrepancies reaching up to 14%." "RM-R1 32B and Claude 3.7 consistently exhibit recency bias."
- [PDF] Table 3, pairwise accuracy averaged over CodeGen/CodeRepair/TestGen (chance = 50%): Gemini-2.5-Pro 82.12; Claude-4-Sonnet 79.93; QwQ-32B 76.40; Qwen3-32B 72.42; Qwen3-14B 71.18; Qwen3-8B 65.60; non-thinking: Claude-3.5-Sonnet-v2 59.12, Qwen2.5-Coder-32B 57.20, Skywork-Critic-70B 55.98, Self-Taught-70B 56.36, Gemini-2.0-Flash-Lite 53.22, AceCodeRM-7B 52.92. Hard-split CodeGen: best 62.24 (Gemini-2.5-Pro), most 36-50.
- Critique: preprint; data from LiveCodeBench (problems May 2023-Apr 2025); pairwise on competition code, not PR diffs. Non-thinking open judges sit near coin-flip.

**[CRScore] Naik, Alenius, Fried, Rose. "CRScore: Grounding Automated Evaluation of Code Review Comments in Code Claims and Smells." arXiv 2409.19801.** https://arxiv.org/abs/2409.19801. Status: VERIFIED (abstract).
- "greatest alignment with human judgment among open source metrics (0.54 Spearman correlation) ... We also release a corpus of 2.9k human-annotated review quality scores."
- Critique: 0.54 is the *best* automated metric; review-quality evaluation remains weakly correlated with humans.

**[SWE-PRBench] Kumar. "SWE-PRBench: Benchmarking AI Code Review Quality Against Pull Request Feedback." arXiv 2603.26130 (2026-03-27).** https://arxiv.org/abs/2603.26130. Status: VERIFIED (abstract).
- "benchmark of 350 pull requests ... LLM-as-judge framework validated at kappa=0.75, 8 frontier models detect only 15-31% of human-flagged issues on the diff-only configuration". "All 8 models degrade monotonically from config_A [diff only] to config_C [full context]". "a structured 2,000-token diff-with-summary prompt outperforms a 2,500-token full-context prompt".
- Critique: single-author preprint; judge κ=0.75 is the evaluation judge, not the reviewer.

**[SWR-Bench] Zeng et al. "SWR-Bench: Assessing LLM Performance in Real-World Code Review Comment Generation." arXiv 2509.01494.** https://arxiv.org/abs/2509.01494. Status: VERIFIED (abstract).
- "1000 manually verified Pull Requests ... LLM-based evaluation method that aligns strongly with human judgment (~90 agreement) ... current systems underperform ... multi-review aggregation strategy ... increasing F1 scores by up to 43.67%."
- Search snippet (UNVERIFIED): manual review of 100 of 1,101 false positives from Gemini-2.5-Pro-based PR-Review.

**[CRBugBench] "(When) Should a Software Factory be Lights-off? Benchmarking Code Review Agents on Bug Detection." arXiv 2610.13668 (2026-10-09).** https://arxiv.org/abs/2610.13668. Status: VERIFIED (abstract + PDF intro).
- "1,000 review tasks across 98 open-source GitHub repositories, and 800 additional tasks from proprietary industry repositories ... the best (claude-opus-5 with copilot-cli) catches 71.9% of bugs within its top-5 comments, up from 47.7% (opus-4.6) in five months". [PDF] "catches 79.6% of bugs that humans found before merge, and 64.2% of bugs that humans found after merge, within top-5 review comments." [PDF] proprietary portion: "dropping up to 25.5% performance".
- Critique: very fresh preprint (6 days before access); measures recall@top-5, not precision; frontier-only cohort.

**[BiggerNotBetter] "Bigger Isn't Always Better: A Comparative Evaluation of LLMs for Automated Code Review." arXiv 2606.15689.** https://arxiv.org/abs/2606.15689. Status: VERIFIED (abstract).
- "150 code review samples - 100 synthetic mutation-injected bugs and 50 real bug-fix pull requests ... Claude Haiku 4.5 ... higher F1 (0.365 vs. 0.343) ... on real PRs alone, the best model achieves F1 = 0.066, compared to F1 = 0.847 on synthetic samples ... F1 dropping from 0.657 on diffs under 10 lines to 0.043 on diffs over 150 lines ... near-zero recall on performance-related bugs."
- Critique: small n, preprint; strong evidence that synthetic benchmarks overstate review ability and that diff size matters.

### B. Vulnerability / defect detection precision

**[PrimeVul] Ding et al. "Vulnerability Detection with Code Language Models: How Far Are We?" arXiv 2403.18624; ICSE 2025.** https://arxiv.org/abs/2403.18624. Status: VERIFIED (abstract); Table VIII numbers UNVERIFIED (search snippet: GPT-4 P-C 5.14 two-shot, 12.94 CoT vs random 22.70).
- "a state-of-the-art 7B model scored 68.26% F1 on BigVul but only 3.09% F1 on PrimeVul. Attempts to improve performance through advanced training techniques and larger models like GPT-3.5 and GPT-4 were unsuccessful, with results akin to random guessing in the most stringent settings."

**[Ullah2024] Ullah et al. "LLMs Cannot Reliably Identify and Reason About Security Vulnerabilities (Yet?)" arXiv 2312.12575; IEEE S&P 2024.** https://arxiv.org/abs/2312.12575. Status: VERIFIED (abstract).
- "228 code scenarios ... eight of the most capable LLMs ... LLMs provide non-deterministic responses, incorrect and unfaithful reasoning ... by merely changing function or variable names, or by the addition of library functions in the source code, these models can yield incorrect answers in 26% and 17% of cases, respectively."

**[VulRAG] Du et al. "Vul-RAG." arXiv 2406.11147.** https://arxiv.org/abs/2406.11147. Status: VERIFIED (abstract).
- LLMs' "limitations in distinguishing between vulnerable and similar-but-benign patched code (only 0.06 - 0.14 accuracy)"; Vul-RAG "accuracy increase of 16% - 24%"; explanations improve "manual detection accuracy (from 60% to 77%)".

**[JinChen2025] Jin, Chen. "Uncovering Systematic Failures of LLMs in Verifying Code Against Natural Language Specifications." arXiv 2508.12358; ASE 2025 NIER.** https://arxiv.org/abs/2508.12358. Status: VERIFIED (abstract).
- "LLMs frequently misclassify correct code implementations as either 'not satisfying requirements' or containing potential defects. Surprisingly, more complex prompting, especially ... explanations and proposed corrections, leads to higher misjudgment rate".
- Critique: NIER short paper; directly relevant: reviewers over-flag correct code.

**[Alexopoulos2026] "Measuring and Exploiting Contextual Bias in LLM-Assisted Security Code Review." arXiv 2603.18740 (v4).** https://arxiv.org/abs/2603.18740. Status: VERIFIED (abstract); "framing reduces detection 16-93%" figure UNVERIFIED (search snippet only).
- "6 LLMs under five framing conditions ... 33 CVEs across 20 real-world projects and two popular ACR pipelines (Claude Code and CodeRabbit) ... Our refinement attack ... is successful in 32/33 (97%) cases".
- Gate implication: PR description/metadata can steer an LLM gate; never let it be the sole security control.

### C. Biases and non-determinism

**[Zheng2023] Zheng et al. "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena." arXiv 2306.05685; NeurIPS 2023 D&B.** Status: VERIFIED (abstract). "position, verbosity, and self-enhancement biases ... GPT-4 ... achieving over 80% agreement, the same level of agreement between humans." Critique: chat, not code.

**[WangP2023] Wang et al. "Large Language Models are not Fair Evaluators." arXiv 2305.17926.** Status: VERIFIED (abstract). "Vicuna-13B could beat ChatGPT on 66 over 80 tested queries with ChatGPT as an evaluator" by reordering; proposes "Balanced Position Calibration, which aggregates results across various orders".

**[Shi2024] Shi et al. "Judging the Judges: A Systematic Study of Position Bias in LLM-as-a-Judge." arXiv 2406.07791; AACL-IJCNLP 2025.** Status: VERIFIED (abstract). "15 LLM judges across MTBench and DevBench ... over 150,000 evaluation instances ... position bias is not due to random chance ... strongly affected by the quality gap between solutions."

**[Thakur2024] "Judging the Judges: Evaluating Alignment and Vulnerabilities in LLMs-as-Judges." arXiv 2406.12624; GEM2 2025.** Status: VERIFIED (abstract). "only the best (and largest) models achieve reasonable alignment with humans ... sensitivity to prompt complexity and length, and a tendency toward leniency ... judges with high percent agreement can still assign vastly different scores."

**[Ouyang2023] Ouyang, Zhang, Harman, Wang. "An Empirical Study of the Non-determinism of ChatGPT in Code Generation." arXiv 2308.02828.** Status: VERIFIED (abstract). "829 code generation problems ... ratio of coding tasks with zero equal test output across different requests is 75.76%, 51.00%, and 47.56% for CodeContests, APPS, and HumanEval ... setting the temperature to 0 does not guarantee determinism".

**[Atil2024] Atil et al. "Non-Determinism of 'Deterministic' LLM Settings." arXiv 2408.04667.** Status: VERIFIED (abstract). "five LLMs ... eight common tasks ... 10 runs ... accuracy variations up to 15% across naturally occurring runs with a gap of best possible performance to worst possible performance up to 70%."

**[He2025] Horace He / Thinking Machines. "Defeating Nondeterminism in LLM Inference." Blog, 2025-09-10.** https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/. Status: VERIFIED [web]. Sampled 1000 completions at temperature 0 from Qwen3-235B-A22B-Instruct-2507: "we generate 80 unique completions, with the most common of these occuring 78 times." Cause: batch size varies with server load (lack of batch invariance). Critique: vendor blog, but reproducible.

### D. Industrial deployments with measured acceptance

| Key | Org / tool | Metric (verbatim) | n | Status |
|---|---|---|---|---|
| [GoogleMLEdits2024] "Resolving Code Review Comments with ML", research.google/pubs/resolving-code-review-comments-with-machine-learning/ | Google, ML-suggested edits for reviewer comments (ICSE-SEIP 2024 "to appear" per page; authors incl. Zheng, Chandra, Maniatis; full author list not checked) | "code-change authors at Google address 7.5% of all reviewer comments by applying an ML-suggested edit" | "millions of reviewer comments per year" | VERIFIED [web, research.google pub page] |
| [AutoCommenter] Vijayvergiya et al. arXiv 2405.13565, AIware '24 | Google best-practice LLM commenter | [PDF] "useful ratio plateaued at around 54%"; rater study "60%"; suppressing 17 non-actionable URLs "increased the historical useful ratio from 54% to 66% on developer feedback, and from 60% to 74% on rater feedback"; "target useful ratio of 80%"; "comment-resolution rate is about 40%"; "about 10% of automated comments" get explicit feedback | 15 raters; 6000 snapshot pairs; 40 manually inspected | VERIFIED |
| [MetaMateCR] Maddila et al. arXiv 2507.13499 (FSE 2026 industry, per researchr; UNVERIFIED) | Meta, AI patches for reviewer comments | "ActionableToApplied rate of 19.7%, which is a 9.2pp improvement over GPT-4o"; safety trial "reviewers taking over 5% longer"; "64k <review comment, patch>" benchmark | production | VERIFIED |
| [Cihan2025] arXiv 2412.18531, ICSE-SEIP 2025 | Beko, Qodo PR-Agent + GPT-4 Turbo (per search; abstract says Qodo PR Agent) | "73.8% of automated comments were resolved. However, the average pull request closure duration increased from five hours 52 minutes to eight hours 20 minutes" | "4,335 pull requests, 1,568 of which underwent automated reviews"; 22 surveyed | VERIFIED |
| [RevMate] Olewicki et al. arXiv 2411.07091 | Mozilla & Ubisoft, RAG + LLM-as-judge filter | "8.1% and 7.2% ... accepted"; "Refactoring-related comments ... (18.2% and 18.6% compared to 4.8% and 5.2%)" for Functional; "median of 43s per patch" | ">587 patch reviews" | VERIFIED |
| [RovoDev] Tantithamthavorn et al. arXiv 2601.01129, ICSE-SEIP 2026 | Atlassian | "code resolution for 38.70%"; "decreasing the PR cycle time by 30.8%"; "reducing the number of human-written comments by 35.6%"; human comment resolution 44.45% (search snippet, UNVERIFIED) | >1,900 repos, >54,000 comments (search snippet, UNVERIFIED) | VERIFIED (abstract) |
| [uReview] Uber blog 2025-08-12 (Mahajan, Roy Choudhary, Bond) | Uber | "Engineers who interact with the tool mark 75% of its comments as useful"; "over 65% of its posted comments addressed"; "only 51% of human-written comments" [addressed]; best config "Claude-4-Sonnet as the primary comment generator" + "o4-mini-high as the review grader" | "over 90% of the weekly ~65,000 diffs" | VERIFIED [web]; vendor blog, self-measured |
| [Bugbot] Cursor forum summary of blog, 2026-01-16 | Cursor Bugbot | "pushed resolution rates from ~52% to over 70%"; resolution measured by "an AI-powered judge that checks, at merge time, which Bugbot-reported issues actually got fixed" | "around 40 major experiments" | VERIFIED [web, forum repost]; "80% at default effort" (May 2026 changelog) UNVERIFIED |
| [Ericsson] Ramesh et al. arXiv 2507.19115, ICSME 2025 | Ericsson | qualitative "encouraging results" only | preliminary | VERIFIED (abstract); no numbers |

Critique across the table: acceptance/"resolved"/"addressed" metrics are not precision. Self-reported vendor numbers (Uber, Cursor, Atlassian) use LLM judges or proxy signals. Acceptance of *generated comments* clusters at 7-40% for independent/academic setups (RevMate 7-8%, AutoCommenter ~40% resolution, RovoDev 38.7%) and 65-74% for filtered/vendor-tuned setups (Beko 73.8%, Uber 65%, Bugbot >70%).

### E. Where must an LLM judge never block? (synthesis from evidence above)
- Security verdicts as the sole control: [PrimeVul], [Ullah2024], [VulRAG], [Alexopoulos2026] (97% framing-attack success).
- "Is this code correct per spec" without execution: [JinChen2025] over-flags correct code.
- Large diffs: [BiggerNotBetter] F1 0.043 on >150-line diffs; [SWE-PRBench].
- Non-thinking small judges in pairwise/binary judging: [CodeJudgeBench] ~53-59% vs 50% chance.
- Static-warning triage as a ground-truth replacement: [Ahmed2024] α 0.15 vs human 0.80.

---

## RQ5: Prompt structure

**[Pornprasit2024] Pornprasit, Tantithamthavorn. "Fine-Tuning and Prompt Engineering for LLMs-based Code Review Automation." arXiv 2402.00905 (IST).** Status: VERIFIED (abstract). "GPT-3.5 with few-shot learning achieves 46.38% - 659.09% higher EM than GPT-3.5 with zero-shot learning ... few-shot learning without a persona should be used". Critique: EM vs reference reviews (CodeReviewer-style), GPT-3.5 cohort.

**[Tam2024] Tam et al. "Let Me Speak Freely? A Study on the Impact of Format Restrictions on Performance of LLMs." arXiv 2408.02442.** Status: VERIFIED (abstract). "a significant decline in LLMs reasoning abilities under format restrictions ... stricter format constraints generally lead to greater performance degradation in reasoning tasks."

**[Kurt2024] Will Kurt (.txt). "Say What You Mean: A Response to 'Let Me Speak Freely'." blog.dottxt.ai.** Status: VERIFIED [web], date not on page. Rerun with Llama-3-8B-Instruct: "our structured results directly contradict the findings of the paper"; "our overall winner is structured JSON with 77% accuracy!"; tables (GSM8K 0.77 unstructured vs 0.78 structured; Last Letter 0.73 vs 0.77). Critique: vendor of constrained decoding (conflict of interest), but identifies prompt mismatch in Tam et al. Net: reason-then-JSON (put a free-text reasoning field before the verdict field, or two-stage) is the safe pattern.

**[Wei2022-CoT] Wei et al. "Chain-of-Thought Prompting Elicits Reasoning in LLMs." arXiv 2201.11903 v6.** Status: VERIFIED [PDF]. "chain of thought actually hurts performance for most models smaller than 10B parameters." Critique: 2022 cohort (LaMDA/PaLM/GPT-3); modern 4B reasoning-trained models (Qwen3) differ, cf. [CodeJudgeBench] where Qwen3-8B thinking beats 70B non-thinking judges.

**[Luo2025] "Through the Valley: Path to Effective Long CoT Training for Small Language Models." arXiv 2506.07712; EMNLP 2025.** Status: VERIFIED (abstract). "small language models (SLMs; <=3B parameters) trained on limited long CoT data experience significant performance deterioration ... lose up to 75% of their original performance".

**[Liu2024-MindStep] "Mind Your Step (by Step): Chain-of-Thought can Reduce Performance on Tasks where Thinking Makes Humans Worse." arXiv 2410.21333.** Status: VERIFIED (abstract). "up to 36.3% absolute accuracy [drop] for OpenAI o1-preview compared to GPT-4o" on some tasks.

**[MultiVer] Rajan. arXiv 2602.17875.** Status: VERIFIED (abstract). Per-dimension decomposition: "four-agent ensemble (security, correctness, performance, style) with union voting achieves 82.7% recall ... 48.8% precision versus 63.9% for fine-tuned baselines ... multi-agent ensemble adds 17 percentage points recall over single-agent". Critique: single-author preprint. Lesson: per-dimension decomposition plus union voting raises recall but cuts precision; it is the wrong combination for a blocking gate unless followed by a verification pass.

**[VulAgent] Wang et al. arXiv 2509.11523.** Status: VERIFIED (abstract). Hypothesis plus trigger-path validation "reduces the false positive rate by about 36% compared with state-of-the-art LLM-based baselines", "improves overall accuracy by 6.6%".

**[RefuteOrPromote] Agarwal. arXiv 2604.19049.** Status: VERIFIED (abstract). Adversarial verification gate "killed roughly 79% of 171 candidates ... on a consolidated-protocol subset (lcms2, wolfSSL; n=30), the prospective kill rate was 83%." "ten dedicated reviewers unanimously endorsed a non-existent Bleichenbacher padding oracle in OpenSSL's CMS module; it was killed only by a single empirical test". Critique: single author, campaign report, no control. Strong qualitative support for "require a concrete reproduction before a finding blocks" and for the view that agreement between LLMs is not evidence.

**[ZeroFalse] Iranmanesh et al. arXiv 2510.02534.** Status: VERIFIED (abstract). LLM adjudication of SAST output: "F1-scores of 0.912 on the OWASP Java Benchmark and 0.955 on the OpenVuln dataset, maintaining recall and precision above 90% ... CWE-specialized prompting consistently outperforms generic prompts, and reasoning-oriented LLMs provide the most reliable precision-recall balance." Critique: OWASP Benchmark is synthetic and likely in training data (contamination).

**[TencentFP] Du et al. "Reducing False Positives in Static Bug Detection with LLMs: An Empirical Study in Industry." arXiv 2601.18844 (ICSE-SEIP 2026 per researchr, UNVERIFIED).** Status: VERIFIED (abstract). "433 alarms (328 false positives, 105 true positives) ... hybrid techniques of LLM and static analysis eliminate 94-98% of false positives with high recall ... per-alarm costs as low as 2.1-109.5 seconds and $0.0011-$0.12"; manual "10-20 minutes of manual inspection per alarm". Snippet (UNVERIFIED): recall "below the enterprise-expected threshold of 90%".

**[LLM4FPM] Chen et al. arXiv 2411.03079.** Status: VERIFIED (abstract). "F1 > 99% across various Common Weakness Enumerations" on Juliet (synthetic), "label accuracy on the D2A dataset to 86%".

**[SAST-Genius] Agrawal, Ahi. arXiv 2509.15433.** Status: VERIFIED (abstract). "reduced false positives by about 91 % (225 to 20) compared to Semgrep alone." Critique: arXiv JREF says "IEEE S&P 2025" but reads as a short report; treat cautiously.

**[LLM4Vuln] Sun et al. arXiv 2401.16185.** Status: VERIFIED (abstract). "147 ground-truth vulnerabilities and 147 non-vulnerable cases in 3,528 controlled scenarios ... varying impacts of knowledge enhancement, context supplementation, and prompt schemes." No single headline FP number.

**[Self-consistency] Wang et al. arXiv 2203.11171, ICLR 2023.** Status: VERIFIED (abstract). "GSM8K (+17.9%) ... ARC-challenge (+3.9%)". For code: [CodeT] below.

**Context scope:** [SWE-PRBench] (diff-only beats full-context, monotonic degradation in all 8 models); [ContextCRBench] Hu et al. arXiv 2511.07017, VERIFIED (abstract): "textual context yields greater performance gains than code context alone" (67,910 entries; ByteDance deployment "+61.98%"). [BiggerNotBetter] diff-size effect.

**"No findings" / pressure to find something:** no direct study found. Closest: [JinChen2025] (over-critique of correct code, worse with elaborate prompts); [Thakur2024] leniency; [Alexopoulos2026] framing. UNVERIFIED gap: no controlled study of "explicitly permit empty findings" found in ~10 searches.

---

## RQ6: False-positive control

**Precision bar.** [Tricorder] <10% effective FP at code review; probation at ≥10% not-useful; off at >25%. [AutoCommenter] internal target "useful ratio of 80%" before wider rollout (implied ≤20% not-useful for advisory comments). Coverity/Infer bars: prior VERIFIED.

**Confidence gating.**
- [Xiong2024] arXiv 2306.13063, ICLR 2024. VERIFIED (abstract): "LLMs, when verbalizing their confidence, tend to be overconfident ... As model capability scales up, both calibration and failure prediction performance improve ... white-box ... 0.522 to 0.605 in AUROC ... all investigated methods struggle in challenging tasks, such as those requiring professional knowledge".
- [Spiess2025] "Calibration and Correctness of Language Models for Code." arXiv 2402.02047, ICSE 2025. VERIFIED (abstract): "generative code models we test are not well-calibrated out of the box ... calibration can be improved using standard methods, such as Platt scaling. Since Platt scaling relies on the prior availability of correctness data".
- [AutoCommenter] [PDF]: model "outputs a confidence score ranging from 0 to 1"; comments suppressed "if its confidence score is below some threshold t". Deployed thresholding works when the score is a trained model probability, not a verbalized one.

**Ensembles / dual-model agreement.**
- [PoLL] Verga et al. arXiv 2404.18796. VERIFIED (abstract): "a PoLL composed of a larger number of smaller models outperforms a single large judge, exhibits less intra-model bias ... over seven times less expensive." Chat QA, not code.
- [uReview]: generator plus separate grader model (Claude-4-Sonnet + o4-mini-high) was the best configuration by F1.
- Counter-evidence: [RefuteOrPromote] ten agreeing reviewers endorsed a nonexistent vuln; [MultiVer] union voting cuts precision. Use intersection or verification, not union.

**Suppression, dedup, baselines (tooling docs).**
- Semgrep diff-aware scanning [web, docs.semgrep.dev, VERIFIED]: "A diff-aware scan shows only findings caused by changes in files starting from a specific Git baseline." `SEMGREP_BASELINE_REF` "typically your trunk branch". "Cross-file analysis is not supported for diff-aware scans."
- SonarQube [web, VERIFIED]: "New code is code that you've recently added or modified." "the built-in Sonar way quality gate defines conditions applying to new code only."
- GitHub code scanning [web, VERIFIED]: "Any new alerts on lines of code changed in the pull request are shown as annotations"; check fails by default for "`error`, `critical`, or `high`", configurable.
- Snyk .snyk [web, VERIFIED]: "The `expires` field is optional. If you need a permanent ignore, omit the field." Malformed date means "the ignore will be respected and persist indefinitely" (a footgun: validate expiry format in CI).
- [AutoCommenter] dedup/suppression-by-category moved useful ratio 54%→66%.
- [Tricorder] changed-lines-only display.

**Sample-size math for precision** (my own computation; Wilson score interval [Wilson1927] JASA 22:209-212, VERIFIED (metadata only) via Crossref; recommended by [Brown2001] "Interval Estimation for a Binomial Proportion", Statistical Science 16(2):101-133, VERIFIED (metadata only)). Minimum number of labelled findings n such that the Wilson lower bound ≥ 0.90:

| False positives observed | n (two-sided 95%, z=1.96) | n (one-sided 95%, z=1.645) |
|---|---|---|
| 0 | 35 | 25 |
| 1 | 53 | 42 |
| 2 | 69 | 58 |
| 5 | 113 | 100 |
| 10 | 179 | 164 |

Exact binomial zero-failure check: 0.9^n ≤ 0.05 needs n = 29. Practical rule: ~50-70 labelled findings per check/category with ≤1-2 FPs before turning on blocking; re-label a fresh sample after every model/prompt change ([Atil2024] and [He2025] show runs differ).

---

## RQ7: Generate → test → repair loops

**Gains concentrate in early iterations.**
- [SelfDebug] Chen, Lin, Schärli, Zhou. arXiv 2304.05128 (venue not checked). VERIFIED (abstract + PDF). Abstract: "improves the baseline accuracy by up to 12%". [PDF]: "We set the maximum number of debugging turns to be 10, though empirically the successful debugging processes mostly end within 3 turns." "the major improvement comes from the first debugging turn. Specifically, a single debugging turn with the full feedback improves over the greedy decoding accuracy by around 12%."
- [DDI] Adnan, Kuhn. "The Debugging Decay Index." arXiv 2506.18403; Sci Rep 15, 2025. VERIFIED (abstract): "most models lose 60-80% of their debugging capability within just 2-3 attempts". Remedy: "strategic fresh start". Critique: HumanEval only (search snippet). Per-model numbers (Llama3.1 72.6→82.8) are UNVERIFIED.
- [Olausson] (prior VERIFIED): gains modest; bottleneck is feedback quality; [PDF] grid (n_p, n_fr) ∈ {1,2,5,10,25}×{1,3,5,10}; "improves with diverse initial samples". Implication: resample before deeper repair.
- [Reflexion] Shinn et al. arXiv 2303.11366. VERIFIED (abstract): "91% pass@1 accuracy on the HumanEval coding benchmark, surpassing the previous state-of-the-art GPT-4 that achieves 80%." Critique: uses self-generated tests; HumanEval contamination.
- [LDB] Zhong et al. arXiv 2402.16906. VERIFIED (abstract): "consistently enhances the baseline performance by up to 9.8%".
- [AlphaCodium] Ridnik et al. arXiv 2401.08500. VERIFIED (abstract): "GPT-4 accuracy (pass@5) increased from 19% with a single well-designed direct prompt to 44% with the AlphaCodium flow." Vendor (Codium/Qodo).
- [Huang2024] (prior): intrinsic self-correction without external feedback can degrade.
- [Pan2024] (prior): same-model generator/evaluator leads to reward hacking.

**Passing tests while wrong.**
- [Smith2015] Smith, Barr, Le Goues, Brun. "Is the cure worse than the disease? overfitting in automated program repair." ESEC/FSE 2015, DOI 10.1145/2786805.2786825. VERIFIED (metadata via Crossref) + tech report UM-CS-2015-007 [PDF] read: "we use one test suite as 'training' data to construct a patch, and another as 'evaluation' or 'held-out' data ... Patches that are overly specific to the training tests and fail to generalize to the held-out tests overfit"; dataset "956 student-written programs with defects". Headline quantitative findings not extracted (2-column PDF garbled) and are UNVERIFIED.
- [Qi2015] Qi, Long, Achour, Rinard. ISSTA 2015, DOI 10.1145/2771783.2771791. VERIFIED [PDF]: "GenProg produced a correct patch for only 2 of the 105 considered defects. RSRepair produced a correct patch for only 2 of the 24 considered defects. AE produced a correct patch for only 3 of the 105". "The overwhelming majority of the reported patches are not correct and are equivalent to a single modification that simply deletes functionality."
- [PatchDiff] Wang, Pradel, Liu. arXiv 2503.15223 (ICSE 2026 per researchr, UNVERIFIED). VERIFIED (abstract): "7.8% of all patches to count as correct while failing the developer-written test suite ... (29.6%) plausible patches induce different behavior than the ground truth ... 28.6% of behaviorally divergent patches are certainly incorrect ... inflation of reported resolution rates by 6.2 absolute percent points."
- [SWE-Bench+] Aleithan et al. arXiv 2410.06992. VERIFIED (abstract): "32.67% of the successful patches involve cheating ... 31.08% of the passed patches are suspicious patches due to weak test cases ... resolution rate of SWE-Agent+GPT-4 dropped from 12.47% to 3.97%."
- [Ahmed2025-overfit] Ahmed, Ganhotra, Shinnar, Hirzel. "Investigating Test Overfitting on SWE-bench." arXiv 2511.16858. VERIFIED (abstract, no numbers): "Some systems even iteratively refine code and tests jointly. This paper presents the first empirical study of test overfitting in this setting." Snippet claim "APR with white-box tests improves performance on black-box tests" is UNVERIFIED.

**Test-generation conflict of interest.**
- [Konstantinou2024] "Can we find bugs using LLM-generated oracles?" arXiv 2410.21136. VERIFIED (abstract): "test cases and oracles ... for 24 Java repositories. Our findings show that LLM-based test generation approaches mainly capture the actual program behavior making bug detection difficult. We also find that LLMs are better at generating oracles than classifying them." This is the direct evidence that model-written tests encode existing (buggy) behaviour.
- [CodeT] Chen et al. arXiv 2207.10397. VERIFIED (abstract): dual execution agreement; "pass@1 metric on HumanEval to 65.8%, ... absolute improvement of 18.8% over the code-davinci-002 model". Uses agreement across many samples rather than trusting one test set.
- [AgentCoder] Huang et al. arXiv 2312.13010. VERIFIED (abstract): separate "test designer agent"; "96.3% and 91.8% pass@1 in HumanEval and MBPP". Separation of roles in the same model family; contamination likely.

**Stop rule "give up after 3 retries" vs evidence.** [SelfDebug] (most successes ≤3 turns, biggest gain turn 1), [DDI] (60-80% capability lost within 2-3 attempts), and [Olausson] (resampling is often better than deeper repair) all support a cap of about 3, ideally with a fresh-context restart or a new sample rather than continued conversation. Passing tests is not acceptance evidence on its own ([Qi2015], [PatchDiff], [SWE-Bench+]). Gate tests should be human-owned or held out from the generator ([Smith2015], [Konstantinou2024]).

---

## Summary table

| Key | RQ | Finding (number) | n / setting | Status | Caveat |
|---|---|---|---|---|---|
| Ahmed2024 | 4 | SA-warning α: human-human 0.80, human-LLM 0.15 | 1,306-sample dataset, 2 humans | VERIFIED | preprint, 2024 models |
| WangR2025 | 4 | Pearson 81.32 / 68.51 vs humans | 3 SE datasets | VERIFIED | quality scores, not defects |
| CodeJudgeBench | 4,10 | Up to 14% swing by order; non-thinking judges 53-59% (chance 50) | 26 judges | VERIFIED | competition code |
| CRScore | 4 | Spearman 0.54 best metric | 2.9k annotations | VERIFIED | — |
| SWE-PRBench | 4,5 | 15-31% issue detection; diff-only best | 350 PRs, 8 models | VERIFIED | single author |
| CRBugBench | 4 | 71.9% bugs in top-5 (best); -25.5% on proprietary | 1,800 tasks | VERIFIED | recall only, 2026-10 |
| BiggerNotBetter | 4,5 | Real-PR F1 0.066; >150-line diff F1 0.043 | 150 samples | VERIFIED | small n |
| PrimeVul | 4 | 7B: 68.26%→3.09% F1; GPT-4 ≈ random | PrimeVul | VERIFIED | — |
| Ullah2024 | 4 | 26%/17% flips on renaming | 228 scenarios | VERIFIED | S&P 2024 |
| VulRAG | 4 | 0.06-0.14 pair accuracy | — | VERIFIED | — |
| Alexopoulos2026 | 4 | 32/33 (97%) framing attacks succeed | 33 CVEs | VERIFIED | preprint |
| Ouyang2023 | 4 | 75.76% tasks zero equal output; T=0 not deterministic | 829 problems | VERIFIED | ChatGPT 2023 |
| Atil2024 | 4 | up to 15% accuracy swing over 10 runs | 5 LLMs, 8 tasks | VERIFIED | — |
| He2025 | 4 | 80 unique of 1000 at T=0 | Qwen3-235B | VERIFIED | blog |
| GoogleMLEdits2024 | 4 | 7.5% of comments resolved by ML edit | Google | VERIFIED | edits, not findings |
| AutoCommenter | 4,6 | useful 54%→66% via suppression; target 80%; ~40% resolution | Google | VERIFIED | T5-based |
| MetaMateCR | 4 | 19.7% ActionableToApplied; +5% review time w/ naive UX | Meta | VERIFIED | — |
| Cihan2025 | 4 | 73.8% resolved; PR close 5h52→8h20 | 1,568 PRs | VERIFIED | ICSE-SEIP 2025 |
| RevMate | 4 | 8.1% / 7.2% accepted | >587 reviews | VERIFIED | — |
| RovoDev | 4 | 38.70% resolution; -30.8% cycle time | Atlassian | VERIFIED | vendor |
| uReview | 4,6 | 75% useful, 65% addressed vs 51% human | ~65k diffs/wk | VERIFIED (web) | vendor blog |
| Bugbot | 4 | resolution ~52%→>70% | 40 experiments | VERIFIED (forum) | LLM-judged metric |
| Pornprasit2024 | 5 | few-shot +46-659% EM; no persona | GPT-3.5 | VERIFIED | EM metric |
| Tam2024 / Kurt2024 | 5 | format limits hurt reasoning / rebuttal 0.77 structured | — | VERIFIED | contested |
| Wei2022-CoT | 5 | CoT hurts <10B | 2022 models | VERIFIED | old cohort |
| MultiVer | 5,6 | union voting: recall 82.7%, precision 48.8% | PyVul | VERIFIED | single author |
| VulAgent | 5 | -36% FPR via hypothesis/trigger-path validation | 2 datasets | VERIFIED | — |
| RefuteOrPromote | 5,6 | 79-83% candidates killed; 10 agents agreed on nonexistent bug | 171 / 30 | VERIFIED | campaign report |
| ZeroFalse | 5,6 | F1 0.912 / 0.955; P,R >90% | OWASP, OpenVuln | VERIFIED | synthetic bench |
| TencentFP | 5,6 | 94-98% FP removed | 433 alarms | VERIFIED | industry |
| Xiong2024 | 6 | verbalized confidence overconfident | 5 LLMs | VERIFIED | — |
| Spiess2025 | 6 | code LMs not calibrated; Platt helps with labels | ICSE 2025 | VERIFIED | — |
| PoLL | 6 | jury of small models > single large judge, 7x cheaper | 6 datasets | VERIFIED | non-code |
| Tricorder | 6 | <10% eff. FP; probation ≥10%; off >25% | Google | VERIFIED (spot) | — |
| Wilson/Brown | 6 | 0 FP needs n≥35 (two-sided) for LB≥0.90 | computed | VERIFIED (metadata) | my computation |
| SelfDebug | 7 | success mostly ≤3 turns; turn 1 ≈ +12% | — | VERIFIED | — |
| DDI | 7 | 60-80% debugging capability lost in 2-3 attempts | HumanEval | VERIFIED | one benchmark |
| Qi2015 | 7 | 2/105, 2/24, 3/105 correct | GenProg/RSRepair/AE | VERIFIED | pre-LLM |
| PatchDiff | 7 | 29.6% plausible patches diverge; +6.2pp inflation | SWE-bench Verified | VERIFIED | — |
| SWE-Bench+ | 7 | 31.08% passed patches weak-test suspicious | SWE-Agent+GPT-4 | VERIFIED | — |
| Konstantinou2024 | 7 | LLM oracles capture actual (buggy) behaviour | 24 Java repos | VERIFIED | — |
| CodeT | 7 | +18.8pp pass@1 via dual agreement | HumanEval | VERIFIED | contamination |
