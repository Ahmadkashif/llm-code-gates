# Backlog — llm-code-gates (ideas and follow-ups; not built in this round)

## Needs the user first (each is a live-host change or an approval)

1. **local-8gb measurement (open question 1 / 9).** Run on the machine where #7's gateway actually lives. It needs a
   dedicated review-only keyward key and an approved GPU window. This run's machine has no gateway and no NVIDIA
   GPU. Commands are in STATUS.md.
2. **Forgejo PR in #3's ci lane (open question 7).** Resume #3's lab container and VMs, push the sample repo with
   the kit, and open a red PR and a green PR. Commands are in STATUS.md.
3. **Tool image (open question 6).** `docker build` of `kit/Dockerfile`, then run `task check` inside it with
   `--cpus/--memory` limits.
4. **Cloud judge (open question 3).** Only on the synthetic sample. The provider and key come from the user.
5. **ci-lane secret decision (open question 2).** Choose (a), (b) or (c); the recommendation is (c) now and (b)
   later.

## Kit improvements found during verification

6. **Self-integrity check.** The kit skips `gates/` and `.gates/`, so a change that weakens
   `.gates/config.env`/`site.env` (for example `GATES_LEVEL_*=inform`) or edits `gates/` is not flagged by the kit
   itself.
   - Add a `gates:integrity` check: the vendored-kit hash vs `kit.lock`, plus a diff of `.gates/*.env` vs BASE.
     Any loosening becomes a block.
   - Protect both paths with CODEOWNERS.
7. **Suppressions: enforce a maximum expiry** (for example 90 days) and require an `owner` field.
8. **test-tamper: parametrize-aware assertion counting.**
   - A table-driven refactor reduces textual assert count while keeping coverage of cases.
   - Count `parametrize` rows × asserts, or compare the set of (input, expected) literals.
   - A related false-positive class, a test whose assertion is removed together with the code it referenced, is
     already handled for whole tests. Extend that to single assertions that reference deleted names.
9. **test-tamper for JS/TS/Go via a real parser** (tree-sitter) instead of counts.
10. **diff-mutation operators.** Add statement deletion, call removal and string-constant mutation, and per-file
    caps. Run on the tests most likely to kill each mutant (coverage-guided) to cut wall time.
11. **coverage-drop for TS/Go** (c8 JSON summary, `go test -coverprofile`).
12. **dep-check.**
    - Add crates.io and deps.dev (seven ecosystems).
    - Add an OpenSSF malicious-packages lookup.
    - Add typosquat distance against the top-N packages.
    - Map import names to distribution names (`yaml`→PyYAML) from installed metadata, to cut undeclared-import
      warnings.
13. **licence-check.** Add an optional ScanCode/SCANOSS snippet-fingerprint mode for code copied without a header.
14. **dup-check.** Add Type-2 clones (identifier-normalised).
15. **LLM review.**
    - Verifier from a different model family (a second endpoint).
    - 2-of-3 verifier samples for blocking categories.
    - A labelled-data harness: export findings to a labelling CSV, then compute Wilson precision per category and
      suggest promotion or demotion.
    - Measure prompt-injection resistance against real models with a seeded injection corpus (nonce tags,
      "nosec"/"reviewed" framings).
16. **Provenance (RQ8).**
    - A `gates:attest` task that writes an in-toto `test-result/v0.1` statement for HEAD from
      `.gates/out/summary-*.json` and signs it offline with `cosign attest-blob --key`.
    - An `Assisted-by:` trailer check for agent commits.
17. **Forgejo v17 job summaries.** When v17 and Runner ≥ 13.2 are deployed, write `llm-review.md` to
    `$FORGEJO_STEP_SUMMARY`. The code already supports it; it needs verifying on a real runner.
18. **PR comments via a bot token.** Out of scope (it needs a token in the ci lane). Revisit after the ci-lane
    decision.
19. **L5 scheduled task template.** Full mutmut/Stryker run, re-baseline, dependency re-audit, and a
    "not useful" rate report from suppressions.

## Upstream notes for #3 (self-hosted-cicd)

20. **zizmor on Forgejo workflows.** `zizmor --offline .forgejo/workflows/` collects nothing ("no inputs collected",
    exit 3). Pass the files instead: `.forgejo/workflows/*.yml`. #3's repo-template Taskfile uses the directory
    form; check it.
21. **actionlint and Forgejo.** It needs a config listing the runner labels (`ci`, `deploy`, `review`). It rejects
    Forgejo's full-URL `uses: https://code.forgejo.org/...` form, so lint the GitHub-style snippets only, or accept
    that one error.
22. **osv-scanner transitive resolution** of `requirements*.txt` picked an old pygments (2.9.0) and reported 2 CVEs
    that are not installed. Pin transitive dependencies in the scanned file, or scan a full lock (`pip freeze`).
23. **Offer the kit as an optional include** in #3's repo-template (`includes: gates:`), with a stub judge by default.

## Research follow-ups

24. A field study of assertion weakening and test deletion in real agent PRs (no source measured it; RQ1 gap).
25. Re-measure the verification corpus with a real 30B+ judge and report per-category precision against the Wilson
    rule.
26. Converge with the `_soul` pipeline's verification (Part 6/7). The `redcheck.py` idea, a stub that proves a test
    discriminates, is a cousin of diff-mutation. Note the overlap; do not merge.
