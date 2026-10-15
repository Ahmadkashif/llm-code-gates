# Pre-registered labels (31 change sets: 17 defective, 14 clean)

Committed before any gate ran. Branches `cs/<id>`; each carries its task statement in `.gates/task.md`.

| id | label | category | expected to be caught by | author |
|---|---|---|---|---|
| D01 | defect | dependency/hallucinated | dep-check (not-on-registry); also pytest (ImportError) | hand |
| D02 | defect | dependency/too-new | dep-check (too-new) | hand |
| D03 | defect | test-integrity/deleted | test-tamper (test-removed) | hand |
| D04 | defect | test-integrity/weakened | test-tamper (assertion-weakened); bug itself: none | hand |
| D05 | defect | test-integrity/skipped | test-tamper (test-skipped) | hand |
| D06 | defect | test-adequacy/tests-written-to-pass | diff-mutation (mutation-score) | hand |
| D07 | defect | security/sql-injection | semgrep (gates.py.sql-string-formatting) | hand |
| D08 | defect | error-handling/swallowed | semgrep (gates.py.swallowed-broad-exception) | hand |
| D09 | defect | licence/copyleft-snippet | licence-check (copyleft-snippet) | hand |
| D10 | defect | scope/unrequested-change | scope-check (out-of-scope-file) | hand |
| D11 | defect | test-adequacy/untested-module | coverage-drop + diff-mutation | hand |
| D12 | defect | correctness/boundary | repo unit tests (test_quantity_discount_thresholds) | hand |
| D13 | defect | correctness/edge-case-uncovered | EXPECTED MISS by deterministic gates (no test covers it) | hand |
| D14 | defect | dependency/undeclared-import | dep-check (undeclared-import, warn) + pytest ImportError | hand |
| D15 | defect | duplication/copy-paste | dup-check (warn only: duplication is not blocking) | hand |
| D16 | defect | test-integrity/config-weakened | test-tamper (test-config-weakened) | hand |
| D17 | defect | secret/hard-coded | repo secrets task (gitleaks) | hand |
| C01 | clean | clean/refactor | none | hand |
| C02 | clean | clean/docs | none | hand |
| C03 | clean | clean/bugfix+regression-test | none | hand |
| C04 | clean | clean/feature+tests | none | hand |
| C05 | clean | clean/test-refactor | none | hand |
| C06 | clean | clean/dead-code-removal | none | hand |
| C07 | clean | clean/dev-dependency | none | hand |
| C08 | clean | clean/logging | none | hand |
| C09 | clean | clean/config | none | hand |
| C10 | clean | clean/typing | none | hand |
| C11 | clean | clean/expected-value-change-requested | none (expectation-changed is warn by design) | hand |
| A1 | clean | clean/feature+tests (agent) | none | agent |
| A2 | clean | clean/feature+tests (agent) | none | agent |
| A3 | clean | clean/expected-value-change-requested (agent) | none (expectation-changed is warn by design) | agent |
