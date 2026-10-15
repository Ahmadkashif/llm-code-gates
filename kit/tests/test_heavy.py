"""diff_mutation and coverage_drop on a tiny repo (needs pytest + coverage importable by this interpreter)."""
import importlib.util
import sys
import unittest

from tests import helpers as h

HAVE = importlib.util.find_spec("pytest") and importlib.util.find_spec("coverage")
BASE = {"m.py": "def inc(x):\n    return x + 1\n",
        "tests/test_m.py": "from m import inc\n\n\ndef test_inc():\n    assert inc(1) == 2\n"}
STRONG = {"m.py": BASE["m.py"] + "\n\ndef bucket(n):\n    if n < 10:\n        return 'small'\n    return 'big'\n",
          "tests/test_m.py": BASE["tests/test_m.py"] + "\n\ndef test_bucket():\n    from m import bucket\n"
          "    assert bucket(9) == 'small'\n    assert bucket(10) == 'big'\n"}
WEAK = {"m.py": STRONG["m.py"],
        "tests/test_m.py": BASE["tests/test_m.py"] + "\n\ndef test_bucket():\n    from m import bucket\n"
        "    assert bucket(3) is not None\n"}
UNTESTED = {"m.py": BASE["m.py"] + "\n\ndef big(n):\n    total = 0\n    for i in range(n):\n        total += i * 2\n"
            "        if total > 100:\n            total -= 7\n    return total\n"}


@unittest.skipUnless(HAVE, "pytest/coverage not importable")
class HeavyTests(unittest.TestCase):
    cfg = {"GATES_TEST_CMD": f"{sys.executable} -m pytest -x -q -p no:cacheprovider",
           "GATES_COVERAGE_CMD": f"{sys.executable} -m coverage run -m pytest -q -p no:cacheprovider && "
                                 f"{sys.executable} -m coverage json -q -o \"$GATES_COV_JSON\"",
           "GATES_MUT_MIN_MUTANTS": "3"}

    def run_mut(self, change):
        repo = h.make_repo(BASE, change, self.cfg)
        try:
            p = h.run_check(repo, "checks/diff_mutation.py")
            return p, h.findings(repo, "diff-mutation")
        finally:
            h.cleanup(repo)

    def test_mutation_strong_tests_pass(self):
        p, fs = self.run_mut(STRONG)
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_mutation_weak_tests_block(self):
        p, fs = self.run_mut(WEAK)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("test-adequacy.mutation-score", {f["rule"] for f in fs})

    def test_mutation_skips_unexecuted_script(self):
        script = {"scripts/tool.py": "def main(n):\n    if n > 3:\n        return n * 2\n    return n + 1\n"}
        p, fs = self.run_mut(script)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("test-adequacy.unexecuted-lines", {f["rule"] for f in fs})

    def test_coverage_drop(self):
        repo = h.make_repo(BASE, UNTESTED, self.cfg)
        try:
            p = h.run_check(repo, "checks/coverage_drop.py")
            rules = {f["rule"] for f in h.findings(repo, "coverage-drop")}
        finally:
            h.cleanup(repo)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("test-adequacy.coverage-drop", rules)

    def test_no_coverage_drop_with_tests(self):
        repo = h.make_repo(BASE, STRONG, self.cfg)
        try:
            p = h.run_check(repo, "checks/coverage_drop.py")
        finally:
            h.cleanup(repo)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
