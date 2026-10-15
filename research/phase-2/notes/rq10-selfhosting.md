# Phase 2 notes: RQ10, self-hosting per judge profile

Access date for all sources: 2026-10-15. Status key as in rq04-07 notes (VERIFIED / VERIFIED (metadata only) / UNVERIFIED). "[card]" = Hugging Face model card README fetched raw; "[PDF]" = pdftotext of arXiv PDF; "[web]" = WebFetch of the page (quoted fragments exact).

Profiles: (a) ~4B local, 8k context; (b) 30B-120B open-weight on 48-96 GB; (c) frontier cloud.

---

## 1. Capability evidence by size

### (a) ~4B class

**[Qwen3-4B-2507-card] Qwen/Qwen3-4B-Instruct-2507 model card.** https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507. Status: VERIFIED [card]. Vendor self-reported.
- "Number of Parameters: 4.0B"; "Context Length: **262,144 natively**."
- "This model supports only non-thinking mode and does not generate `<think></think>` blocks in its output. Meanwhile, specifying `enable_thinking=False` is no longer required."
- Table (GPT-4.1-nano / Qwen3-30B-A3B non-thinking / Qwen3-4B non-thinking / Qwen3-4B-Instruct-2507): LiveCodeBench v6 (25.02-25.05) 31.5 / 29.0 / 26.4 / **35.1**; MultiPL-E 76.3 / 74.6 / 66.6 / 76.8; Aider-Polyglot 9.8 / 24.4 / 13.8 / **12.9**; IFEval 74.5 / 83.7 / 81.2 / **83.4**; BFCL-v3 53.0 / 58.6 / 57.6 / 61.9.
- Recommended sampling: "Temperature=0.7, TopP=0.8, TopK=20, and MinP=0".
- Critique: vendor numbers; Aider-Polyglot 12.9% means it fails most real multi-file edit tasks; IFEval 83.4 suggests format adherence is adequate, especially with constrained decoding.

**[CodeJudgeBench] arXiv 2507.10535.** VERIFIED [PDF] (see rq04-07 notes). Non-thinking judges score near the 50% chance line on pairwise code judging (AceCodeRM-7B 52.92, Qwen2.5-Coder-32B 57.20, Claude-3.5-Sonnet-v2 59.12); thinking Qwen3-8B 65.60, Qwen3-14B 71.18, Qwen3-32B 72.42, QwQ-32B 76.40, frontier Gemini-2.5-Pro 82.12, Claude-4-Sonnet 79.93. "even relatively small thinking models, such as Qwen3-8B, can outperform specially trained LLM-as-a-Judge models up to 70B in size."
- Implication for the 4B profile: Qwen3-4B-Instruct-2507 is non-thinking by design. On the evidence above, a non-thinking judge in this class should be expected to be near chance on binary code-correctness judgments. No 4B model is in this table; extrapolation is mine.

**[RefactorSLM] Evaluating the Effectiveness of Small Language Models in Detecting Refactoring Bugs. arXiv 2502.18454.** https://arxiv.org/abs/2502.18454. VERIFIED (abstract + PDF).
- Abstract: models "Llama 3.2 3B, Mistral 7B, Gemma 2 9B, Gemma 3 12B, DeepSeek-R1 14B, Phi-4 14B, o1-mini, and o3-mini-high ... 100 refactoring bugs ... o3-mini-high ... identifying 84.3% of Type I bugs".
- [PDF] "Phi-4 14B achieves the highest detection rate (71.4%) for Type I bugs ... Mistral 7B exhibits the weakest performance (2.9%)". "Llama 3.2 3B and Gemma 2 9B show moderate performance, with detection rates ranging between 30.4% and 57.9%." "Llama 3.2 3B has the highest rate of incorrect explanations (32.9%)".
- Critique: recall-only (no clean-code false-positive rate); 100 bugs; 2024-25 cohort; Phi-4 14B is not Phi-4-mini (3.8B).

**[Wei2022-CoT]** [PDF] "chain of thought actually hurts performance for most models smaller than 10B parameters." VERIFIED; old cohort. **[Luo2025]** "SLMs; <=3B ... lose up to 75% of their original performance" after limited long-CoT SFT. VERIFIED (abstract).

**Phi-4-mini / Gemma 3 4B.** Phi-4-mini card downloaded (29 KB) but not mined for code numbers; Gemma 3 4B card is gated (128-byte response). No code-review benchmark for either found. UNVERIFIED gap.

### (b) 30B-120B open-weight

**[gpt-oss-card] OpenAI. "gpt-oss-120b & gpt-oss-20b Model Card." arXiv 2508.10925.** VERIFIED [PDF Table 3] + [card].
- Table 3 (low / medium / high reasoning): SWE-Bench Verified, 120b: 47.9 / 52.6 / **62.4**; 20b: 37.4 / 53.2 / **60.7**. Aider Polyglot, 120b: 24.0 / 34.2 / 44.4; 20b: 16.6 / 26.6 / 34.2. [PDF] "All SWE-bench evaluation runs use a fixed subset of n=477 verified tasks".
- [card] "gpt-oss-120b ... fit into a single 80GB GPU (like NVIDIA H100 or AMD MI300X) (117B parameters with 5.1B active parameters)"; "gpt-oss-20b ... (21B parameters with 3.6B active parameters)"; "MXFP4 quantization ... gpt-oss-20b model run within 16GB of memory"; "Configurable reasoning effort ... (low, medium, high)".
- Critique: vendor; reasoning effort changes scores by ~15pp, so pin it.

**[Qwen3-Coder cards] Qwen3-Coder-30B-A3B-Instruct and Qwen3-Coder-480B-A35B-Instruct.** VERIFIED [card].
- 30B: "Number of Parameters: 30.5B in total and 3.3B activated"; "Context Length: **262,144 natively**". 480B: "480B in total and 35B activated". Both: "If you encounter out-of-memory (OOM) issues, consider reducing the context length to a shorter value, such as `32,768`."
- The cards contain no SWE-bench numbers. The Qwen blog (2025-07-22) [web] claims only that 480B "achieves state-of-the-art performance among open-source models on SWE-Bench Verified without test-time scaling". The often-cited 69.6 (480B) and 51.6 (30B-A3B) figures are UNVERIFIED; third-party aggregators conflict (49.2 / 60.4 / 70.3 for 30B-A3B).

**[Qwen3-Coder-Next] Qwen3-Coder-Next Technical Report. arXiv 2603.00729.** VERIFIED (abstract + PDF Table 3).
- "80-billion-parameter model that activates only 3 billion parameters". Table 3, SWE-Bench Verified (SWE-Agent / MiniSWE-Agent / OpenHands), "maximum number of agent turns was set to 300": Qwen3-Coder-Next 70.6 / 71.1 / 71.3; DeepSeek-V3.2 (671A37) 70.2 / 67.2 / 72.6; GLM-4.7 (358A32) 74.2 / 70.4 / 70.6; Claude-Opus-4.5 78.2 / 77.8 / 79.0; Claude-Sonnet-4.5 76.0 / 68.4 / 74.6.
- Critique: vendor report, agentic SWE task (not review); SWE-bench contamination concerns ([SWE-Bench+]: "over 94% of the issues were created before LLM's knowledge cutoff dates").

**[Aider] Aider polyglot leaderboard.** https://aider.chat/docs/leaderboards/ and raw YAML (github.com/Aider-AI/aider, aider/website/_data/polyglot_leaderboard.yml). VERIFIED (YAML values cross-checked against WebFetch). n = 225 exercises (R1-0528: 224).
- Qwen3 32B 40.0% (well-formed 83.6%, 2025-05-08); Qwen3 235B A22B no-think 59.6% (92.9%); gpt-oss-120b (high) 41.8% (79.1%); Kimi K2 59.1%; DeepSeek R1 (0528) 71.4%; Llama 4 Maverick 15.6%; gpt-5 (high) 88.0%; Gemini 2.5 Pro (06-05, 32k think) 83.1% [WebFetch only]; claude-opus-4 (32k thinking) 72.0% [WebFetch only]. Qwen2.5-Coder-32B 16.4% [WebFetch only]. Llama 3.3 70B and Qwen3-Coder not listed.
- Critique: code editing, not review; "well-formed" (79-84% for gpt-oss-120b / Qwen3-32B) is a useful proxy for format-following failure rates under free-form output.

**[CodeJudgeBench]** thinking 14-32B open models reach 71-76% pairwise vs 80-82% frontier.

**Llama 3.3 70B.** HF card is gated (141-byte response). No direct code-review benchmark found. UNVERIFIED.

### (c) Frontier cloud
- [CRBugBench] arXiv 2610.13668: "the best (claude-opus-5 with copilot-cli) catches 71.9% of bugs within its top-5 comments, up from 47.7% (opus-4.6) in five months"; proprietary repos: "dropping up to 25.5% performance". Only frontier models evaluated. VERIFIED.
- [SWE-PRBench]: "8 frontier models detect only 15-31% of human-flagged issues" (diff-only). VERIFIED.
- [BiggerNotBetter] arXiv 2606.15689: Haiku 4.5 F1 0.365 > Sonnet 4.6 0.343; real PRs best F1 0.066. VERIFIED.
- [uReview]: generator Claude-4-Sonnet + grader o4-mini-high best by F1. VERIFIED [web].
- Gap between frontier and best open-weight on agentic SWE: ~5-8pp ([Qwen3-Coder-Next] Table 3). On pairwise code judging: ~6-10pp (QwQ-32B 76.4 vs Gemini-2.5-Pro 82.1).

---

## 2. Qwen3 thinking control

**[Qwen3-8B-card] Qwen/Qwen3-8B model card** (hybrid thinking models). VERIFIED [card].
- "`enable_thinking=True` # True is the default value for enable_thinking" in `tokenizer.apply_chat_template`.
- "We provide a hard switch to strictly disable the model's thinking behavior, aligning its functionality with the previous Qwen2.5-Instruct models." (`enable_thinking=False`). "In this mode, the model will not generate any think content and will not include a `<think>...</think>` block."
- Soft switch: "you can add `/think` and `/no_think` to user prompts or system messages to switch the model's thinking mode from turn to turn."
- Caveat: "when `enable_thinking=True`, regardless of whether the user uses `/think` or `/no_think`, the model will always output a block wrapped in `<think>...</think>`. However, the content inside this block may be empty". "When `enable_thinking=False`, the soft switches are not valid."
- "The `enable_thinking` switch is also available in APIs created by SGLang and vLLM."
- 2507 Instruct variants: non-thinking only ([Qwen3-4B-2507-card]); 2507 Thinking variants are separate models.

**[Qwen3-TR] Qwen3 Technical Report. arXiv 2505.09388.** VERIFIED (abstract): "integration of thinking mode ... and non-thinking mode ... into a unified framework ... thinking budget mechanism".

**[Ollama-thinking] docs.ollama.com/capabilities/thinking.** VERIFIED [web]. `think` field: "`true`: request thinking output." "`false`: request no thinking output, if the model permits it." "`null`: use the model default." gpt-oss levels via string values `["low","medium","high"]`, default "medium"; "Numbers are not supported."

---

## 3. Structured output

**[Ollama-SO] Ollama blog "Structured outputs", 2024-12-06.** https://ollama.com/blog/structured-outputs. VERIFIED [web]. "the `format` parameter can be used" to pass a JSON schema; tips: "Use Pydantic (Python) or Zod (JavaScript) to define the schema", "Add 'return as JSON' to the prompt", "Set the temperature to 0 for more deterministic output".

**[vLLM-SO] docs.vllm.ai Structured Outputs (latest).** VERIFIED [web].
- Options: `structured_outputs` with `json`, `choice`, `regex`, `grammar`, `structural_tag`; OpenAI-compatible `response_format` `{"type":"json_schema"}`.
- "vLLM supports the generation of structured outputs using xgrammar or guidance as backends." "The default backend is `auto`".
- Deprecation: the `guided_*` fields "were removed in v0.12.0" (`guided_json` → `{"structured_outputs": {"json": ...}}`).
- Reasoning: "you can use reasoning with any provided structured outputs feature." For Qwen3 Coder models, "structured outputs might become disabled if the reasoning content does not get parsed"; fix: `--structured-outputs-config.enable_in_reasoning=True`.

**[JSONSchemaBench] arXiv 2501.10868.** VERIFIED (abstract). "10K real-world JSON schemas ... evaluate six state-of-the-art constrained decoding frameworks, including Guidance, Outlines, Llamacpp, XGrammar, OpenAI, and Gemini." No headline number in the abstract; schema-feature coverage varies by framework, so keep gate schemas simple (flat objects, enums, required fields).

**Reasoning vs format:** [Tam2024] format limits hurt reasoning. [Kurt2024] rebuttal: structured output 0.77 vs 0.73 unstructured on Last Letter (Llama-3-8B). Practical pattern: allow a free-text `reasoning` field before `verdict` in the schema, or think first and then emit constrained JSON.

---

## 4. Memory: weights (Q4_K_M) and KV cache

**Weights, Ollama library pages** (VERIFIED [web/curl], 2026-10-15). Tag → download size, quantization:
| Model (Ollama tag) | Size | Quant |
|---|---|---|
| qwen3:4b-instruct-2507-q4_K_M | 2.5 GB | Q4_K_M |
| gemma3:4b | 3.4 GB | Q4_K_M (page also lists 2.5GB variant) |
| phi4-mini (3.8b) | 2.5 GB | not shown on page |
| gpt-oss:20b | 14 GB | MXFP4 |
| qwen3-coder:30b | 19 GB | Q4_K_M |
| llama3.3:70b | 43 GB | Q4_K_M |
| qwen2.5:72b | 47 GB | Q4_K_M |
| gpt-oss:120b | 65 GB | MXFP4 |

**KV cache: my computation from HF config.json** (VERIFIED configs; formula 2 × layers × kv_heads × head_dim × 2 bytes per token, f16). Ollama default KV type is f16; `q8_0` ≈ ½, `q4_0` ≈ ¼ ([Ollama-FAQ]).
| Model | layers / kv_heads / head_dim | 8k ctx | 32k ctx |
|---|---|---|---|
| Qwen3-4B-Instruct-2507 | 36 / 8 / 128 | 1.12 GiB | 4.50 GiB |
| Qwen3-Coder-30B-A3B / Qwen3-30B-A3B-2507 | 48 / 4 / 128 | 0.75 GiB | 3.00 GiB |
| Llama-3.3-70B (unsloth mirror config) | 80 / 8 / 128 | 2.50 GiB | 10.00 GiB |
| Qwen2.5-72B | 80 / 8 / 128 | 2.50 GiB | 10.00 GiB |
| gpt-oss-20b | 24 / 8 / 64, alternating sliding(128)/full | ≤0.38 GiB (upper bound; ~half with sliding layers) | ≤1.50 GiB |
| gpt-oss-120b | 36 / 8 / 64, alternating | ≤0.56 GiB | ≤2.25 GiB |

Rough fit (weights + KV + ~1-2 GB runtime overhead; my estimate, not measured): a 4B model at 8k needs ~4-5 GB; 30B-A3B at 32k needs ~23-24 GB; 70B Q4_K_M at 8k needs ~47 GB and at 32k ~55 GB (so 48 GB is tight, 64-96 GB comfortable); gpt-oss-120b needs ~68-70 GB (fits 80-96 GB).

**[Ollama-FAQ] docs.ollama.com/faq.** VERIFIED [web]. "By default, Ollama uses a context window size of 4096 tokens." Override with `OLLAMA_CONTEXT_LENGTH` or `num_ctx`. `OLLAMA_KV_CACHE_TYPE`: `q8_0` "uses approximately 1/2 the memory of `f16` with a very small loss in precision"; `q4_0` "approximately 1/4"; quantized KV requires Flash Attention (`OLLAMA_FLASH_ATTENTION=1`). Gate risk: an 8k diff prompt on default settings is silently truncated to 4096. Set `num_ctx` explicitly.

---

## 5. Determinism for self-hosted judges
- [He2025] batch-size-dependent kernels cause temperature-0 nondeterminism: 80 unique completions out of 1000 (Qwen3-235B). Self-hosting with a fixed batch size or batch-invariant kernels can remove this; shared cloud endpoints cannot. VERIFIED [web].
- [Atil2024], [Ouyang2023]: see rq04-07 notes.

---

## Summary table

| Key | Profile | Evidence | Number | Status | Caveat |
|---|---|---|---|---|---|
| Qwen3-4B-2507-card | a | non-thinking only; LCB v6 35.1; Aider 12.9; IFEval 83.4 | vendor | VERIFIED | self-reported |
| CodeJudgeBench | a/b/c | non-thinking judges ~53-59% (chance 50); Qwen3-8B think 65.6; QwQ-32B 76.4; Gemini-2.5-Pro 82.1 | 26 judges | VERIFIED | competition code |
| RefactorSLM | a | Llama 3.2 3B 30.4-57.9% detection; Mistral 7B 2.9%; Phi-4 14B 71.4% | 100 bugs | VERIFIED | recall only |
| Wei2022-CoT / Luo2025 | a | CoT hurts <10B (2022); ≤3B long-CoT SFT −75% | — | VERIFIED | cohort |
| gpt-oss-card | b | SWE-bench V 62.4 (120b high), 60.7 (20b high); Aider 44.4 / 34.2; 120b fits one 80GB GPU | n=477 | VERIFIED | vendor |
| Qwen3-Coder-Next | b | SWE-bench V ~70.6-71.3 (80B-A3B) vs Opus-4.5 78-79 | 300 turns | VERIFIED | vendor, agentic |
| Qwen3-Coder 30B/480B | b | 69.6 / 51.6 SWE-bench claims | — | UNVERIFIED | conflicting aggregators |
| Aider | b/c | Qwen3-32B 40.0; gpt-oss-120b 41.8; Qwen3-235B 59.6; R1-0528 71.4; gpt-5 high 88.0 | 225 | VERIFIED | editing, not review |
| CRBugBench | c | 71.9% bugs in top-5 (opus-5); −25.5% proprietary | 1,800 | VERIFIED | recall only |
| SWE-PRBench | c | 15-31% human-flagged issues | 350 PRs | VERIFIED | single author |
| Qwen3-8B-card | — | enable_thinking=False hard switch; /no_think soft switch | — | VERIFIED | — |
| Ollama-thinking | — | think: true/false/null; gpt-oss low/medium/high | — | VERIFIED | — |
| Ollama-SO | — | format = JSON schema | — | VERIFIED | — |
| vLLM-SO | — | structured_outputs / response_format json_schema; guided_* removed v0.12.0 | — | VERIFIED | — |
| JSONSchemaBench | — | 10K schemas, 6 frameworks | — | VERIFIED | — |
| Ollama library | — | 4B 2.5 GB; 30B 19 GB; 70B 43 GB; 72B 47 GB; gpt-oss 14/65 GB | — | VERIFIED | — |
| KV calc | — | 4B 1.1/4.5 GiB; 30B-A3B 0.75/3.0; 70B 2.5/10 (8k/32k, f16) | computed | VERIFIED configs | my arithmetic |
| Ollama-FAQ | — | default ctx 4096; KV q8_0 ≈ ½ | — | VERIFIED | silent truncation risk |
| He2025 | — | 80/1000 unique at T=0 | Qwen3-235B | VERIFIED | blog |
