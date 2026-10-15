# Phase 1 — Scoping (2026-10-15)

Source of truth: `../brief.md` (registry issue #15). Inputs read in full: brief, `../plan.md`, both Mac plans
(canonical + 13:36 stray copy), everything under `../related/`, live STATUS of `../../self-hosted-cicd/` (#3) and
`../../home-llm-gateway/` (#7), the facility memory dir.

## 1. Merged research questions (union of canonical + stray; canonical wins on conflict)

| Brief # | Question | Canonical | Stray |
|---|---|---|---|
| RQ1 | Failure taxonomy + base rates (9 named categories) | RQ1 | RQ1 |
| RQ2 | Mode → cheapest reliable check → layer L0–L5 → block/warn/inform | RQ2 | Phase 3 task |
| RQ3 | Deterministic tooling: version, licence, self-hostability, runtime; re-check #3 pins; no Trivy | (Phase 2d) | RQ2 |
| RQ4 | Judge reliability: kappa/alpha + n, P/R, biases, rubric sensitivity, variance; where never to block | RQ3 | RQ3 |
| RQ5 | Prompt structures: what raises recall vs what lowers FPs (separate levers) | RQ4 | RQ4 |
| RQ6 | FP control + blocking threshold (from Tricorder < 10%); tuning data | RQ6 | RQ5 |
| RQ7 | Repair loops, caps, stop rules, test-generation conflict of interest; vs agent-gate's "give up after 3" | RQ7 | RQ6 |
| RQ8 | Provenance/audit: trailers, SLSA, in-toto, sigstore, SBOM; 2026 regulation | — | RQ7 |
| RQ9 | Reference implementations (commercial + OSS self-hostable), licence + activity, cost as fact | — | RQ8 |
| RQ10 | Self-hosting per judge profile (4B/8 GB, 70B/48–96 GB, frontier) | RQ8 | — |
| RQ11 | Limits: what no gate catches; when no-human is irresponsible | RQ9 | RQ9 |
| Q12–Q18 | Build questions (kit plugs into contract; checks fire; llm_review pipeline; stub; Forgejo visibility; real Claude Code L0; corpus measurement) | — | — |

Canonical RQ5 (architecture/time budgets) is answered by RQ2 + Q12 (measured budgets).

## 2. Definitions

- **Gate**: an automated check whose result changes what happens next (agent keeps working, push refused, merge blocked).
- **Block / warn / inform**: block = non-zero exit of a contract task (`check:fast`/`check`/`ci`) or the merge-required
  status; warn = shown in the same place but exit 0; inform = recorded in a report/log only.
- **Finding**: one reported issue (file, line range, category, severity, evidence).
- **Precision** = true findings / all findings, per category. **Recall** = defective change sets caught / defective
  change sets. On the verification corpus these are change-set level (a change set is "caught" if any blocking
  finding of the labelled category, or of any category for a gate that is category-agnostic, fires).
- **Effective false positive** (Tricorder): a finding the developer does not act on. In the corpus: a finding on a
  change set labelled clean, or a finding unrelated to the labelled defect.
- **Escape**: a defect that passed every gate and was found later. **Override**: a gate failure bypassed by a human
  (suppression, `--no-verify`, admin merge).
- **Smoke test**: every measured number in this topic. n is stated beside it. Never a benchmark.

## 3. Evidence bar and source hierarchy

1. Primary sources fetched this session (paper PDF/abstract, official docs, release API) — **VERIFIED** with access date.
2. Prior verified evidence (sweep-02 2026-09-07, sweep-04) — reused after spot re-check; marked "re-checked" or "carried".
3. Peer-reviewed > preprint > vendor report > blog. Vendor numbers are labelled vendor.
4. Every benchmark number carries its critique (contamination, construct validity, sample, model cohort date).
5. Nothing from memory. Unfetchable sources are UNVERIFIED leads and are not used for numbers.

## 4. Environment inventory (read-only; `env-inventory.txt`)

**Important deviation from the brief's assumptions.** This session runs on a 16-core / 31 GB Linux workstation with
an Intel iGPU only: **no NVIDIA GPU, no `nvidia-smi`, no LLM gateway listening on <gateway-host:port>, no
`<gateway-app-dir>`**, and `ollama.service` is active but holds **0 models**. #7's own STATUS (2026-10-15)
records the same: its run "executed on a different machine (no NVIDIA GPU, no app repo, no `homellm` stack)".
Consequences:
- The `local-8gb` judge profile cannot be measured here even with approval: the endpoint does not exist on this
  machine. It stays **NOT RUN** with exact commands for the box. No ollama pull (forbidden) and no second server.
- The `llm_review` HTTP path is exercised against a **local mock OpenAI-compatible server** (stdlib, canned
  responses incl. qwen3-style `<think>` blocks), which proves the protocol/parsing path but says nothing about model
  quality. This is labelled as such everywhere.
- Tools present: python 3.12, git 2.43, docker 29.8 (not used for builds/runs — open question 6), node 24, go,
  claude 2.1.300, gh. Absent: task, gitleaks, osv-scanner, semgrep, actionlint, zizmor, syft, grype, shellcheck,
  hadolint, uv. They are fetched as pinned release binaries (checksum-verified) or into a project-local venv under
  `../tools/` — no global installs.
- One unrelated container is running (not ours, not touched). Listening ports are local-only.

**#3 status** (`../../self-hosted-cicd/STATUS.md`, 2026-10-14): DONE/VERIFIED for the Forgejo stack in disposable KVM
VMs inside a lab container; VMs **stopped**, lab container stopped. Using its ci lane would require starting the lab
container (a live-host change) → the Forgejo-PR row is **NOT RUN** with exact resume commands. #3 also proved that
the `args` exec-form in `settings.json.example` works with Claude Code 2.1.299 (q10 transcript) — reused for Q17.

## 5. Scope boundaries (from brief, binding)

IN: research RQ1–11; prompt library; kit template; brand-new sample repo; ≥ 20 pre-registered change sets;
stub judge; mock-endpoint protocol test; real headless Claude Code L0 run; public repo publish.
OUT / NOT RUN: model pulls, gateway changes, keyward key, GPU-window runs, cloud judge, live Docker builds/runs,
host installs, Forgejo PR (lab stopped), bot-token PR comments, self-repair loop build, `_soul` packaging, company code.

## 6. Output skeleton — the 14 + 3 findings sections (stray plan list, then brief appendix)

1 Executive summary + one diagram · 2 Failure taxonomy with evidence · 3 Mode → check mapping · 4 Layered
architecture on #3's L0–L5 and Taskfile tasks · 5 Deterministic layer · 6 Prompt library (full, copy-pasteable,
schemas, rationale) · 7 Judge reliability and biases · 8 FP control and tuning · 9 Verification/self-repair loops ·
10 Provenance and audit · 11 Measurement · 12 Reference implementations incl. self-hostable · 13 Rollout plan ·
14 Limits · 15 Self-hostable vs frontier per layer · 16 Adversarial pass per check · 17 VERIFIED / NOT VERIFIED /
NOT RUN for RQ1–11 and Q12–Q18 + repo URL + verified commit + live-host changes + teardown.

## 7. Success criteria (checked in Phase 7)

- [ ] every number sourced + dated + critiqued · [ ] prompts one per file + schema + severity ladder + rationale +
recorded critique/revise · [ ] kit per brief shape · [ ] new sample repo, ≥ 20 pre-registered change sets committed
before any gate run · [ ] proof-linux per question · [ ] public repo scanned then pushed · [ ] sources/STATUS/backlog.
