# RQ3 deterministic tooling + RQ9 reference implementations + Forgejo Q16 (discovery notes)

Access date for every source below: **2026-10-15**. Versions, dates, licences and activity were pulled from APIs on that date:
- GitHub: `gh api repos/<o>/<r>`, `.../releases/latest`, `.../license` (read-only, public data)
- PyPI: `https://pypi.org/pypi/<pkg>/json` · npm: `https://registry.npmjs.org/<pkg>` · crates.io: `https://crates.io/api/v1/crates/<name>` · Go: `https://proxy.golang.org/<module>/@latest`
- Codeberg/Forgejo: `https://codeberg.org/api/v1/...`, `https://code.forgejo.org/api/v1/...`

"Activity" = last push to default branch (GitHub `pushed_at`) unless stated. Licence is the SPDX id from the GitHub licence API. Where GitHub returned `NOASSERTION`, the LICENSE file was read and the result is noted.

---

## Part A: RQ3 deterministic tooling

### A1. Pins in the self-hosted-cicd template

The template file is not in this repo (`grep` over `research/` found no pins), so the pins come from the brief.

| Tool | Pin in template | Latest (date) | Pin current? | Licence | Runtime | Activity | Source |
|---|---|---|---|---|---|---|---|
| gitleaks | v8.30.1 | v8.30.1 (2026-03-21) | **yes** | MIT | Go binary | push 2026-09-30 | https://github.com/gitleaks/gitleaks/releases |
| osv-scanner | unpinned | v2.7.0 (2026-10-12) | n/a: pin to v2.7.0 | Apache-2.0 | Go binary | 2026-10-14 | https://github.com/google/osv-scanner/releases |
| semgrep (CE) | "latest CE" | 1.181.0 (2026-10-14, GitHub + PyPI) | n/a: pin to 1.181.0 | LGPL-2.1 (engine); rules have their own licence, see A5 | Python wrapper + OCaml core binary | 2026-10-15 | https://github.com/semgrep/semgrep/releases, https://pypi.org/project/semgrep/ |
| actionlint | v1.7.12 | v1.7.12 (2026-03-30) | **yes** | MIT | Go binary | 2026-07-16 | https://github.com/rhysd/actionlint/releases |
| zizmor | v1.30.1 | **v1.31.0 (2026-10-15)** | **no, one minor behind** (released on the access date) | MIT | Rust binary (also on PyPI) | 2026-10-15 | https://github.com/zizmorcore/zizmor/releases |
| syft | (version not supplied) | v1.54.1 (2026-10-06) | check against the template | Apache-2.0 | Go binary | 2026-10-12 | https://github.com/anchore/syft/releases |
| grype | (version not supplied) | v0.120.1 (2026-10-06) | check against the template | Apache-2.0 | Go binary | 2026-10-13 | https://github.com/anchore/grype/releases |
| go-task (task) | (version not supplied) | v3.54.0 (2026-10-01) | check against the template | MIT | Go binary | 2026-10-15 | https://github.com/go-task/task/releases |
| pre-commit-hooks | v6.0.0 | v6.0.0 (2025-08-09) | **yes** | MIT | Python | 2026-10-12 | https://github.com/pre-commit/pre-commit-hooks/releases |
| prek | (version not supplied) | v0.5.5 (2026-10-05; PyPI first upload 2025-08-08) | check | MIT | Rust binary (PyPI wheel) | 2026-10-14 | https://github.com/j178/prek/releases |
| (pre-commit itself) | n/a | 4.7.0 (2026-10-12) | n/a | MIT | Python | n/a | https://pypi.org/project/pre-commit/ |

**Trivy is excluded.** Source for the compromise: GHSA-69fq-xp46-6x23, "Trivy ecosystem supply chain was briefly compromised", published 2026-03-21 on the repo and 2026-03-24 in the global DB. It is CVE-2026-33634 (https://github.com/advisories/GHSA-69fq-xp46-6x23). Wiz's write-up (https://wiz.io/blog/trivy-compromised-teampcp-supply-chain-attack) reports that the actor TeamPCP did four things on 2026-03-19:
- published a malicious trivy v0.69.4;
- force-pushed 76 of 77 `trivy-action` tags and all 7 `setup-trivy` tags to credential-stealing commits;
- pushed malicious Docker Hub images 0.69.5 and 0.69.6;
- dumped Runner.Worker memory and exfiltrated credentials.

Wiz also reports that the CVE is on CISA KEV and that the attack followed incomplete credential rotation after an earlier Feb/Mar incident. Trivy is still actively released (v0.76.0, 2026-10-14). Per the brief, these notes do **not** recommend it. Lesson for the template: pin actions by full commit SHA, not tag. zizmor/actionlint enforce this.

### A2. Type checkers / linters

| Tool | Latest (date) | Licence | Self-host | Runtime | Activity | Source |
|---|---|---|---|---|---|---|
| ruff | 0.17.0 (2026-10-09) | MIT | yes | Rust binary (PyPI wheel) | 2026-10-15 | github.com/astral-sh/ruff, pypi ruff |
| mypy | 2.4.0 (PyPI 2026-10-01; tag v2.4.0, no GH release object) | MIT (PyPI; GH API says NOASSERTION because of the multi-part LICENSE) | yes | Python (mypyc-compiled) | 2026-10-14 | pypi.org/project/mypy |
| pyright | 1.1.414 (2026-09-09 npm / GH; PyPI wrapper 2026-09-10) | MIT (LICENSE.txt read) | yes | Node | 2026-10-15 | github.com/microsoft/pyright |
| basedpyright | v1.40.2 (2026-10-04) | MIT (LICENSE.txt, a pyright fork) | yes | Node (bundled in PyPI wheel) | 2026-10-04 | github.com/DetachHead/basedpyright |
| eslint | v10.12.0 (2026-10-02) | MIT | yes | Node | 2026-10-14 | github.com/eslint/eslint |
| TypeScript (tsc) | 7.0.2 (npm 2026-07-08; GH release 2026-08-20) | Apache-2.0 | yes | **TS 7 is the native Go port** (repo language now Go) | 2026-10-15 | registry.npmjs.org/typescript |
| golangci-lint | v2.14.0 (2026-09-24) | **GPL-3.0** (tool only; it does not infect linted code) | yes | Go binary | 2026-10-14 | github.com/golangci/golangci-lint |
| staticcheck (go-tools) | 2026.2.2 (2026-10-12; module honnef.co/go/tools v0.8.2) | MIT | yes | Go binary | 2026-10-12 | github.com/dominikh/go-tools |
| biome | 2.5.15 (2026-09-30) | MIT OR Apache-2.0 (npm); GH reports Apache-2.0 | yes | Rust binary (npm) | 2026-10-15 | github.com/biomejs/biome |

### A3. Mutation testing, including diff-scoped support

| Tool | Latest (date) | Licence | Runtime | Activity | Diff / incremental support (cited) |
|---|---|---|---|---|---|
| mutmut | 3.8.0 (2026-09-12) | BSD-3-Clause | Python (POSIX only; Windows via WSL) | 2026-09-12 | **Incremental, not diff-scoped.** It "only re-tests mutants in functions whose source changed" between runs (state is kept in `mutants/`). Git change detection exists only for non-Python files (`use_git_change_detection`). Scoping is by glob (`mutmut run "mod.func*"`) or `only_mutate`. There is **no `--since`/git-diff option**: build the glob from `git diff --name-only`. https://mutmut.readthedocs.io/en/latest/ |
| cosmic-ray | 8.7.0 (2026-08-09) | MIT | Python | 2026-08-09 | **Yes, via filter.** `cr-filter-git` "looks for edited or new lines from the given git branch" and skips other mutations (`[cosmic-ray.filters.git-filter]`). docs/source/how-tos/filters.rst in github.com/sixty-north/cosmic-ray |
| StrykerJS | 10.0.0 (2026-08-14) | Apache-2.0 | Node | 2026-10-10 | **Incremental (`--incremental`, `incrementalFile` default `reports/stryker-incremental.json`, `--force`).** It diffs against the previous incremental report, **not** against a git ref. There is no `--since`. Changes to deps/env are not detected. Scoping by `--mutate file:lines` is possible. https://stryker-mutator.io/docs/stryker-js/incremental/ |
| Stryker.NET | 5.0.0 (2026-09-11) | Apache-2.0 | .NET | 2026-10-14 | **Yes, `--since:<committish>`** (default target `master`; `since.ignore-changes-in`). There is also `--with-baseline:<committish>` (experimental) with Disk/Dashboard/Azure/S3 baseline providers. The two are mutually exclusive. https://stryker-mutator.io/docs/stryker-net/configuration/ |
| PIT (pitest) | 1.30.1 (2026-10-14) | Apache-2.0 | JVM | 2026-10-14 | **Partial in OSS, full in commercial.** OSS has `withHistory` / `historyInputFile` / `historyOutputFile` for incremental runs (https://pitest.org/quickstart/maven/). There is a Maven `scmMutationCoverage` goal that uses the POM `<scm>` to pick changed files (secondary source: https://blog.frankel.ch/faster-mutation-testing/). **arcmutate** (commercial, licence file required) adds `+GIT(from[master])` and, by default, mutates "only lines that have been modified" (https://docs.arcmutate.com/docs/git-integration.html). |
| cargo-mutants | 27.1.0 (2026-06-02; crates.io) | MIT | Rust | 2026-10-13 | **Yes, `--in-diff DIFF_FILE`** tests "only mutants that overlap with regions changed in the diff". The intended CI use is to diff the PR against its base branch. The docs warn it is "not a substitute for a full test run". https://mutants.rs/in-diff.html |
| gremlins (Go) | v0.6.0 (GH release 2025-12-06; proxy.golang.org @latest still v0.5.1, 2024-05-14) | Apache-2.0 | Go binary | 2026-06-26 | **Yes, `--diff/-D <git ref>`**, e.g. `gremlins unleash --diff "origin/$GITHUB_BASE_REF"` (needs `fetch-depth: 0`). It is 0.x and only the current minor is maintained. docs/docs/usage/commands/unleash/index.md in github.com/go-gremlins/gremlins |
| ooze (Go) | tag v0.3.1 (commit 2023-05-04; no GH release) | MIT | Go library (runs as a go test) | push 2026-10-13 (deps only) | No diff support documented (README) |
| go-mutesting (avito fork) | v2.3.1 (2025-12-26) | MIT | Go binary | 2026-10-02 | No diff mode documented (README) |

### A4. Property-based testing

| Tool | Latest (date) | Licence | Runtime | Activity | Source |
|---|---|---|---|---|---|
| Hypothesis | 6.169.3 (2026-10-15) | MPL-2.0 (LICENSE.txt) | Python | 2026-10-15 | pypi hypothesis |
| fast-check | 4.10.2 (2026-09-19) | MIT | Node | 2026-10-14 | npm fast-check |
| proptest | 1.12.0 (crates.io 2026-10-10; GH "latest release" object is a stale 0.9.6 from 2020, so use crates.io) | MIT OR Apache-2.0 | Rust | 2026-10-10 | crates.io/api/v1/crates/proptest |
| rapid (Go) | v1.3.0 (GH 2026-04-30; proxy time 2026-03-30) | MPL-2.0 | Go library | 2026-09-04 | github.com/flyingmutant/rapid, pgregory.net/rapid |

### A5. SAST

| Tool | Latest (date) | Licence | Self-host | Runtime | Activity | Notes |
|---|---|---|---|---|---|---|
| Semgrep CE engine | 1.181.0 (2026-10-14) | LGPL-2.1 (PyPI: LGPL-2.1-or-later) | yes | Python + OCaml | 2026-10-15 | https://docs.semgrep.dev/licensing |
| Semgrep Registry rules (semgrep/semgrep-rules) | rolling | **Semgrep Rules License v1.0** (updated 2024-12-13) | n/a | n/a | 2026-10-14 | Grants a non-exclusive, non-transferable licence to use rules "only for your own internal business purposes". **Forbids** distributing the rules or "mak[ing] them available to others as a service". Modified copies must carry notices. The patent licence ends on a patent claim. Licensing page: both Community and Pro rules are under it, and it bars vendors from using them in competing products/SaaS. Third-party registry rules keep their own licence (e.g. Trail of Bits = AGPL-3.0). **Implication:** internal CI gating on our own repos is fine. Shipping a product or service that bundles Semgrep rules is not. https://semgrep.dev/legal/rules-license |
| Opengrep | v1.30.2 (2026-10-07) | LGPL-2.1 | yes | OCaml binary (cosign-signed) | 2026-10-15 | Fork of Semgrep v1.100.0, "created when Semgrep moved critical features behind a commercial licence". Adds intrafile cross-function taint (`--taint-intrafile`), SARIF with fingerprints, and extra languages. Backed by Aikido, Endor Labs, Orca, Kodem, Amplify. Semgrep rule syntax works unchanged, but **the Semgrep Registry rules licence still applies to those rules**. `opengrep/opengrep-rules` is archived (2025-11-28). https://github.com/opengrep/opengrep |
| CodeQL CLI | v2.27.2 (2026-10-07) | **GitHub CodeQL Terms and Conditions** (proprietary; not OSI) | partial (CLI runs anywhere, but the licence restricts it) | Native + JVM bundle | 2026-10-07 | The terms allow analysis of OSI-licensed codebases and academic research. Automated/CI analysis is allowed only for OSS hosted on GitHub.com. Use on "any codebase that is not an Open Source Codebase (e.g., code in a private repo)" is **not** authorised unless under a paid GitHub Advanced Security licence (now sold as **GitHub Code Security, $30/active committer/month, standalone since 2025-04-01**). **So CodeQL is not usable on a private, self-hosted Forgejo repo without a paid licence.** Queries repo github/codeql is MIT. Sources: https://github.com/github/codeql-cli-binaries/blob/main/LICENSE.md, https://github.blog/changelog/2025-03-04-introducing-github-secret-protection-and-github-code-security/ |
| bandit | 1.9.4 (2026-02-25) | Apache-2.0 | yes | Python | 2026-10-12 | pypi bandit |
| gosec | v2.29.0 (2026-08-26; proxy 2026-08-25) | Apache-2.0 | yes | Go binary | 2026-10-12 | github.com/securego/gosec |

### A6. SCA / SBOM / secrets

| Tool | Latest (date) | Licence | Self-host | Runtime | Activity | Notes |
|---|---|---|---|---|---|---|
| osv-scanner | v2.7.0 (2026-10-12) | Apache-2.0 | yes (offline DB mode) | Go | 2026-10-14 | n/a |
| grype | v0.120.1 (2026-10-06) | Apache-2.0 | yes | Go | 2026-10-13 | n/a |
| syft | v1.54.1 (2026-10-06) | Apache-2.0 | yes | Go | 2026-10-12 | n/a |
| OWASP dependency-check | v13.0.0 (2026-08-03) | Apache-2.0 | yes | JVM | 2026-10-14 | Repo moved to **dependency-check/DependencyCheck**. The old jeremylong/DependencyCheck repo is archived. NVD API key recommended. |
| gitleaks | v8.30.1 (2026-03-21) | MIT | yes | Go | 2026-09-30 | n/a |
| trufflehog | v3.99.2 (2026-10-08) | **AGPL-3.0** (confirmed) | yes | Go | 2026-10-14 | AGPL matters only if modified and offered over a network. Running it as a CI tool is fine. |
| detect-secrets | v1.5.0 (**2024-05-06**) | Apache-2.0 | yes | Python | 2026-04-02 | Stale releases: no release in about 2.5 years |

### A7. Dependency existence and package age (slopsquatting defence)

All of the following were checked live on the access date. Non-existent names return **HTTP 404** on PyPI JSON, npm registry, proxy.golang.org `@v/list` and crates.io.

| Ecosystem | Existence check | Age / "first published" | Doc |
|---|---|---|---|
| PyPI | `GET https://pypi.org/pypi/<p>/json` → 404 if absent | min `upload_time_iso_8601` across `releases[*][*]`. **Note:** the `releases` key is deprecated ("projects should shift to using the Index API"), so the long-term option is the PEP 691 JSON Simple API (`/simple/<p>/`, `Accept: application/vnd.pypi.simple.v1+json`) with per-file `upload-time` | https://docs.pypi.org/api/json/ |
| npm | `GET https://registry.npmjs.org/<p>` → 404 | `time.created` (packument `time` = {created, modified, <ver>: ts}). The abbreviated doc (`Accept: application/vnd.npm.install-v1+json`) omits `time` | https://github.com/npm/registry/blob/main/docs/REGISTRY-API.md |
| Go | `GET https://proxy.golang.org/<module>/@v/list` → 404/410 | `@v/<ver>.info` → `{"Version","Time"}` (e.g. gosec v2.29.0 Time 2026-08-25). The earliest version's `.info` gives the first-seen time. `@latest` also works | https://go.dev/ref/mod#goproxy-protocol |
| crates.io | `GET https://crates.io/api/v1/crates/<name>` → 404 | `crate.created_at`, `versions[].created_at`. A descriptive User-Agent is required by crates.io policy | https://crates.io/data-access |
| multi | deps.dev v3: `GET https://api.deps.dev/v3/systems/{GO,NPM,CARGO,MAVEN,PYPI,NUGET,RUBYGEMS}/packages/<name>` | `versions[].publishedAt` | https://docs.deps.dev/api/v3/ (no key, Google API ToS, caching explicitly allowed) |

Existing tools:

| Tool | Latest (date) | Licence | Self-host / cost | What it does |
|---|---|---|---|---|
| slopcheck (PyPI) | 0.6.1 (2026-04-02; first upload 2026-03-21) | MIT | CLI, free | Hallucinated-package detector for PyPI/npm/crates/Go/RubyGems/Maven/Packagist. Flags non-existence, age < 7 days, < 100 downloads, LLM-style names, and typosquat distance. **Very new, single maintainer (0xToxSec): verify before depending on it.** https://pypi.org/project/slopcheck/ |
| Aikido Safe Chain | 1.5.25 (2026-10-09) | **AGPL-3.0-or-later + commercial dual licence** (LICENSE read; GH says NOASSERTION) | free, tokenless, local proxy, but **calls the Aikido Intel cloud** | Wraps npm/yarn/pnpm/bun/pip/uv/poetry/pipx/pdm. Blocks known malware. **Default minimum package age is 48 h.** https://github.com/AikidoSec/safe-chain |
| Socket Firewall Free (`sfw`) | npm sfw 2.0.6 (2026-05-22) | MIT (npm metadata) | free CLI, no API key, **calls the Socket API** | Blocks confirmed malware for npm/yarn/pnpm/pip/uv/cargo. Public registries only. Enterprise tier adds Go/Java/Ruby/.NET and private registries. https://docs.socket.dev/docs/socket-firewall-free. Socket.dev platform is commercial. |
| Datadog GuardDog | v3.2.0 (2026-08-12) | Apache-2.0 | fully self-hosted (heuristics + Semgrep/YARA rules) | Scans PyPI/npm/Go/GitHub Actions packages for malicious indicators |
| OpenSSF malicious-packages | rolling data (no releases) | Apache-2.0 (repo) | data is public | OSV-format reports of malicious packages, ingested into osv.dev, so **osv-scanner surfaces them** as `MAL-` advisories. https://github.com/ossf/malicious-packages |
| Phylum | n/a | n/a | n/a | Assets acquired by **Veracode on 2025-01-06** and folded into Veracode SCA (commercial). https://www.veracode.com/press-release/veracode-acquires-phylum-inc-technology-to-transform-software-supply-chain-security/ |

**Recommendation for a self-hosted gate** (deterministic, no third-party cloud):
1. Registry existence check via the APIs above (404 → hard fail).
2. Package age threshold (e.g. first publish < 7 days or newest version < 48 h → advisory or fail).
3. osv-scanner, which includes OpenSSF MAL data.
4. Optionally GuardDog.

Safe Chain and sfw are good developer-side guards, but both phone home.

### A8. Licence compliance

| Tool | Latest (date) | Licence | Self-host | Runtime | Activity | Notes |
|---|---|---|---|---|---|---|
| ScanCode toolkit | v32.5.0 (2026-01-15) | Apache-2.0 (code) AND CC-BY-4.0 (licence DB data) | yes | Python | 2026-10-13 | The best licence-*text* detector, including partial licence-text matches. It does **not** do OSS code-snippet provenance by itself. That is the AboutCode MatchCode/PurlDB / ScanCode.io stack (not verified in this pass). |
| licensee | v10.1.0 (2026-08-07) | MIT | yes | Ruby | 2026-10-12 | Project-level LICENSE identification (used by GitHub) |
| pip-licenses | 5.5.5 (2026-03-28) | MIT | yes | Python | 2026-10-15 | n/a |
| license-checker-rseidelsohn | 5.0.1 (2026-05-27) | BSD-3-Clause | yes | Node | 2026-10-08 | n/a |
| go-licenses | v2.0.1 (2025-09-08; module /v2) | Apache-2.0 | yes | Go | 2026-07-09 | n/a |
| REUSE tool | 6.2.0 (2025-10-27) | GPL-3.0-or-later for code (PyPI classifiers; data/docs CC0/CC-BY-SA; GH API has no licence) | yes | Python | 2026-10-13 | Enforces SPDX headers |
| FOSSology | 4.7.2 (2026-09-22) | GPL-2.0 | yes (server) | PHP/C server | 2026-10-13 | Heavy. Clearing workflow tool. |
| SCANOSS (snippet detection) | engine v5.4.27 (2026-07-09), scanoss.py 1.54.2 (2026-07-21) | engine **GPL-2.0**, clients MIT | **partial**: the engine is OSS, but it needs a knowledge base. The free `osskb.org` API is best-effort and rate-limited. A self-hosted KB / high-precision snippet matching is commercial. | C engine / Python CLI | engine 2026-10-13 | The only realistic OSS **snippet-level** detector. Sending code to osskb.org means code leaves the network (it sends fingerprints, i.e. winnowing hashes, not source, per SCANOSS docs, not verified). https://scanoss.readthedocs.io/projects/scanoss-py/en/latest/ |

### A9. Coverage, Dockerfile, shell

| Tool | Latest (date) | Licence | Runtime | Activity | Notes |
|---|---|---|---|---|---|
| coverage.py | 7.16.2 (2026-09-27) | Apache-2.0 | Python | 2026-10-14 | Repo is now coveragepy/coveragepy |
| diff-cover | 10.6.0 (2026-09-22) | Apache-2.0 | Python | 2026-10-01 | Compares Cobertura/Clover/JaCoCo XML or LCov against `git diff` (default `origin/main`, `--compare-branch`, `...` notation). `--fail-under=N` gives a non-zero exit. `diff-quality --violations=ruff.check|flake8|pylint|...` covers lint on changed lines only. https://github.com/Bachmann1234/diff_cover |
| c8 | 12.0.0 (2026-07-14) | ISC | Node (V8 coverage) | 2026-10-13 | n/a |
| nyc / istanbul | 18.0.0 (2026-02-22) | ISC | Node | 2026-05-17 | n/a |
| hadolint | v2.15.1 (2026-07-31) | GPL-3.0 | Haskell static binary | 2026-10-14 | n/a |
| shellcheck | v0.11.0 (2025-08-04) | GPL-3.0 | Haskell static binary | 2026-10-14 | n/a |

---

## Part B: RQ9 reference implementations

Price is stated as a fact from the vendor page on the access date. No sign-ups were made.

**Benchmarks:** none is clearly independent.
- **Martian Code Review Bench** (released late Feb 2026, https://codereview.withmartian.com/) has an offline track (50 curated PRs scored against human "golden comments", F1/F2) and an online track (whether developers act on comments in real PRs). Martian is the most-cited neutral party. Rankings swing by date and track, and most write-ups are by participating vendors (Kilo, Greptile, Qodo), so treat those as **vendor-reported**.
- **GitHub ran its own benchmark** where Copilot came first (The New Stack headline: "Copilot tops GitHub's own AI code review benchmark. An independent one tells a different story"). That is **vendor-run**.
- **Entelligence's 2026 benchmark** ranks Entelligence first. It is **vendor-run**.
- **Academic: arXiv 2606.15689** (Apr 2026), "Bigger Isn't Always Better":
  - Claude Haiku 4.5 F1 0.365 vs Sonnet 4.6 0.343.
  - Real PRs: best F1 **0.066**, vs 0.847 on synthetic mutation-injected bugs.
  - F1 falls from 0.657 (diffs < 10 lines) to 0.043 (> 150 lines).
  - Near-zero recall on performance bugs.

  **This is strong evidence for small diffs and deterministic gates first.**

| Product | What it does well / badly (sourced) | Licence | Self-host with own model | Price (fact) | Last activity | Source |
|---|---|---|---|---|---|---|
| CodeRabbit | Strong recall on Martian at launch (vendor-relayed figures conflict). Line-by-line PR comments, learnings, pre-merge checks. The original OSS `coderabbitai/ai-pr-reviewer` repo now returns 404. | Proprietary | **Enterprise only** ("self-hosting" listed); BYO model not stated | Free for public repos. Essentials $24/seat/mo annual ($30 monthly). Team $48 ($60). Advanced $72. Enterprise custom. | SaaS | https://www.coderabbit.ai/pricing |
| Greptile | Builds a repo graph. Usually highest precision but lower recall in third-party tables. Self-reported 82% catch rate is well above its independent leaderboard scores. | Proprietary (VS Code ext repo archived) | Enterprise "self-host in your own infrastructure"; BYO LLM not stated | Starter free (1 dev, 50 credits). Pro $30/seat/mo (50 credits/seat, $1 extra). Enterprise custom. | SaaS | https://www.greptile.com/pricing |
| Codacy | Deterministic analysers plus AI Reviewer with **merge gates**. IDE "AI Guardrails". **No on-prem git support** (GitHub/GitLab/Bitbucket Cloud only). | Proprietary | **No** | Developer (IDE) free. Team $18/dev/mo yearly ($21 monthly), ≤30 devs. Business quote. Free for OSS. | SaaS | https://www.codacy.com/pricing |
| SonarQube Server (AI Code Assurance / AI CodeFix) | AI Code Assurance applies a stricter quality gate to projects flagged as containing AI code (Developer, Enterprise, Data Center editions). AI CodeFix proposes LLM fixes (Enterprise and Data Center only). | Server editions are commercial; Community Build is LGPL-3.0 (github SonarSource/sonarqube 26.10.0.133078, 2026-10-12) | **Yes**: SonarQube is self-hosted. AI CodeFix "supports a self-hosted LLM, including your own model through Azure OpenAI", but the server still needs internet for prompts/rule descriptions. | Edition pricing not captured | 2026-10-14 | https://docs.sonarsource.com/sonarqube-server/2026.1/ai-capabilities/ai-codefix.md |
| Semgrep Assistant ("Multimodal") | AI triage, fix guidance, autofix PRs, and noise filtering that suppresses PR comments it judges false positive. Vendor claim: ">95% accurate" FP categorisation (no methodology). | Proprietary (AppSec Platform) | **No**: OpenAI primary with Bedrock fallback; BYO key not documented | Requires a Semgrep AppSec Platform plan | SaaS | https://docs.semgrep.dev/semgrep-assistant/overview |
| GitHub Copilot code review | Agentic full-repo context. Reads `.github/copilot-instructions.md`, `*.instructions.md`, `AGENTS.md`. Docs: "can miss problems and make mistakes". Reviews don't count toward required approvals by default; Copilot approvals are in preview. Skips dependency/log/SVG files. | Proprietary | **No** (GitHub.com; GHES not listed) | Copilot Pro/Pro+/Max/Business/Enterprise. Per review roughly $0.05–$1 (Lite) or $0.25–$5 (Balanced) in AI credits, plus Actions minutes. GitHub Code Quality is separate: $10/committer/mo (GA 2026-07-20). | SaaS | https://docs.github.com/en/copilot/concepts/agents/code-review |
| Qodo (ex-Qodo Merge, now "Qodo 2.0") | Led the Martian offline board in one snapshot (vendor-relayed). | Proprietary | Enterprise only (on-prem/air-gapped, BYOK) | Pro Team $30 listed, credits $0.012. No permanent free tier; 14-day trial; free OSS programme. | SaaS | https://www.qodo.ai/pricing/ |
| **PR-Agent** (open source) | `/review`, `/improve`, `/describe`, `/ask`, each a single LLM call, so cheap and predictable. Supports GitHub, GitLab, Bitbucket, Azure DevOps and **Gitea** (Forgejo not named, but the APIs are largely compatible: verify). Any model via LiteLLM, including **Ollama**. **Donated by Qodo to the community.** The repo moved to `The-PR-Agent/pr-agent` and is headed for a foundation. | **MIT** | **Yes** (CLI, Docker `pragent/pr-agent`, Actions, webhook) | Free | v0.47.0 (2026-10-02), push 2026-10-14 | https://github.com/The-PR-Agent/pr-agent |
| Diffblue Cover | Generates Java/Kotlin unit tests autonomously. Not a reviewer. Vendor messaging is "agentic"; the reinforcement-learning basis was not confirmed in this pass. | Proprietary (cover-github-action MIT, v2026.08.01) | Runs locally (IntelliJ plugin / CLI). Some tiers need a continuous online licence check. | Community free (100 MUTs/mo on pricing page; docs say 25, which conflicts). Developer about $30/mo. Teams/Enterprise quote. | action 2026-08-17 | https://www.diffblue.com/pricing/ |
| Amazon CodeGuru Reviewer | **Maintenance mode since 2025-11-07**: no new repository associations, no new features. **CodeGuru Security ended 2025-11-20.** AWS points to Amazon Q Developer and Inspector Code Security. **Do not adopt.** | Proprietary | No | n/a | Deprecated | https://docs.aws.amazon.com/codeguru/latest/reviewer-ug/codeguru-reviewer-availability-change.md |
| reviewdog | Not an LLM. Turns any linter output (errorformat/RDJSON/SARIF) into PR review comments, checks, or filtered diff-only output. Has Gitea support. An ideal "reporter" layer for deterministic gates. | MIT | Yes (Go binary) | Free | v0.21.2 (2026-09-18), 2026-10-15 | https://github.com/reviewdog/reviewdog |
| **Kodus** | OSS self-hosted AI review with "Kody Rules". BYO LLM (OpenAI, Anthropic, Gemini, Vertex, any OpenAI-compatible endpoint, including self-hosted). **Explicitly supports Forgejo** and self-managed GitLab. Docker on 2 CPU / 8 GB / 60 GB. Anonymous telemetry heartbeat (opt out with `KODUS_TELEMETRY_DISABLED=true`). | **AGPL-3.0 + commercial EE** (`.ee.` files) | **Yes** | Community free. Teams $10/dev/mo plus tokens. Enterprise custom. | web-1.2.7 (2026-10-06), 2026-10-15 | https://github.com/kodustech/kodus-ai |
| villesau/ai-codereviewer | Simple GitHub Action calling OpenAI on the diff | MIT | Partly (OpenAI only) | Free | **Stale**: v2.7.0 2023-12-02, last push 2024-08-19 | github.com/villesau/ai-codereviewer |
| anc95/ChatGPT-CodeReview | GitHub App/Action calling OpenAI-compatible APIs | ISC | Yes (any OpenAI-compatible base URL) | Free | v1.0.24 (2026-07-14) | github.com/anc95/ChatGPT-CodeReview |
| shippie (ex code-review-gpt, mattzcarey) | CLI/Action reviewer, multi-provider | MIT | Yes | Free | v0.21.2 (2026-06-23), push 2026-09-28 | github.com/mattzcarey/shippie |
| Sweep | **Pivoted to a JetBrains AI assistant.** The PR-bot repo is effectively dormant. | **Sweep EE licence** (production/commercial use needs a subscription) | No (in practice) | n/a | last push 2025-09-18 | github.com/sweepai/sweep |
| OpenHands PR review | SDK-based GitHub Actions workflow: full diff, `/codereview` and `/github-pr-review` skills, inline comments with priority labels. Docs disagree on trigger (`pull_request_target` vs `pull_request`), and a third-party audit flags prompt-injection risk from untrusted PR content. | MIT (OpenHands v1.27.1, 2026-10-12) | Yes (any LLM key) | Free (plus LLM cost) | 2026-10-15 | https://docs.openhands.dev/sdk/guides/github-workflows/pr-review |
| anthropics/claude-code-action | General `@claude` / automation action. Can do PR review. Runs on your own runner. Auth via Anthropic API, Bedrock, Vertex or Microsoft Foundry. **GitHub-only per docs.** | MIT | Partial (your runner, but Claude models only) | Free action, plus API cost | v1.0.250 (2026-10-14) | https://github.com/anthropics/claude-code-action |

---

## Part C: Forgejo specifics (Q16)

Versions on the access date:
- **Forgejo stable v16.0.6** (2026-10-12). v15.0.10 LTS is also current.
- **Forgejo v17.0 is scheduled for 2026-10-15**, the access date. It was not yet tagged when checked: the latest Codeberg release was v16.0.6, and the v17 blog post was still a WIP PR (forgejo/website#1141).
- **Forgejo Runner v13.2.0** (2026-09-18).

Sources: https://forgejo.org/docs/next/admin/release-schedule/, codeberg API releases, code.forgejo.org runner releases.

| Question | Answer | Source |
|---|---|---|
| Job summaries (`GITHUB_STEP_SUMMARY`) | **Not in v16 and earlier** (v16 docs don't mention it). **Added in Forgejo v17.0** (PR forgejo/forgejo#14076, "Upload and persist TaskStepSummaries and display them in the ActionView", merged 2026-09-07, milestone v17.0.0). Needs **Forgejo Runner ≥ 13.2** (runner PR #1707 "Upload Job summary"). Steps write Markdown to `$FORGEJO_STEP_SUMMARY`; "`$GITHUB_STEP_SUMMARY` is supported, too". It renders above the job log with Mermaid and KaTeX, up to 1 MiB per step, truncated beyond that. | https://forgejo.org/docs/v17.0/user/actions/advanced-features/ ; https://codeberg.org/forgejo/forgejo/pulls/14076 ; draft blog https://codeberg.org/forgejo/website/pulls/1141 ; runner v13.2.0 notes |
| upload-artifact | Upstream `actions/upload-artifact@v4+` fails on Forgejo (GHES check, "GHESNotSupportedError"). Docs v16/v17: "you must use v3 or patched v4". Use **`https://code.forgejo.org/forgejo/upload-artifact@v4`** (tags v4 from 2024-03-21, and **v5** from 2025-12-29) and the matching download-artifact fork. Artifacts can be downloaded from the run page in the web UI and expire after 90 days by default. Upstream is at v7.0.2 (2026-10-07), so don't use it on Forgejo. | https://forgejo.org/docs/v16.0/user/actions/advanced-features/ ; https://code.forgejo.org/forgejo/runner/issues/144 |
| `continue-on-error` | **Step-level works**: "the step won't cause the job to fail". **Job-level is ignored** ("Certain subkeys on the job key ... are ignored, like `permissions`, and `continue-on-error`"). | https://forgejo.org/docs/latest/user/actions/reference/ ; https://forgejo.org/docs/latest/user/actions/github-actions/ |
| `permissions:` | **Ignored.** The automatic token is read-only for fork PRs and has write for `pull_request_target`. OIDC uses `enable-openid-connect:` instead of `permissions: id-token: write`. | same two pages |
| `::set-output` | **Removed in Runner v13** (PR 1631, along with `set-env` and `add-path`). Workflows that still use it print a warning, and the output is not set. Use `echo "k=v" >> "$FORGEJO_OUTPUT"` (`GITHUB_*` aliases exist). `ACTIONS_ALLOW_UNSECURE_COMMANDS` cannot restore them. v13 also hard-fails invalid matrices and failed expression interpolation, and needs Docker ≥ 25. | https://code.forgejo.org/forgejo/runner/releases/tag/v13.0.0 ; https://forgejo.org/2026-08-runner-release-v13/ |
| SARIF / code scanning | **No code-scanning UI or SARIF ingestion** in Forgejo: not in the docs, and no Codeberg issue was found by search. A user write-up lists "No centralized security findings dashboard" as missing on Codeberg. SARIF can only be kept as an artifact or rendered by your own step (e.g. reviewdog `-f=sarif` → PR comments, which needs a token, or → job summary). | https://itiquette.codeberg.page/posts/codeberg-missing-features/ (secondary) |
| `::error` / `::warning` annotations | Not documented for Forgejo, so don't rely on them. | Forgejo reference (absence) |
| **GitHub:** SARIF upload | `github/codeql-action/upload-sarif` (latest bundle v2.27.2, 2026-10-07) needs `security-events: write` (plus `actions: read` on private repos). **On private repos, GitHub Code Security / GHAS must be enabled** (error: "GitHub Code Security or GitHub Advanced Security must be enabled for this repository to use code scanning"). | https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/uploading-a-sarif-file-to-github |
| **GitHub:** step summary | `$GITHUB_STEP_SUMMARY` per step, 1 MiB max per step (an oversized upload fails with an annotation but doesn't change job status), up to 20 step summaries shown per job, on the run summary page. Secrets are masked. | https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#adding-a-job-summary |

---

## Summary table 1: tools

| Tool | Latest | Date | Licence | Self-host | Runtime |
|---|---|---|---|---|---|
| gitleaks | v8.30.1 | 2026-03-21 | MIT | yes | Go |
| osv-scanner | v2.7.0 | 2026-10-12 | Apache-2.0 | yes | Go |
| semgrep CE | 1.181.0 | 2026-10-14 | LGPL-2.1 (rules: Semgrep Rules License v1.0) | yes | Python+OCaml |
| opengrep | v1.30.2 | 2026-10-07 | LGPL-2.1 | yes | OCaml |
| actionlint | v1.7.12 | 2026-03-30 | MIT | yes | Go |
| zizmor | v1.31.0 | 2026-10-15 | MIT | yes | Rust |
| syft | v1.54.1 | 2026-10-06 | Apache-2.0 | yes | Go |
| grype | v0.120.1 | 2026-10-06 | Apache-2.0 | yes | Go |
| task | v3.54.0 | 2026-10-01 | MIT | yes | Go |
| pre-commit-hooks | v6.0.0 | 2025-08-09 | MIT | yes | Python |
| prek | v0.5.5 | 2026-10-05 | MIT | yes | Rust |
| ruff | 0.17.0 | 2026-10-09 | MIT | yes | Rust |
| mypy | 2.4.0 | 2026-10-01 | MIT | yes | Python |
| pyright | 1.1.414 | 2026-09-09 | MIT | yes | Node |
| basedpyright | 1.40.2 | 2026-10-04 | MIT | yes | Node |
| eslint | 10.12.0 | 2026-10-02 | MIT | yes | Node |
| typescript | 7.0.2 | 2026-07-08 | Apache-2.0 | yes | Go-native (npm) |
| golangci-lint | v2.14.0 | 2026-09-24 | GPL-3.0 | yes | Go |
| staticcheck | 2026.2.2 | 2026-10-12 | MIT | yes | Go |
| biome | 2.5.15 | 2026-09-30 | MIT OR Apache-2.0 | yes | Rust |
| mutmut | 3.8.0 | 2026-09-12 | BSD-3-Clause | yes | Python |
| cosmic-ray | 8.7.0 | 2026-08-09 | MIT | yes | Python |
| StrykerJS | 10.0.0 | 2026-08-14 | Apache-2.0 | yes | Node |
| Stryker.NET | 5.0.0 | 2026-09-11 | Apache-2.0 | yes | .NET |
| PIT | 1.30.1 | 2026-10-14 | Apache-2.0 | yes | JVM |
| cargo-mutants | 27.1.0 | 2026-06-02 | MIT | yes | Rust |
| gremlins | v0.6.0 | 2025-12-06 | Apache-2.0 | yes | Go |
| go-mutesting | v2.3.1 | 2025-12-26 | MIT | yes | Go |
| ooze | v0.3.1 (tag) | 2023-05-04 | MIT | yes | Go |
| Hypothesis | 6.169.3 | 2026-10-15 | MPL-2.0 | yes | Python |
| fast-check | 4.10.2 | 2026-09-19 | MIT | yes | Node |
| proptest | 1.12.0 | 2026-10-10 | MIT OR Apache-2.0 | yes | Rust |
| rapid | v1.3.0 | 2026-04-30 | MPL-2.0 | yes | Go |
| CodeQL CLI | v2.27.2 | 2026-10-07 | GitHub CodeQL Terms (proprietary) | partial (licence bars private repos without GHAS/Code Security) | native/JVM |
| bandit | 1.9.4 | 2026-02-25 | Apache-2.0 | yes | Python |
| gosec | v2.29.0 | 2026-08-26 | Apache-2.0 | yes | Go |
| OWASP dependency-check | v13.0.0 | 2026-08-03 | Apache-2.0 | yes | JVM |
| trufflehog | v3.99.2 | 2026-10-08 | AGPL-3.0 | yes | Go |
| detect-secrets | v1.5.0 | 2024-05-06 | Apache-2.0 | yes | Python |
| GuardDog | v3.2.0 | 2026-08-12 | Apache-2.0 | yes | Python |
| slopcheck | 0.6.1 | 2026-04-02 | MIT | yes | Python |
| Aikido Safe Chain | 1.5.25 | 2026-10-09 | AGPL-3.0-or-later / commercial | partial (cloud intel) | Node |
| Socket sfw | 2.0.6 | 2026-05-22 | MIT (CLI) | partial (cloud API) | Node |
| ScanCode toolkit | 32.5.0 | 2026-01-15 | Apache-2.0 + CC-BY-4.0 | yes | Python |
| SCANOSS engine / py | 5.4.27 / 1.54.2 | 2026-07-09 / 2026-07-21 | GPL-2.0 / MIT | partial (KB) | C / Python |
| licensee | v10.1.0 | 2026-08-07 | MIT | yes | Ruby |
| pip-licenses | 5.5.5 | 2026-03-28 | MIT | yes | Python |
| license-checker-rseidelsohn | 5.0.1 | 2026-05-27 | BSD-3-Clause | yes | Node |
| go-licenses | v2.0.1 | 2025-09-08 | Apache-2.0 | yes | Go |
| REUSE | 6.2.0 | 2025-10-27 | GPL-3.0-or-later (code) | yes | Python |
| FOSSology | 4.7.2 | 2026-09-22 | GPL-2.0 | yes | PHP/C server |
| coverage.py | 7.16.2 | 2026-09-27 | Apache-2.0 | yes | Python |
| diff-cover | 10.6.0 | 2026-09-22 | Apache-2.0 | yes | Python |
| c8 | 12.0.0 | 2026-07-14 | ISC | yes | Node |
| nyc | 18.0.0 | 2026-02-22 | ISC | yes | Node |
| hadolint | v2.15.1 | 2026-07-31 | GPL-3.0 | yes | Haskell bin |
| shellcheck | v0.11.0 | 2025-08-04 | GPL-3.0 | yes | Haskell bin |
| reviewdog | v0.21.2 | 2026-09-18 | MIT | yes | Go |
| Trivy (EXCLUDED) | v0.76.0 | 2026-10-14 | Apache-2.0 | n/a | compromised 2026-03-19 (GHSA-69fq-xp46-6x23 / CVE-2026-33634) |

## Summary table 2: reference implementations

| Product | Licence | Self-host + own model | Price (fact) | Last activity |
|---|---|---|---|---|
| CodeRabbit | proprietary | Enterprise self-host; BYO model n/s | free public repos; $24–$72/seat/mo; Ent custom | SaaS |
| Greptile | proprietary | Enterprise self-host; BYO model n/s | free 1 dev; $30/seat/mo; Ent custom | SaaS |
| Codacy | proprietary | no | free IDE; $18/dev/mo yearly; Business quote | SaaS |
| SonarQube Server AI Code Assurance / AI CodeFix | commercial (Community Build LGPL-3.0) | yes; CodeFix via Azure OpenAI own model | edition-priced (not captured) | 26.10 (2026-10-12) |
| Semgrep Assistant | proprietary | no | AppSec Platform plan | SaaS |
| Copilot code review | proprietary | no | Copilot paid plans; ~$0.05–$5/review in AI credits | SaaS |
| Qodo (Merge → Qodo 2.0) | proprietary | Enterprise only (on-prem, BYOK) | $30 Pro Team + credits | SaaS |
| PR-Agent | MIT | **yes** (LiteLLM, Ollama; GitHub/GitLab/Bitbucket/Azure/Gitea) | free | v0.47.0, 2026-10-02 |
| Kodus | AGPL-3.0 + EE | **yes** (BYO LLM; **Forgejo supported**) | free Community; $10/dev/mo Teams | 2026-10-15 |
| reviewdog (reporter, not LLM) | MIT | yes | free | v0.21.2, 2026-09-18 |
| OpenHands PR review | MIT | yes | free + LLM | v1.27.1, 2026-10-12 |
| claude-code-action | MIT | partial (own runner; Claude via API/Bedrock/Vertex/Foundry); GitHub-only | free + API | v1.0.250, 2026-10-14 |
| Diffblue Cover | proprietary | runs locally (Java/Kotlin test gen) | Community free (25–100 MUT/mo, sources conflict); Dev ~$30/mo | 2026-08-17 |
| Amazon CodeGuru Reviewer | proprietary | no | n/a | **maintenance mode since 2025-11-07; do not adopt** |
| Sweep | Sweep EE licence | no (pivoted to JetBrains) | n/a | 2025-09-18 |
| villesau/ai-codereviewer | MIT | OpenAI only | free | stale (2024-08-19) |
| anc95/ChatGPT-CodeReview | ISC | yes (OpenAI-compatible) | free | v1.0.24, 2026-07-14 |
| shippie (code-review-gpt) | MIT | yes | free | v0.21.2, 2026-06-23 |

## Forgejo Q16: short answer

On Forgejo you can show an advisory report in a PR **without any token** in four ways:

1. **The job log.** Reach it from the PR's commit-status check link. Everyone with read access to the repo sees it; on a public repo that includes anonymous visitors.
2. **A job summary**, by writing Markdown to `$FORGEJO_STEP_SUMMARY` (or `$GITHUB_STEP_SUMMARY`). This needs **Forgejo ≥ v17.0** (scheduled 2026-10-15; v16.0.6 is the current stable at access time) **and Forgejo Runner ≥ 13.2**. It renders above the job log, 1 MiB per step.
3. **A downloadable artifact** via `code.forgejo.org/forgejo/upload-artifact@v4` (or v5). Upstream `actions/upload-artifact@v4+` fails on Forgejo.
4. **The pass/fail check itself.** Use step-level `continue-on-error: true` to keep it advisory, because job-level `continue-on-error` and `permissions:` are ignored.

What is not available on Forgejo:
- There is **no SARIF / code-scanning UI**.
- `::set-output` was removed in runner v13; use `$FORGEJO_OUTPUT`.
- Annotations are undocumented.

Inline PR comments always need a token (the automatic token is read-only on fork PRs).

The GitHub equivalents are `$GITHUB_STEP_SUMMARY` (no token needed) and SARIF via `upload-sarif`. SARIF needs `security-events: write`, and on private repos it needs paid GitHub Code Security.
