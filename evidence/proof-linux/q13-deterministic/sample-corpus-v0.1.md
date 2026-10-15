# Phase 6 — corpus results (smoke test, n = 31 change sets: 17 defective, 14 clean)

Labels pre-registered in `sample-service/verification/labels.json` (committed before any gate ran).
Machine: 16-core workstation, niced, no GPU; LLM review = stub judge (pipeline only, NOT a model).

## Contract outcome (what an agent / developer / CI would experience)

- defective change sets blocked by some contract task: **16/17** (Wilson 95% CI 0.73–0.99)
  - first blocked at L0 `check:fast`: 11, L2 `check`: 5, L3 `ci`: 0
  - missed: D13 (correctness/edge-case-uncovered)
- clean change sets blocked (false positives): **3/14** (Wilson 95% CI 0.08–0.48): C05 by test-tamper:test-integrity.assertions-removed, C07 by diff-mutation:test-adequacy.mutation-score; repo:audit, A3 by scope-check:scope.out-of-scope-file

## Per change set

| id | label | category | blocked at | blocking gates (kit check:rules / repo task) | warn-only | LLM stub (advisory) | expected |
|---|---|---|---|---|---|---|---|
| D01 | defect | dependency/hallucinated | L0 | dep-check:dependency.not-on-registry<br>repo:test:unit<br>repo:test:integration | coverage-drop:test-adequacy.coverage-error | — | dep-check (not-on-registry); also pytest (ImportError) |
| D02 | defect | dependency/too-new | L0 | dep-check:dependency.too-new | — | — | dep-check (too-new) |
| D03 | defect | test-integrity/deleted | L0 | test-tamper:test-integrity.test-removed<br>coverage-drop:test-adequacy.coverage-drop<br>repo:lint | llm-review:llm.test-integrity | llm.test-integrity | test-tamper (test-removed) |
| D04 | defect | test-integrity/weakened | L0 | test-tamper:test-integrity.assertion-weakened | llm-review:llm.test-adequacy | llm.test-adequacy | test-tamper (assertion-weakened); bug itself: none |
| D05 | defect | test-integrity/skipped | L0 | test-tamper:test-integrity.test-skipped<br>coverage-drop:test-adequacy.coverage-drop<br>repo:test:unit | llm-review:llm.test-integrity | llm.test-integrity | test-tamper (test-skipped) |
| D06 | defect | test-adequacy/tests-written-to-pass | L2 | coverage-drop:test-adequacy.coverage-drop<br>diff-mutation:test-adequacy.mutation-score | llm-review:llm.test-adequacy | llm.test-adequacy | diff-mutation (mutation-score) |
| D07 | defect | security/sql-injection | L0 | semgrep:gates.py.sql-string-formatting | llm-review:llm.security | llm.security | semgrep (gates.py.sql-string-formatting) |
| D08 | defect | error-handling/swallowed | L0 | semgrep:gates.py.swallowed-broad-exception<br>coverage-drop:test-adequacy.coverage-drop<br>repo:lint | — | — | semgrep (gates.py.swallowed-broad-exception) |
| D09 | defect | licence/copyleft-snippet | L2 | licence-check:licence.copyleft-snippet | — | — | licence-check (copyleft-snippet) |
| D10 | defect | scope/unrequested-change | L0 | scope-check:scope.out-of-scope-file | — | — | scope-check (out-of-scope-file) |
| D11 | defect | test-adequacy/untested-module | L2 | coverage-drop:test-adequacy.coverage-drop<br>diff-mutation:test-adequacy.mutation-score<br>repo:test:unit | — | — | coverage-drop + diff-mutation |
| D12 | defect | correctness/boundary | L0 | repo:test:unit | coverage-drop:test-adequacy.coverage-error | — | repo unit tests (test_quantity_discount_thresholds) |
| D13 | defect | correctness/edge-case-uncovered | — | — | — | — | EXPECTED MISS by deterministic gates (no test covers it) |
| D14 | defect | dependency/undeclared-import | L0 | repo:test:unit<br>repo:test:integration | dep-check:dependency.undeclared-import<br>coverage-drop:test-adequacy.coverage-error | — | dep-check (undeclared-import, warn) + pytest ImportError |
| D15 | defect | duplication/copy-paste | L2 | coverage-drop:test-adequacy.coverage-drop<br>diff-mutation:test-adequacy.mutation-score | dup-check:duplication.copied-block | — | dup-check (warn only: duplication is not blocking) |
| D16 | defect | test-integrity/config-weakened | L0 | test-tamper:test-integrity.test-config-weakened<br>scope-check:scope.out-of-scope-file | — | — | test-tamper (test-config-weakened) |
| D17 | defect | secret/hard-coded | L2 | repo:secrets | — | — | repo secrets task (gitleaks) |
| C01 | clean | clean/refactor | — | — | — | — | none |
| C02 | clean | clean/docs | — | — | — | — | none |
| C03 | clean | clean/bugfix+regression-test | — | — | — | — | none |
| C04 | clean | clean/feature+tests | — | — | — | — | none |
| C05 | clean | clean/test-refactor | L0 | test-tamper:test-integrity.assertions-removed | llm-review:llm.test-integrity | llm.test-integrity | none |
| C06 | clean | clean/dead-code-removal | — | — | llm-review:llm.test-integrity | llm.test-integrity | none |
| C07 | clean | clean/dev-dependency | L2 | diff-mutation:test-adequacy.mutation-score<br>repo:audit | — | — | none |
| C08 | clean | clean/logging | — | — | — | — | none |
| C09 | clean | clean/config | — | — | — | — | none |
| C10 | clean | clean/typing | — | — | — | — | none |
| C11 | clean | clean/expected-value-change-requested | — | — | — | — | none (expectation-changed is warn by design) |
| A1 | clean | clean/feature+tests (agent) | — | — | — | — | none |
| A2 | clean | clean/feature+tests (agent) | — | — | — | — | none |
| A3 | clean | clean/expected-value-change-requested (agent) | L0 | scope-check:scope.out-of-scope-file | test-tamper:test-integrity.expectation-changed | — | none (expectation-changed is warn by design) |

## Per gate (fired = blocking finding / non-zero exit)

| gate | fired on defective | fired on clean (FP) | warn on defective | warn on clean |
|---|---|---|---|---|
| test-tamper | 4 ['D03', 'D04', 'D05', 'D16'] | 1 ['C05'] | 0 | 2 ['A3', 'A3'] |
| dep-check | 2 ['D01', 'D02'] | 0 [] | 2 | 0  |
| semgrep-changed | 2 ['D07', 'D08'] | 0 [] | 0 | 0  |
| semgrep | 2 ['D07', 'D08'] | 0 [] | 0 | 0  |
| scope-check | 2 ['D10', 'D16'] | 1 ['A3'] | 0 | 0  |
| licence-check | 1 ['D09'] | 0 [] | 0 | 0  |
| dup-check | 0 [] | 0 [] | 1 | 0  |
| coverage-drop | 6 ['D03', 'D05', 'D06', 'D08', 'D11', 'D15'] | 0 [] | 3 | 0  |
| diff-mutation | 3 ['D06', 'D11', 'D15'] | 1 ['C07'] | 0 | 0  |
| llm-review | 0 [] | 0 [] | 5 | 2 ['C05', 'C06'] |
| lint | 2 ['D03', 'D08'] | 0 [] | 0 | 0  |
| test:unit | 5 ['D01', 'D05', 'D11', 'D12', 'D14'] | 0 [] | 0 | 0  |
| secrets | 1 ['D17'] | 0 [] | 0 | 0  |
| audit | 0 [] | 1 ['C07'] | 0 | 0  |
| test:integration | 2 ['D01', 'D14'] | 0 [] | 0 | 0  |

## Wall time (seconds; smoke test on one machine, niced, sequential)

| task | n | median | max | budget |
|---|---|---|---|---|
| `check:fast` | 31 | 3.5 | 4.3 | < 60 OK |
| `check` | 31 | 23.6 | 27.5 | < 120 OK |
| `ci` | 31 | 22.7 | 50.7 | < 600 OK |
| `gates:fast` | 31 | 3.2 | 3.6 | < 60 OK |
| `gates:deterministic` | 31 | 10.7 | 11.9 | < 120 OK |
| `gates:server` | 31 | 5.6 | 31.8 | < 600 OK |

| kit check | median | max |
|---|---|---|
| test-tamper | 0.35 | 0.54 |
| dep-check | 0.32 | 1.10 |
| semgrep-changed | 2.09 | 2.69 |
| semgrep | 2.20 | 2.40 |
| scope-check | 0.07 | 0.29 |
| licence-check | 0.25 | 0.97 |
| dup-check | 0.29 | 0.36 |
| coverage-drop | 7.02 | 7.92 |
| diff-mutation | 4.84 | 31.24 |
| llm-review | 0.19 | 0.34 |

LLM review (stub) repeats identical across 3 runs: 31/31 change sets (the stub is deterministic; the nonce and reply wrapping vary per run, so this exercises parser stability).
