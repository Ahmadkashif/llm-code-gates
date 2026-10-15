import datetime as dt
import json
import unittest
from pathlib import Path

from tests import helpers  # noqa: F401  (sets sys.path)
import gateslib as g
import parse


class YamlTests(unittest.TestCase):
    def test_subset(self):
        d = g.yaml_load("""
a: 1
b: "x: y"   # comment
c: [1, two, "three"]
d:
  - k: v
    n: 2
  - plain
e: |
  line1
  line2
f: {x: 1, y: true}
g: null
""")
        self.assertEqual(d, {"a": 1, "b": "x: y", "c": [1, "two", "three"], "d": [{"k": "v", "n": 2}, "plain"],
                             "e": "line1\nline2\n", "f": {"x": 1, "y": True}, "g": None})

    def test_all_profiles_and_taskfile_parse(self):
        for f in list((helpers.KIT / "profiles").glob("*/*.yml")) + [helpers.KIT / "Taskfile.gates.yml"]:
            self.assertIsInstance(g.load_yaml_file(f), dict, f)

    def test_matches_pyyaml_when_available(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed")
        for f in list((helpers.KIT / "profiles").glob("*/*.yml")) + [helpers.KIT / "Taskfile.gates.yml"]:
            self.assertEqual(g.load_yaml_file(f), yaml.safe_load(f.read_text()), f)


class SchemaTests(unittest.TestCase):
    schema = json.loads((helpers.KIT / "schemas" / "findings.schema.json").read_text())

    def good(self):
        return {"analysis": "ok", "findings": [{"category": "correctness", "severity": "high", "confidence": 0.9,
                                                "path": "a.py", "side": "new", "line_start": 3, "line_end": 3,
                                                "title": "off by one", "evidence": "x < n",
                                                "failure_scenario": "Input/state: n=3 -> executes line 3 -> ...",
                                                "suggested_test": None, "cwe": None, "scope_kind": None}]}

    def test_valid(self):
        self.assertEqual(g.validate(self.good(), self.schema), [])
        self.assertEqual(g.validate({"analysis": "", "findings": []}, self.schema), [])

    def test_invalid(self):
        bad = self.good()
        bad["findings"][0]["severity"] = "huge"
        bad["findings"][0]["extra"] = 1
        del bad["findings"][0]["evidence"]
        errs = g.validate(bad, self.schema)
        self.assertTrue(any("severity" in e for e in errs) and any("extra" in e for e in errs)
                        and any("evidence" in e for e in errs), errs)
        self.assertTrue(g.validate({"analysis": "x", "findings": [], "more": 1}, self.schema))

    def test_agrees_with_jsonschema_when_available(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        for doc in (self.good(), {"analysis": 3, "findings": []}, {"findings": []}):
            ours = not g.validate(doc, self.schema)
            theirs = jsonschema.Draft202012Validator(self.schema).is_valid(doc)
            self.assertEqual(ours, theirs, doc)


class ParseTests(unittest.TestCase):
    def test_variants(self):
        cases = {
            '<think>reasoning {"no": 1}</think>\n{"analysis": "a", "findings": []}': {"analysis": "a", "findings": []},
            '<think>\n\n</think>\n\n```json\n{"a": True, "b": [1,],}\n```': {"a": True, "b": [1]},
            'Sure: {"a": "brace } inside"} trailing': {"a": "brace } inside"},
            '<think>unclosed... {"a": 2}': {"a": 2},
        }
        for text, want in cases.items():
            self.assertEqual(parse.extract_json(text), (want, None), text)
        self.assertIsNone(parse.extract_json("no json here")[0])
        self.assertIsNone(parse.extract_json("")[0])


class SuppressionTests(unittest.TestCase):
    def test_expiry(self):
        import tempfile
        root = Path(tempfile.mkdtemp())
        (root / ".gates").mkdir()
        f1 = g.Finding("c", "rule.a", "security", "high", "m", "x.py", 1, "ev")
        f2 = g.Finding("c", "rule.b", "security", "high", "m", "x.py", 2, "ev2")
        (root / ".gates" / "suppressions.json").write_text(json.dumps({"suppressions": [
            {"rule": "rule.a", "reason": "accepted risk", "expires": "2099-01-01"},
            {"fingerprint": f2.fingerprint, "reason": "old", "expires": "2000-01-01"},
            {"rule": "rule.*", "expires": "2099-01-01"}]}))
        notes = g.apply_suppressions([f1, f2], root, today=dt.date(2026, 10, 15))
        self.assertTrue(f1.suppressed)
        self.assertFalse(f2.suppressed)
        self.assertTrue(any("EXPIRED" in n for n in notes))
        self.assertTrue(any("without 'reason'" in n for n in notes))

    def test_fingerprint_ignores_line(self):
        a = g.Finding("c", "r", "security", "high", "m", "x.py", 1, "  foo(bar) ")
        b = g.Finding("c", "r", "security", "high", "m", "x.py", 40, "foo(bar)")
        self.assertEqual(a.fingerprint, b.fingerprint)

    def test_sarif(self):
        s = g.to_sarif("t", [g.Finding("c", "r", "security", "high", "m", "x.py", 3, "e", level="warn")])
        r = s["runs"][0]["results"][0]
        self.assertEqual((s["version"], r["level"], r["locations"][0]["physicalLocation"]["region"]["startLine"]),
                         ("2.1.0", "warning", 3))


if __name__ == "__main__":
    unittest.main()
