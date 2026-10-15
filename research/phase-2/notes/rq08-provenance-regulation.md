# RQ8: Provenance, audit and regulation for AI-generated code changes

Access date for all sources: 2026-10-15. Status key:
- **VERIFIED**: I fetched the primary page or raw file and the quote matches.
- **VERIFIED (2nd)**: I fetched it, but it is secondary commentary (law firm, press), not the primary instrument.
- **UNVERIFIED**: I only saw it in search snippets or could not fetch the primary text.

About 65 web calls (WebSearch, WebFetch, curl, gh api).

---

## 1. Commit trailers and AI-tool attribution conventions

### 1.1 git interpret-trailers (the mechanism)
- **Source:** git-scm.com, "git-interpret-trailers"
- **URL:** https://git-scm.com/docs/git-interpret-trailers
- **Status:** VERIFIED
- **Quote:** "Add or parse trailer metadata at the end of the otherwise free-form part of a commit message, or any other kind of text."
- **Quote:** "the last two lines starting with `Signed-off-by` are trailers."
- The page shows `trailer.<token>.key`, `.ifexists`, `.ifmissing` and `.cmd` config. That lets a hook add trailers idempotently, for example `trailer.sign.ifexists doNothing`. The page never mentions `Co-authored-by`.
- **Relevance:** Trailers are git's native, parseable key/value channel. Any AI-provenance trailer can be written and read with `git interpret-trailers --parse`.

### 1.2 git notes (out-of-band storage)
- **Source:** git-scm.com, "git-notes"
- **URL:** https://git-scm.com/docs/git-notes
- **Status:** VERIFIED
- **Quote:** "Adds, removes, or reads notes attached to objects, without touching the objects themselves."
- **Relevance:** Notes can carry large provenance records (prompt hashes, gate results) after the commit is made, without changing its SHA. They are not pushed by default and are lost on rebase unless `notes.rewriteRef` is configured.

### 1.3 Claude Code (Anthropic)
- **Source:** Claude Code settings reference, "Git and attribution"
- **URL:** https://code.claude.com/docs/en/settings-reference.md (via https://code.claude.com/docs/en/settings)
- **Status:** VERIFIED
- **Quote:** "Commits get a [git trailer](https://git-scm.com/docs/git-interpret-trailers) such as `Co-Authored-By` by default; pull request descriptions get plain text."
- **Quote:** "**Default**: unset, so Claude Code adds `Co-Authored-By: <name> <noreply@anthropic.com>`. The name is the model in use when the commit is made, such as `Claude Sonnet 5`. When a [subagent](/docs/en/sub-agents) makes the commit, the trailer names the subagent's model."
- **Quote:** "When it can't match the model ID to any Claude model, such as a third-party model served through a custom `ANTHROPIC_BASE_URL`, it writes `Claude Code`."
- **Quote:** `includeCoAuthoredBy` is "Deprecated since v2.0.62, when [`attribution`](#attribution) replaced it."
- `attribution.sessionUrl` controls whether cloud and Remote Control commits carry a claude.ai session link. This session's own system reminder shows such a trailer: `Claude-Session: https://claude.ai/code/session_...`.
- **Relevance:** On by default, it records the model name, but in a Co-Authored-By trailer, which some projects (Mesa, kernel) reserve for humans. It can be overridden with any text, including custom trailers.

### 1.4 Aider
- **Source:** aider.chat, "Git integration"
- **URL:** https://aider.chat/docs/git.html
- **Status:** VERIFIED
- **Quote:** "If aider authored the changes in a commit, they will have “(aider)” appended to the git author and git committer name metadata."
- **Quote:** "You can use `--no-attribute-author` and `--no-attribute-committer` to disable modification of the git author and committer name fields."
- **Quote:** `--attribute-co-authored-by` will "have aider append a Co-authored-by trailer to the end of the commit string." It also "will disable appending `(aider)` to the git author and git committer unless you have explicitly enabled those settings."
- **Quote:** `--attribute-commit-message-author`: "Prefix commit messages with ‘aider: ‘ if aider authored the changes."
- **Relevance:** By default it uses an identity-field suffix rather than a trailer. That survives `git log --format=%an` but is not machine-structured: it carries no model ID.

### 1.5 OpenAI Codex
- **Source:** openai/codex repo, `codex-rs/ext/git-attribution/src/world_state.rs` (fetched via `gh api`)
- **URL:** https://github.com/openai/codex/blob/main/codex-rs/ext/git-attribution/src/world_state.rs
- **Status:** VERIFIED (source code)
- **Quote:** "Commit messages must end with `Co-authored-by: Codex <noreply@openai.com>`. Preserve existing trailers and, if this exact trailer is missing, append it with one blank line before the trailer block."
- `policy.rs` reads a backend setting `commit_attribution_enabled`, so the trailer is policy-gated per account.
- Secondary sources describe a `commit_attribution` key in `config.toml` behind a `codex_git_commit` feature flag (https://codex.danielvaughan.com/2026/03/28/codex-cli-commit-attribution/). **UNVERIFIED**: the config doc was not found in the repo with gh code search.
- **Relevance:** Uses the same Co-authored-by convention as Claude. It names the tool, not the model.

### 1.6 GitHub Copilot coding agent and VS Code
- **Source:** GitHub Changelog, 2026-03-20, "Trace any Copilot coding agent commit to its session logs"
- **URL:** https://github.blog/changelog/2026-03-20-trace-any-copilot-coding-agent-commit-to-its-session-logs
- **Status:** VERIFIED
- **Quote:** commits are "authored by Copilot, with the human who gave Copilot the task marked as the co-author."
- **Quote:** the commit message includes an "`Agent-Logs-Url`" trailer that links to the session logs.
- **Relevance:** This is the most audit-friendly vendor default. It inverts author and co-author (agent = author), and it adds a trailer that dereferences to the full session (prompt and actions). The link points at a vendor-hosted, access-controlled resource.

- **Source:** heise online, "Microsoft forces 'Co-Authored-by Copilot' in commits"
- **URL:** https://heise.de/-11279554
- **Status:** VERIFIED (2nd)
- **Quote:** the trailer text is "Co-authored-by: Copilot copilot@github.com". The setting is `git.addAICoAuthor`. heise tested on "VS Code v1.118", where the default was "chatAndAgent".
- **Relevance:** Shows the backlash to default-on attribution. Search snippets say the default was later reverted to `off` (**UNVERIFIED**).

- **Source:** GitHub community discussion #179983
- **URL:** https://github.com/orgs/community/discussions/179983
- **Status:** UNVERIFIED (snippet)
- **Point:** Squash-merging a Copilot PR makes Copilot the commit author.
- **Relevance:** Squash-merge rewrites or drops per-commit trailers. Provenance has to survive the merge strategy.

### 1.7 Gemini CLI
- **Source:** google-gemini/gemini-cli issue #25721, "CLA prevents adding Gemini as co-author", opened 2026-04-21
- **URL:** https://github.com/google-gemini/gemini-cli/issues/25721
- **Status:** VERIFIED
- **Quote:** "When contributing to projects using Gemini CLI, I like adding a `Co-authored-by` trailer to give credit to Gemini. However, this repo's CLA shows that gemini@google.com hasn't signed the CLA and is blocking my PRs."
- The settings schema (`schemas/settings.schema.json`) has no "co-author", "attribution" or "trailer" key, per a grep on the date of access.
- **Relevance:** Gemini CLI has no built-in attribution default; users add trailers by hand. A Co-authored-by email can also trip CLA bots.

### 1.8 Linux kernel
- **Source:** Documentation/process/coding-assistants.rst (torvalds/linux.git, current tree)
- **URL:** https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/Documentation/process/coding-assistants.rst and https://docs.kernel.org/process/coding-assistants.html
- **Status:** VERIFIED
- **Quote:** "AI agents MUST NOT add Signed-off-by tags. Only humans can legally certify the Developer Certificate of Origin (DCO)."
- **Quote:** "Contributions should include an Assisted-by tag in the following format:: `Assisted-by: LLM [TOOL1] [TOOL2]`"
- **Quote:** "Basic development tools (git, gcc, make, editors) should not be listed."
- **History** (git log of that file): added 2026-01-06 by Sasha Levin (+59 lines). "coding-assistants: simplify attribution" by Christian Brauner on 2026-08-03. Merged for docs-7.3 on 2026-08-20.
- The v7.0 version had a richer format, which is now gone from mainline: `Assisted-by: AGENT_NAME:MODEL_VERSION [TOOL1] [TOOL2]` (VERIFIED from the `?id=v7.0` blob).
- **Relevance:** The most influential trailer convention, `Assisted-by:`. Note that the kernel *dropped* agent and model version from the required format in Aug 2026, so it now records only "an LLM was used", not which one.

- **Source:** Documentation/process/generated-content.rst
- **URL:** https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/Documentation/process/generated-content.rst
- **Status:** VERIFIED
- **Quote:** "These guidelines apply when a meaningful amount of content in a kernel contribution was not written by a person in the Signed-off-by chain, but was instead created by a tool."
- **Quote:** "If in doubt, choose transparency and assume these guidelines apply to your contribution."

- **Source:** Documentation/process/submitting-patches.rst
- **URL:** https://docs.kernel.org/process/submitting-patches.html
- **Status:** VERIFIED
- **Quote:** "every Co-developed-by: must be immediately followed by a Signed-off-by: of the associated co-author."
- **Relevance:** This is why `Co-developed-by` cannot be used for an AI. The RTEMS proposal (below) cites this explicitly.

### 1.9 LLVM
- **Source:** LLVM AI Tool Use Policy
- **URL:** https://llvm.org/docs/AIToolPolicy.html (raw: https://llvm.org/docs/_sources/AIToolPolicy.md.txt)
- **Status:** VERIFIED
- **Quote:** "Contributors must read and review all LLM-generated code or text before they ask other project members to review it."
- **Quote:** "Our policy on labelling is intended to facilitate reviews, and not to track which parts of LLVM are generated."
- **Quote:** "For instance, use a commit message trailer like Assisted-by: <name of code assistant>."
- **Relevance:** Explicitly says the label is a review aid, not a provenance ledger.

### 1.10 Mesa
- **Source:** mesa/docs/submittingpatches.rst (main)
- **URL:** https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/docs/submittingpatches.rst
- **Status:** VERIFIED
- **Quote:** "It is not allowed to use autonomously acting tools to submit any contributions, that is every contributions needs explicit oversight and your review."
- **Quote:** "Disclosure is always required when "AI" was involved in the creative process of coming up with the code"
- **Quote:** "``Assisted-by: TOOL (OPTIONAL: MODEL)`` for when "AI" was involved in making decisions or also generated parts of the code."
- **Quote:** "``Generated-by: TOOL (OPTIONAL: MODEL)`` for when almost all the code was generated through "AI"."
- **Quote:** "Do not use the ``Co-authored-by`` tag as this one is reserved for human co-authors."
- **Relevance:** The only major project with a two-level scheme (Assisted-by vs Generated-by). It directly conflicts with the Claude, Codex and Copilot Co-authored-by defaults. Phoronix (2026-04-06, https://phoronix.com/news/Mesa-Two-Gen-AI-Policies) reports these as the April 2026 GenAI policies (UNVERIFIED, 2nd).

### 1.11 Fedora
- **Source:** Fedora Council AI-Assisted Contributions Policy. Commit 823e93b6 in the forge.fedoraproject.org council/docs repo (2025-10-24) says it was approved by Council vote on 2025-10-22.
- **URL:** https://forge.fedoraproject.org/council/docs/commit/823e93b640dea2205d6df2bc51586552a52898d7 (the rendered page, https://docs.fedoraproject.org/en-US/council/policy/ai-contribution-policy/, returned an Anubis "Access Denied")
- **Status:** VERIFIED (from the commit diff)
- **Quote:** "You *MUST* disclose the use of AI tools when the significant part of the contribution is taken from a tool without changes."
- **Quote:** "For contributions tracked in git, the recommended method is an `Assisted-by:` commit message trailer."
- **Quote:** "`Assisted-by: generic LLM chatbot`", "`Assisted-by: ChatGPTv5`"
- **Quote:** "The final accountability for accepting a contribution, even if implemented by an automated system, always rests with the human contributor who authorizes the action."

### 1.12 QEMU (ban, still in force)
- **Source:** QEMU docs, "Code provenance", Use of AI-generated content (master)
- **URL:** https://www.qemu.org/docs/master/devel/code-provenance.html and https://gitlab.com/qemu-project/qemu/-/raw/master/docs/devel/code-provenance.rst
- **Status:** VERIFIED
- **Quote:** "Current QEMU project policy is to DECLINE any contributions which are believed to include or derive from AI generated content. This includes ChatGPT, Claude, Copilot, Llama and similar tools."
- **Quote:** "This policy does not apply to other uses of AI, such as researching APIs or algorithms, static analysis, or debugging, provided their output is not included in contributions."
- **Status as of 2026-10-15:** The last change to the file is "docs/code-provenance: Fix formatting of *-by tags" (2026-05-22), per the GitLab API.
- Paolo Bonzini's 2026-05-28 patch to relax the ban (AI allowed for mechanical changes, tests, docs and fixes of 20 lines or fewer, plus an "AI-used-for" trailer) is reported by linuxiac and Phoronix (https://linuxiac.com/qemu-may-relax-its-ban-on-ai-generated-contributions/). It is **not merged** in master. The trailer detail is UNVERIFIED (Phoronix returned 403).

### 1.13 Gentoo (ban)
- **Source:** Gentoo Council AI policy, adopted 2024-04-14
- **URL:** https://wiki.gentoo.org/wiki/Project:Council/AI_policy
- **Status:** VERIFIED
- **Quote:** "It is expressly forbidden to contribute to Gentoo any content that has been created with the assistance of Natural Language Processing artificial intelligence tools."

### 1.14 NetBSD (presumed tainted)
- **Source:** NetBSD Commit Guidelines
- **URL:** https://www.netbsd.org/developers/commit-guidelines.html
- **Status:** VERIFIED
- **Quote:** "Code generated by a large language model or similar technology ... is presumed to be tainted code, and must not be committed without prior written approval by core."

### 1.15 Other emerging conventions (not standards)
- **RTEMS proposal #5657 (2026-07)**
  - **URL:** https://lists.rtems.org/pipermail/bugs/2026-July/061763.html
  - **Status:** VERIFIED
  - **Quote:** "Adopt `Assisted-by:` for AI disclosure"
  - **Quote:** example "Assisted-by: Claude:claude-opus-4-8 claude-code"
  - **Quote:** "The kernel considered `Co-developed-by:` and rejected it, because that tag ..."
  - Note: the proposal copies the *older* kernel format, with the model ID.
- **Apache magpie PR #1032**
  - **URL:** https://github.com/apache/magpie/pull/1032
  - **Status:** UNVERIFIED (snippet)
  - **Point:** Uses `Generated-by: <agent> (<model>)`.
- **CheckMarK rai-lint**
  - **URL:** https://github.com/CheckMarKDevTools/rai-lint
  - **Status:** UNVERIFIED (snippet)
  - **Point:** A four-level scheme: Authored-by, Commit-generated-by, Assisted-by and Co-authored-by.
- **Agent Trace** (Cursor-led open spec, v0.1.0, status "RFC", January 2026)
  - **URL:** https://agent-trace.dev/
  - **Status:** VERIFIED
  - **Quote:** "Agent Trace is an open specification for tracking AI-generated code."
  - **Quote:** `model_id` is "The model's unique identifier following models.dev convention (e.g., 'anthropic/claude-opus-4-5-20251101')".
  - **Quote:** "This spec intentionally does not define how traces are stored."
  - **Relevance:** Line-range-level attribution (contributor type human, ai, mixed or unknown, plus a conversation URL). Thoughtworks Radar put it in "Assess" (April 2026, https://www.thoughtworks.com/radar/platforms/agent-trace, UNVERIFIED).
- **Git AI Standard v3.0.0** (git-ai-project)
  - **URL:** https://github.com/git-ai-project/git-ai/blob/main/specs/git_ai_standard_v3.0.0.md
  - **Status:** VERIFIED
  - **Quote:** "Authorship logs MUST be stored under the `refs/notes/ai` namespace"
  - **Quote:** "Implementations MUST NOT use the default `refs/notes/commits` namespace to avoid conflicts with other tools"
  - **Relevance:** A concrete git-notes-based line-level AI authorship log, with schema `authorship/3.0.0`.
- **Verdict on 1:** There is **no ratified standard trailer**. The de facto split:
  - **Assisted-by:** Kernel, LLVM, Fedora, Mesa, RTEMS. Model naming is optional or dropped.
  - **Co-authored-by:** Claude Code, Codex, Copilot/VS Code, Aider opt-in. Conflicts with the "human-only" rule in Mesa and with CLA bots.
  - **Agent-Logs-Url:** Copilot only. The only default that links the prompt and session.
  - **Generated-by:** Mesa (full generation), Apache magpie.
  - **Hard rule everywhere:** No AI Signed-off-by (kernel).

---

## 2. Attestations, signing and supply-chain provenance

### 2.1 SLSA Build provenance (v1.1; site says v1.2 is current)
- **Source:** SLSA spec v1.1, Provenance
- **URL:** https://slsa.dev/spec/v1.1/provenance
- **Status:** VERIFIED
- **Quote:** "It’s the verifiable information about software artifacts describing where, when, and how something was produced."
- **Quote:** predicateType `https://slsa.dev/provenance/v1`
- **Quote:** builder.id is "URI indicating the transitive closure of the trusted build platform."
- **Quote:** resolvedDependencies is "Unordered collection of artifacts needed at build time."

- **Source:** SLSA v1.1, About
- **URL:** https://slsa.dev/spec/v1.1/about
- **Status:** VERIFIED
- **Quote:** "SLSA v1.1 consists of only a single track"
- **Quote:** "SLSA's Build Track protects against tampering during or after the build."
- **Quote:** "SLSA does not tell you whether the developers writing the source code followed secure coding practices."
- **Relevance:** Build provenance attests the *build* (inputs, builder, run). It says nothing about who or what authored the source. An AI-written commit built on a trusted builder gets the same SLSA Build L3 as a human-written one.

### 2.2 SLSA Source track (v1.2)
- **Source:** SLSA v1.2, Source requirements
- **URL:** https://slsa.dev/spec/v1.2/source-requirements
- **Status:** VERIFIED
- **Quote:** "The SCS MUST document how actors are identified for the purposes of attribution."
- **Quote:** L4: "The SCS requires two trusted persons to review all changes to protected branches."
- **Quote:** "SLSA leaves source provenance attestations undefined"
- Source VSA uses `https://slsa.dev/verification_summary/v1`.
- It never mentions AI. It does define "trusted robots": "Automation authorized by the organization to act in explicitly defined contexts."
- **Relevance:** The closest standard hook for an AI agent is to model it as a *trusted robot* actor with its own identity. Two-party review at L4 means the agent cannot be one of the "trusted persons".

### 2.3 in-toto attestation predicates
- **Source:** in-toto/attestation, spec/predicates (vetted list)
- **URL:** https://github.com/in-toto/attestation/tree/main/spec/predicates
- **Status:** VERIFIED
- **Vetted predicates:** CycloneDX, Link, Reference, Release, Runtime Traces, SCAI Report, SLSA Provenance, SLSA Verification Summary, SPDX2, SPDX3, Simple Verification Result, Test Result, VULNS.
- **Test Result**
  - **URL:** https://github.com/in-toto/attestation/blob/main/spec/predicates/test-result.md
  - **Status:** VERIFIED
  - Type `https://in-toto.io/attestation/test-result/v0.1`.
  - **Quote:** "It can be used to verify: 1. that all tests were in fact run, and 2. that all required tests passed"
  - Fields: `result` (PASSED, WARNED or FAILED), `configuration`, `url`, `passedTests`, `warnedTests`, `failedTests`.
  - **Quote:** "The expected `subject` are the source artifacts tested."
  - **Relevance:** A direct fit for "which gates did this commit pass", one attestation per gate run.
- **Vulnerabilities**
  - **URL:** https://github.com/in-toto/attestation/blob/main/spec/predicates/vulns_02.md
  - **Status:** VERIFIED
  - Type `https://in-toto.io/attestation/vulns`, v0.2. Required fields: `scanner.uri`, `scanner.db.lastUpdate` and `scanner.result`.
  - **Quote:** "an empty list means the **scanner** found no vulnerabilities."
- **SCAI**
  - **URL:** https://github.com/in-toto/attestation/blob/main/spec/predicates/scai.md
  - **Status:** VERIFIED
  - Type `https://in-toto.io/attestation/scai`, v0.3.
  - **Quote:** examples of attributes include "code features instrumented by a compiler, or properties tested via static analysis."
  - **Quote:** "this predicate does not dictate the types of attributes that can be attested".
  - **Relevance:** A generic attribute and evidence container. It could carry `GENERATED_BY_MODEL=<id>` as a custom attribute with the prompt hash as evidence, though no standard attribute name exists.
- **DigestSet**
  - **URL:** https://github.com/in-toto/attestation/blob/main/spec/v1/digest_set.md
  - **Status:** VERIFIED
  - Supports `gitCommit`: "The lowercase hex SHA-1 (40 character) or SHA-256 (64 character) of a git commit". The subject of an attestation can therefore be a commit SHA directly.

### 2.4 Sigstore and cosign (keyless vs local key; offline lane)
- **Source:** Sigstore docs, Signing overview
- **URL:** https://docs.sigstore.dev/cosign/signing/overview/
- **Status:** VERIFIED
- **Quote:** "Keyless signing associates identities, rather than keys, with an artifact signature."
- **Quote:** "Fulcio issues short-lived certificates binding an ephemeral key to an OpenID Connect identity."

- **Source:** cosign CLI docs (repo doc/*.md)
- **URL:** https://github.com/sigstore/cosign/blob/main/doc/cosign_attest-blob.md and cosign_verify-blob-attestation.md
- **Status:** VERIFIED
- **Quote:** "cosign attest-blob --predicate <FILE> --type <TYPE> --key cosign.key --bundle <path> <BLOB>"
- **Quote:** `--type` values: "(slsaprovenance|slsaprovenance02|slsaprovenance1|link|spdx|spdxjson|cyclonedx|vuln|openvex|custom) or an URI (default "custom")"
- **Quote** (verify-blob-attestation): "--insecure-ignore-tlog ignore transparency log verification, to be used when an artifact signature has not been uploaded to the transparency log. Artifacts cannot be publicly verified when not included in a log"
- The current `sign-blob` flags no longer list `--tlog-upload`. Instead there is `--signing-config`, and `cosign signing-config create` has `--no-default-rekor` / `--no-default-fulcio`. My inference (not stated on one page): in cosign v3 the offline route is a signing config with no Rekor, plus `--key`.

- **Source:** Fulcio identity config (list of accepted OIDC issuers)
- **URL:** https://github.com/sigstore/fulcio/blob/main/config/identity/config.yaml
- **Status:** VERIFIED
- **Point:** The issuers include token.actions.githubusercontent.com, gitlab.com, oidc.circleci.com, agent.buildkite.com and more. There are **no Forgejo or Codeberg issuers**.

- **Source:** Forgejo docs, "Forgejo Actions | Security OpenID Connect" (v16, latest)
- **URL:** https://forgejo.org/docs/latest/user/actions/security-openid-connect/
- **Status:** VERIFIED
- **Quote:** "Forgejo Actions allows for workflows to request OpenID Connect compatible JWT ID tokens from Forgejo to exchange with external systems for credentials once a trust relationship between the external service and Forgejo is established."
- **Relevance for a self-hosted or offline lane:**
  - Public-good keyless signing needs a Fulcio-trusted OIDC issuer and network access to Fulcio and Rekor.
  - A self-hosted Forgejo issuer is not trusted by public Fulcio.
  - Options: (a) `cosign --key` with a local or KMS/HSM key, with Rekor disabled and `--insecure-ignore-tlog` on verify; or (b) run a private Fulcio and Rekor that trusts the Forgejo issuer. Option (b) is heavy.
  - Recommendation: (a), a local key that only the gate runner holds.

### 2.5 GitHub artifact attestations
- **Source:** GitHub Docs, "Using artifact attestations to establish provenance for builds"
- **URL:** https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds
- **Status:** VERIFIED
- **Quote:** "uses: actions/attest@v4". Permissions are `id-token: write`, `contents: read` and `attestations: write`.
- **Quote:** "gh attestation verify PATH/TO/YOUR/BUILD/ARTIFACT-BINARY -R ORGANIZATION_NAME/REPOSITORY_NAME"
- The docs now use `actions/attest` rather than `actions/attest-build-provenance`.

- **Source:** GitHub Docs, "Artifact attestations" concepts
- **URL:** https://docs.github.com/en/actions/concepts/security/artifact-attestations
- **Status:** VERIFIED
- **Quote:** "artifact attestations are *not* a guarantee that an artifact is secure."
- **Quote:** GitHub's private Sigstore instance "does not have a transparency log and only federates with GitHub Actions."
- **Relevance:** GitHub-only. Not usable from Forgejo.

### 2.6 Commit signing: SSH signing and gitsign
- **Source:** git-config docs, `gpg.format`
- **URL:** https://git-scm.com/docs/git-config
- **Status:** VERIFIED
- **Quote:** "Specifies which key format to use when signing with --gpg-sign. Default is "openpgp". Other possible values are "x509", "ssh"."

- **Source:** sigstore/gitsign README
- **URL:** https://github.com/sigstore/gitsign
- **Status:** VERIFIED
- **Quote:** "Keyless Git signing with Sigstore!"
- **Quote:** "git config --local gpg.format x509  # gitsign expects x509 args"
- The default issuer is `https://oauth2.sigstore.dev/auth` and the default Rekor is `https://rekor.sigstore.dev`. Token providers include `github-actions`, `filesystem`, `spiffe` and `buildkite-agent`.
- **Relevance:** For an offline lane, use SSH signing (`gpg.format=ssh`) with a dedicated *agent* key, so agent commits are cryptographically distinguishable from human commits. gitsign needs reachable OIDC, Fulcio and Rekor services.

---

## 3. SBOMs: can they say "this code was generated by model X"?

### 3.1 SPDX 3.0.1 AI profile
- **Source:** SPDX 3.0.1, AI/Classes/AIPackage
- **URL:** https://spdx.github.io/spdx-spec/v3.0.1/model/AI/Classes/AIPackage/
- **Status:** VERIFIED
- **Quote:** "Metadata information that can be added to a package to describe an AI application or trained AI model."
- Properties include autonomyType, typeOfModel, informationAboutTraining, safetyRiskAssessment, and others. None is about generated output.

- **Source:** SPDX 3.0.1, Core RelationshipType
- **URL:** https://spdx.github.io/spdx-spec/v3.0.1/model/Core/Vocabularies/RelationshipType/
- **Status:** VERIFIED
- **Quote:** "generates: The `from` Element generates each `to` Element."
- **Quote:** "usesTool: The `from` Element uses each `to` Element as a tool, during a LifecycleScopeType period."
- **Quote:** "invokedBy: The `from` Element was invoked by the `to` Agent, ..."
- **Relevance:** You *can* express `AIPackage(model) --generates--> File(src/x.py)` with the general `generates` relationship. There is no dedicated "AI-generated" relationship or property, and no tooling emits it.

### 3.2 CycloneDX ML-BOM
- **Source:** CycloneDX ML-BOM capability page
- **URL:** https://cyclonedx.org/capabilities/mlbom/
- **Status:** VERIFIED
- **Quote:** "Model and dataset transparency for security, privacy, safety and ethical considerations."
- It does not mention model *outputs*.

- **Source:** CycloneDX 1.6 JSON schema (bom-1.6.schema.json)
- **URL:** https://github.com/CycloneDX/specification/blob/master/schema/bom-1.6.schema.json
- **Status:** VERIFIED
- **Quote** (formulation): "Describes how a component or service was manufactured or deployed. This is achieved through the use of formulas, workflows, tasks, and steps..."
- **Quote** (authors): "Components created through automated means may have `@.manufacturer` instead."
- **Relevance:** You could model the agent run as a `formulation` workflow whose task used a `machine-learning-model` component. This is possible but non-standard. Neither SBOM format has a first-class "generated-by-model" field for source files.
- **Verdict on 3:** SBOMs describe *components* and *models*, not authorship of lines in first-party code. Use a trailer or note plus an in-toto attestation instead.

---

## 4. Regulation and standards, 2026

### 4.1 EU AI Act (Regulation (EU) 2024/1689)
- **Source:** Article 3 definitions
- **URL:** https://artificialintelligenceact.eu/article/3/
- **Status:** VERIFIED (2nd, an unofficial consolidated reproduction)
- **Quote:** provider: "a natural or legal person, public authority, agency or other body that develops an AI system or a general-purpose AI model ..."
- **Quote:** deployer: "... using an AI system under its authority except where the AI system is used in the course of a personal non-professional activity"
- **Relevance:** Obligations attach to providers and deployers of *AI systems*, not to the artefacts (code) those systems emit.

- **Source:** Article 50 (transparency)
- **URL:** https://artificialintelligenceact.eu/article/50/
- **Status:** VERIFIED (2nd)
- **Quote:** 50(2): providers of AI systems "generating synthetic audio, image, video or text content" must ensure outputs are "marked in a machine-readable format and detectable as artificially generated or manipulated."
- **Quote:** the exemption covers where "the AI systems perform an assistive function for standard editing".
- Applies from 2 August 2026.

- **Source:** European Commission FAQ, "Transparency obligations under Article 50 of the AI Act" (summarising the Commission *Guidelines on Transparency of AI-Generated Content*)
- **URL:** https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act
- **Status:** **VERIFIED (primary, Commission)**
- **Quote:** "The Guidelines on Transparency of AI-Generated Content clarify that certain outputs fall outside the scope of the obligations, such as: a short sequence of numbers, symbols or letters, source code outputs of an AI system intended to be exclusively communicated from machine-to-machine and processed automatically without any exposure to humans, or outputs that are only used in closed loop industrial and product development environments..."
- **Relevance:** **Source code is explicitly outside Article 50(2) marking.** Even where it applied, the duty falls on the *provider of the generator* (Anthropic, OpenAI, ...), not on the repo owner. Secondary commentary says the final guidelines define source code broadly, including comments, IaC, YAML/JSON config and SQL. Those sources are C(2026) 5054 final of 2026-07-20 per regulation-ai.eu, and Bird & Bird; the latter returned 402. **UNVERIFIED** at paragraph level.

- **Source:** Commission news, "Commission publishes Code of Practice on marking and labelling AI-generated content", 10 June 2026
- **URL:** https://digital-strategy.ec.europa.eu/en/news/commission-publishes-code-practice-marking-and-labelling-ai-generated-content
- **Status:** VERIFIED
- **Point:** Voluntary. The labelling duty covers deepfakes and "AI-generated or AI-manipulated text published on matters of public interest". It does not cover code.

- **Source:** Article 53 (GPAI providers; applies from 2 Aug 2025)
- **URL:** https://artificialintelligenceact.eu/article/53/
- **Status:** VERIFIED (2nd)
- **Quote:** "Providers of general-purpose AI models shall: (a) draw up and keep up-to-date the technical documentation of the model, including its training and testing process ..."
- **Relevance:** Model-provider duties only. Nothing for users of the model's code output.

- **Source:** Article 113 (dates)
- **URL:** https://artificialintelligenceact.eu/article/113/
- **Status:** VERIFIED (2nd)
- **Quote:** "Chapters I and II shall apply from 2 February 2025", "... shall apply from 2 August 2025", "It shall apply from 2 August 2026."

- **Source:** Digital Omnibus on AI, Regulation (EU) 2026/1744
- **URL:** https://eur-lex.europa.eu/eli/reg/2026/1744/oj/eng (EUR-Lex returned an empty body to curl, so the primary text was **not fetched**). Secondary sources: Jones Walker (https://www.joneswalker.com/en/insights/blogs/ai-law-blog/yes-august-2-still-matters-the-eu-approved-a-high-risk-ai-delay-but-most-trans.html) and Orrick (https://www.orrick.com/en/Insights/2026/07/EU-AI-Act-Update-Digital-Omnibus-Finalizes-8-Compliance-Changes).
- **Status:** VERIFIED (2nd)
- **Quote** (Orrick): Annex III high-risk obligations "will now take effect on 2 December 2027 instead of 2 August 2026". Annex I / Art 6(1) systems "will follow a later date: 2 August 2028".
- **Quote** (Orrick): providers of systems placed on the market before 2 Aug 2026 "will have until 2 December 2026 to comply with the Article 50(2) transparency obligations."
- Search results say it was published in the OJ on 24 July 2026 and entered into force on 27 July 2026 (UNVERIFIED, with one conflicting 31 July date).
- **Relevance:** The high-risk delay does not change anything for code provenance. Article 50 still starts 2 Aug 2026 but excludes code.

### 4.2 EU Cyber Resilience Act (Regulation (EU) 2024/2847)
- **Source:** CRA Article 71 (unofficial reproduction; EUR-Lex blocked)
- **URL:** https://www.european-cyber-resilience-act.com/Cyber_Resilience_Act_Article_71.html
- **Status:** VERIFIED (2nd)
- **Quote:** "This Regulation shall apply from 11 December 2027."
- **Quote:** "However, Article 14 shall apply from 11 September 2026 and Chapter IV (Articles 35 to 51) shall apply from 11 June 2026."

- **Source:** CRA Annex I, Part II(1)
- **URL:** https://www.european-cyber-resilience-act.com/Cyber_Resilience_Act_Annex_1.html
- **Status:** VERIFIED (2nd)
- **Quote:** "identify and document vulnerabilities and components contained in the product, including by drawing up a software bill of materials in a commonly used and machine-readable format covering at the very least the top-level dependencies of the product;"
- The annex does not mention AI.

- **Source:** CRA Article 12, "High-risk AI systems"
- **URL:** https://www.european-cyber-resilience-act.com/Cyber_Resilience_Act_Article_12.html
- **Status:** VERIFIED (2nd)
- **Quote:** products "classified as high-risk AI systems pursuant to Article 6 of that Regulation shall be deemed to comply with the cybersecurity requirements set out in Article 15 of that Regulation where: ..."
- **Relevance:** This concerns products that *are* AI systems. Nothing distinguishes AI-*written* code.
- Sonar's commentary (vendor; https://www.sonarsource.com/resources/library/cyber-resilience-act-compliance-for-ai-generated-code/, UNVERIFIED snippet) says the CRA sets no different requirements by code origin. The manufacturer is responsible either way.

### 4.3 US
- **NIST SP 800-218A**
  - **Source:** NIST SP 800-218A (July 2024), SSDF Community Profile for Generative AI and Dual-Use Foundation Models
  - **URL:** https://csrc.nist.gov/pubs/sp/800/218/a/final
  - **Status:** VERIFIED
  - **Quote:** it adds practices "that are specific to AI model development throughout the software development life cycle." It is "intended to be useful to the producers of AI models, the producers of AI systems that use those models, and the acquirers of those AI systems."
  - **Relevance:** About building models, not about code written *by* models. Its parent EO 14110 was revoked in January 2025 (my knowledge, not re-fetched).
- **SSDF 1.2 draft**
  - **Source:** NIST SP 800-218 Rev. 1 ipd (SSDF v1.2), draft dated 12/17/2025. Per the CSRC publications page (updated 2026-10-06) it is still a draft; v1.1 (2022-02-03) is the final version.
  - **URLs:** https://csrc.nist.gov/Projects/ssdf/publications, https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218r1.ipd.pdf
  - **Status:** VERIFIED (I downloaded the PDF and grepped it)
  - **Quote** (PS.3.2): "Collect, safeguard, maintain, and share provenance data for all components of each software release (e.g., in a software bill of materials [SBOM])."
  - **Quote** (footnote): provenance "may also include personnel and processes used to interact with or make modifications to the system, component, or associated data" [SP80053].
  - A grep for "artificial intelligence", "\bAI\b", "machine learning" and "large language" found **no hits**.
  - **Relevance:** SSDF's provenance definition is broad enough to *include* "processes used ... to make modifications", which could cover an AI agent. It does not require that, and it never mentions AI.
- **OMB M-26-05**
  - **Source:** Mayer Brown, "OMB Rescinds Biden-Era Software Security Memoranda" (Feb 2026)
  - **URL:** https://www.mayerbrown.com/en/insights/publications/2026/02/omb-rescinds-biden-era-software-security-memoranda
  - **Status:** VERIFIED (2nd)
  - **Quote:** "January 23, 2026, the Office of Management and Budget issued" M-26-05, "formally rescinding two Biden Administration memoranda" (M-22-18 and M-23-16).
  - **Quote:** agencies may require producers to "provide a current software bill of materials (SBOM) upon request". The attestation form remains available but agencies "are no longer required to use them."
  - **Relevance:** The US federal self-attestation mandate is gone as of Jan 2026.
- **EO 14306** (2025-06-06) amends EO 14144 and EO 13694. It removed the FAR attestation directive and ordered the SSDF update. Sources: https://www.clarkhill.com/news-events/news/how-does-executive-order-14306-shift-the-cyber-strategy-for-government-contractors and https://csrc.nist.gov/Topics/Laws-and-Regulations/executive-documents/Executive-Order-14306. Status UNVERIFIED (snippets).
- **CISA Secure by Design:** I found no 2026 CISA document on AI-generated code. CIS and SAFECode "Secure by Design v1.1" (July 2026) adds AI considerations (https://www.cisecurity.org/about-us/media/press-release/cis-and-safecode-release-secure-by-design-v1-1-a-guide-to-assessing-software-security-practices). Status UNVERIFIED (snippet).
- **FDA**
  - **Source:** FDA, "Cybersecurity in Medical Devices: Quality Management System Considerations and Content of Premarket Submissions", issued February 3, 2026 (supersedes the June 27, 2025 version)
  - **URL:** https://www.fda.gov/media/119933/download
  - **Status:** VERIFIED (PDF downloaded)
  - **Quote:** "Contains Nonbinding Recommendations"
  - **Quote:** objectives "may apply broadly to devices within the scope of this guidance, including, but not limited to, devices containing artificial intelligence (AI) and cloud-based services."
  - **Quote:** "The SBOM should be in a machine-readable format."
  - No text on AI-*generated* code.

### 4.4 Sector rules
- **DORA RTS on ICT risk management** (Delegated Regulation (EU) 2024/1774), Article 16
  - **URL:** https://www.springlex.eu/en/packages/dora/rts-rmf-regulation/article-16/
  - **Status:** VERIFIED (2nd reproduction of the OJ text)
  - **Quote:** "The procedure referred to in paragraph 2 shall contain the performance of source code reviews covering both static and dynamic testing."
  - **Quote:** the RTS requires "the implementation of controls to protect the integrity of the source code of ICT systems".
  - No AI mention.
  - **Relevance:** Applies to AI-written code like any code. Review and integrity controls are mandatory for EU financial entities, but origin labelling is not.
- **PCI DSS v4.0.1**, req. 6.2.3, 6.2.3.1 and 6.2.4
  - **URL:** https://www.myctrl.tools/frameworks/pci-dss-v4/6-2-3
  - **Status:** UNVERIFIED (snippets; PCI SSC docs need a login)
  - **Point:** Bespoke and custom software is reviewed before release. Manual reviews need someone other than the author. I found no PCI SSC text on AI-generated code.
  - **Relevance:** "Reviewer other than the code author" becomes interesting when the author is an agent and the human prompter reviews. An auditor may argue the prompter is the author.

### 4.5 Voluntary frameworks
- **ISO/IEC 42001:2023** (AI management system)
  - **URLs:** https://webstore.iec.ch/publication/90574, https://connect.snv.ch/isoiec-42001-2023-2
  - **Status:** UNVERIFIED (iso.org returned 403; snippets only)
  - **Point:** It "specifies the requirements and provides guidance for establishing, implementing, maintaining and continually improving an AI management system" for organisations that provide or use AI. Certification is voluntary.
  - **Relevance:** An organisation that *uses* AI coding agents could scope them into an AIMS, which pushes toward logs and records, but nothing code-specific.
- **NIST AI RMF**
  - **URL:** https://www.nist.gov/itl/ai-risk-management-framework
  - **Status:** VERIFIED
  - **Quote:** "The NIST AI Risk Management Framework (AI RMF) is intended for voluntary use". The Generative AI Profile (NIST AI 600-1) was released July 26, 2024.

### 4.6 Plain verdict
- **Nothing in force on 2026-10-15 legally *requires* recording which AI model or prompt produced a code change.**
  - EU AI Act Article 50(2) is the only rule that marks AI output. It binds the *provider of the generator*, and the Commission's guidelines **expressly exclude source code**.
  - The CRA, DORA, FDA guidance, PCI DSS and the SSDF are all **origin-neutral**. They require review, testing, integrity controls, vulnerability handling and SBOMs (CRA: top-level dependencies, from Dec 2027) for *all* code, however it was produced.
  - US federal attestation (M-22-18) was rescinded in Jan 2026.
- **What effectively compels it is contractual and community policy, not law:**
  - Upstream projects: the kernel `Assisted-by`, no AI Signed-off-by; Fedora's MUST disclose; Mesa's required disclosure with Assisted-by or Generated-by; LLVM; bans at QEMU, Gentoo and NetBSD.
  - CLAs and DCOs (only humans can certify).
  - Customer contracts, ISO 42001 or SOC 2 scope.
- **Indirect legal pressure to keep provenance anyway:**
  - The CRA (11 Sep 2026 reporting, Dec 2027 full) and DORA require you to find and fix vulnerabilities and protect source integrity. Knowing which changes came from an unreviewed agent lane is useful evidence for root-cause analysis and incident reports, so it is good practice, not a mandate.
  - Copyright uncertainty is the reason QEMU, Gentoo and NetBSD ban AI code. A provenance record is what lets you find and remove such code later.

---

## (a) Recommended minimal provenance record for an agent-made commit

Design notes:
- Use trailers that match the community majority (`Assisted-by`), not only the vendor default (`Co-authored-by`, which Mesa reserves for humans and which trips CLA bots).
- Put the heavy, mutable data (gate results) in an in-toto attestation keyed by `gitCommit` digest and stored in `refs/notes/` or as an artefact. It should not live in the commit message, because gates run *after* the commit exists.
- Never add Signed-off-by for the agent.

**Commit trailers** (written by the agent harness, parseable with `git interpret-trailers --parse`):

```
Assisted-by: claude-code:claude-opus-5-5 ruff semgrep        # kernel v7.0 / RTEMS form: AGENT:MODEL [TOOLS]
Generated-by: claude-code (claude-opus-5-5)                  # optional, Mesa form, only when ~all code is AI
AI-Session: https://forge.example/agent-runs/2026-10-15T12-03Z-7f3a   # cf. Copilot Agent-Logs-Url
AI-Prompt-SHA256: 9c1e...ab                                  # hash of the task prompt + system/instructions bundle
AI-Gates: pending                                            # flipped by verifying an attestation, not by editing the commit
Signed-off-by: Human Reviewer <human@example.org>            # human only, added at review/merge
```

(Optional, for tool compatibility: also keep `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` if repo policy allows it. Do not use it in Mesa-style repos.)

Sign the commit with a dedicated agent SSH key (`gpg.format=ssh`). That makes agent commits cryptographically separable from human ones. SLSA Source treats it as a "trusted robot" identity.

**Gate attestation**: an in-toto Statement, signed offline with `cosign attest-blob --key agent-gate.key --type https://in-toto.io/attestation/test-result/v0.1`, with Rekor disabled and verification using `--insecure-ignore-tlog`. Stored at `refs/notes/ai-gates` or as a CI artefact:

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [{ "name": "git+https://forge.example/org/repo", "digest": { "gitCommit": "<40-hex sha>" } }],
  "predicateType": "https://in-toto.io/attestation/test-result/v0.1",
  "predicate": {
    "result": "PASSED",
    "configuration": [{ "name": "gates.yaml", "digest": { "sha256": "<hash of gate config>" } }],
    "url": "https://forge.example/org/repo/actions/runs/1234",
    "passedTests": ["lint:ruff", "types:mypy", "unit:pytest", "sast:semgrep", "secrets:gitleaks", "diff-size<=400"],
    "warnedTests": [],
    "failedTests": []
  }
}
```

**Generation record**: a companion custom predicate, e.g. `https://example.org/attestation/ai-generation/v0.1`, or SCAI attributes. Same subject. Field names are aligned with Agent Trace and the Git AI standard where possible:

```json
{
  "agent": { "name": "claude-code", "version": "2.x.y" },
  "model": { "id": "anthropic/claude-opus-5-5", "provider": "anthropic", "params": { "temperature": null } },
  "prompt": { "sha256": "<task prompt hash>", "instructions_sha256": "<CLAUDE.md/AGENTS.md bundle hash>", "stored_at": "<private URI or null>" },
  "session": { "id": "<run id>", "url": "<log URL>", "started": "2026-10-15T12:03:00Z", "ended": "2026-10-15T12:19:41Z" },
  "human": { "requester": "<id>", "reviewer": "<id or null until review>" },
  "contribution": { "level": "generated|assisted", "files": [{ "path": "src/x.py", "ranges": [[10, 58]], "contributor": "ai" }] },
  "base_commit": "<parent sha>"
}
```

The minimum mandatory subset: `agent.name`, `model.id`, `prompt.sha256`, `session.id`, `human.requester`, `base_commit`, plus the test-result gate attestation. Everything else is optional.

---

## (b) Regulation table

| Instrument | Applies to AI-generated code as such? | Date | Verbatim basis |
|---|---|---|---|
| EU AI Act Art. 50(2) marking of synthetic content | **No.** Source code is excluded, and the duty sits on the generator's provider anyway. | Applies 2 Aug 2026; legacy systems until 2 Dec 2026 (Omnibus) | Commission FAQ: "certain outputs fall outside the scope of the obligations, such as: ... source code" |
| EU AI Act Art. 50 Code of Practice (marking/labelling) | No (voluntary; covers deepfakes and public-interest text) | Published 10 Jun 2026 | "AI-generated or AI-manipulated text published on matters of public interest" |
| EU AI Act Art. 53 GPAI obligations | No (on model providers only) | 2 Aug 2025 | "Providers of general-purpose AI models shall: (a) draw up ... technical documentation of the model" |
| EU AI Act high-risk (Annex III / Annex I) as amended by Digital Omnibus Reg. (EU) 2026/1744 | No (on AI systems, not code they emit) | 2 Dec 2027 / 2 Aug 2028 | Orrick: "will now take effect on 2 December 2027 instead of 2 August 2026" |
| EU Cyber Resilience Act 2024/2847 | No, origin-neutral. All product code is covered, so AI code is covered like any code. | Art. 14 reporting 11 Sep 2026; full 11 Dec 2027 | Annex I Part II(1): "drawing up a software bill of materials ... covering at the very least the top-level dependencies"; no AI mention |
| DORA RTS 2024/1774 Art. 16 (EU finance) | No, origin-neutral (mandatory code review and integrity) | In force since 17 Jan 2025 | "source code reviews covering both static and dynamic testing"; "controls to protect the integrity of the source code" |
| NIST SSDF SP 800-218 v1.1 / v1.2 draft | No (voluntary; provenance = components, may include "processes") | v1.1 2022; v1.2 still draft (ipd 17 Dec 2025) | PS.3.2 "Collect, safeguard, maintain, and share provenance data for all components of each software release" |
| NIST SP 800-218A (GenAI profile) | No (about developing AI models) | Jul 2024 | "specific to AI model development throughout the software development life cycle" |
| OMB M-22-18 / M-23-16 self-attestation | N/A, rescinded | Rescinded by M-26-05, 23 Jan 2026 | "formally rescinding two Biden Administration memoranda" |
| FDA premarket cybersecurity guidance | No (nonbinding; SBOM, mentions devices *containing* AI) | 3 Feb 2026 | "Contains Nonbinding Recommendations"; "The SBOM should be in a machine-readable format." |
| PCI DSS v4.0.1 6.2.3 / 6.2.3.1 | No, origin-neutral (review of bespoke code; reviewer ≠ author for manual review) | Future-dated reqs mandatory since 31 Mar 2025 | (UNVERIFIED snippets) review "bespoke and custom software ... prior to being released" |
| ISO/IEC 42001:2023 | No (voluntary AIMS; could scope AI-assisted dev) | Dec 2023 | (UNVERIFIED) "requirements ... for establishing, implementing, maintaining and continually improving an AI management system" |
| NIST AI RMF 1.0 / AI 600-1 | No (voluntary) | Jan 2023 / Jul 2024 | "intended for voluntary use" |
| Linux kernel coding-assistants.rst | **Yes (project rule)**, Assisted-by; no AI Signed-off-by | Added Jan 2026; simplified Aug 2026 (7.3) | "AI agents MUST NOT add Signed-off-by tags"; "Assisted-by: LLM [TOOL1] [TOOL2]" |
| Fedora AI-Assisted Contributions Policy | **Yes (project rule)**, MUST disclose significant unchanged AI output | Approved 22 Oct 2025 | "You *MUST* disclose the use of AI tools when the significant part of the contribution is taken from a tool without changes." |
| Mesa submittingpatches | **Yes (project rule)**, disclosure required; no autonomous submission | 2026 | "Disclosure is always required when "AI" was involved in the creative process" |
| QEMU / Gentoo / NetBSD | **Yes: ban** (NetBSD: needs core approval) | QEMU 2025 (still in force Oct 2026); Gentoo Apr 2024; NetBSD 2024 | QEMU: "DECLINE any contributions which are believed to include or derive from AI generated content" |

**Bottom line:**
- Recording AI provenance for code is **legally required by nothing** in the EU or US as of Oct 2026.
- It is **required by several upstream open-source projects**, banned outright by a few, and is **strongly advisable** as cheap evidence for the origin-neutral review, integrity and vulnerability duties in the CRA and DORA.
