"""Run the deterministic checks over the kit's labelled corpus (corpus/cases.py)."""
import unittest

from tests import helpers as h
import cases as corpus

DETERMINISTIC = {
    "test-tamper": "checks/test_tamper.py",
    "dep-check": "checks/dep_check.py",
    "licence-check": "checks/licence_check.py",
    "scope-check": "checks/scope_check.py",
    "dup-check": "checks/dup_check.py",
    "semgrep": "checks/semgrep_gate.py",
}


class CorpusTests(unittest.TestCase):
    def run_case(self, case):
        cfg = {"GATES_SCOPE": case["scope"]} if case.get("scope") else {}
        repo = h.make_repo(corpus.BASE, case["change"], cfg)
        try:
            out = {}
            for name, script in DETERMINISTIC.items():
                if name == "semgrep" and not h.have_semgrep():
                    continue
                h.run_check(repo, script)
                out[name] = h.findings(repo, name)
            return out
        finally:
            h.cleanup(repo)

    def test_cases(self):
        for case in corpus.CASES:
            with self.subTest(case=case["id"]):
                out = self.run_case(case)
                allf = [f for fs in out.values() for f in fs]
                blocking = [f["rule"] for f in allf if f["level"] == "block"]
                if case["label"] == "clean":
                    self.assertEqual(blocking, [], f"{case['id']} false positive")
                    warns = {f["rule"] for f in allf if f["level"] == "warn"}
                    for rule in case.get("expect_warn", []):
                        self.assertIn(rule, warns, case["id"])
                else:
                    if "gates.py." in case["expect"][0] and not h.have_semgrep():
                        self.skipTest("semgrep not installed")
                    level = case.get("level", "block")
                    got = {f["rule"] for f in allf if f["level"] == level}
                    for rule in case["expect"]:
                        self.assertIn(rule, got, f"{case['id']} missed {rule}; got {[(f['rule'], f['level']) for f in allf]}")


if __name__ == "__main__":
    unittest.main()
