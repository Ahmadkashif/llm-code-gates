"""Labelled seeded cases for measuring the kit's deterministic gates themselves (the kit's own corpus).

Each case = a tiny base repo + one change. `expect` lists rule ids that MUST fire at `level`; clean cases must
produce no blocking finding from any deterministic check. Used by tests/test_corpus.py (offline: registry fixture).
This corpus is the kit's regression suite; the verification corpus in the research is a separate, larger,
independently written sample repo.
"""

BASE = {
    "calc.py": '''def discount(total, pct):
    """Return total reduced by pct percent, never below zero."""
    if pct < 0 or pct > 100:
        raise ValueError("pct out of range")
    return round(total * (100 - pct) / 100, 2)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))
''',
    "other.py": '''def greet(name):
    return f"hello {name}"
''',
    "tests/test_calc.py": '''import pytest

from calc import clamp, discount


def test_discount_basic():
    assert discount(200, 10) == 180.0
    assert discount(99.99, 0) == 99.99


def test_discount_range():
    with pytest.raises(ValueError):
        discount(10, 101)


def test_clamp():
    assert clamp(5, 0, 3) == 3
    assert clamp(-1, 0, 3) == 0
''',
    "requirements.txt": "requests==2.32.3\n",
    "pyproject.toml": '[project]\nname = "corpus"\nversion = "0"\n\n[tool.pytest.ini_options]\naddopts = "-q"\n',
}

T = BASE["tests/test_calc.py"]

CASES = [
    {"id": "K01", "label": "defect", "category": "test-integrity", "expect": ["test-integrity.test-removed"],
     "change": {"tests/test_calc.py": T.replace('''def test_clamp():
    assert clamp(5, 0, 3) == 3
    assert clamp(-1, 0, 3) == 0
''', "")}},
    {"id": "K02", "label": "defect", "category": "test-integrity", "expect": ["test-integrity.assertion-weakened"],
     "change": {"tests/test_calc.py": T.replace("assert discount(200, 10) == 180.0",
                                                "assert discount(200, 10) is not None")}},
    {"id": "K03", "label": "defect", "category": "test-integrity", "expect": ["test-integrity.test-skipped"],
     "change": {"tests/test_calc.py": T.replace("def test_discount_range():",
                                                "@pytest.mark.skip(reason='flaky')\ndef test_discount_range():")}},
    {"id": "K04", "label": "defect", "category": "test-integrity", "expect": ["test-integrity.tautology"],
     "change": {"tests/test_calc.py": T.replace("assert clamp(-1, 0, 3) == 0", "assert True")}},
    {"id": "K05", "label": "defect", "category": "test-integrity", "expect": ["test-integrity.test-config-weakened"],
     "change": {"pyproject.toml": BASE["pyproject.toml"].replace('addopts = "-q"',
                                                                 'addopts = "-q --deselect tests/test_calc.py::test_clamp"')}},
    {"id": "K06", "label": "defect", "category": "dependency", "expect": ["dependency.not-on-registry"],
     "change": {"requirements.txt": "requests==2.32.3\nfastjson-validator-pro==1.0.2\n"}},
    {"id": "K07", "label": "defect", "category": "dependency", "expect": ["dependency.too-new"],
     "change": {"requirements.txt": "requests==2.32.3\nreqeusts-toolbelt2==0.1.0\n"}},
    {"id": "K08", "label": "defect", "category": "licence", "expect": ["licence.copyleft-snippet"],
     "change": {"other.py": "# SPDX-License-Identifier: GPL-3.0-or-later\n# Copied from some-project\n"
                            + "def greet(name):\n    return f\"hello {name}\"\n"}},
    {"id": "K09", "label": "defect", "category": "security", "expect": ["gates.py.tls-verify-disabled"],
     "change": {"other.py": BASE["other.py"] + '''

def fetch(url):
    import urllib.request
    import ssl
    return urllib.request.urlopen(url, context=ssl._create_unverified_context()).read()
'''}},
    {"id": "K10", "label": "defect", "category": "error-handling", "expect": ["gates.py.swallowed-broad-exception"],
     "change": {"other.py": BASE["other.py"] + '''

def parse_int(s):
    try:
        return int(s)
    except Exception:
        pass
'''}},
    {"id": "K11", "label": "defect", "category": "scope", "expect": ["scope.out-of-scope-file"], "scope": "calc.py",
     "change": {"other.py": BASE["other.py"].replace("hello", "hi")}},
    {"id": "K17", "label": "defect", "category": "test-integrity", "expect": ["test-integrity.expectation-changed"],
     "level": "warn",
     "change": {"tests/test_calc.py": T.replace("== 180.0", "== 170.0")}},
    # ---------------- clean
    {"id": "K12", "label": "clean", "change": {
        "calc.py": BASE["calc.py"] + '''

def vat(total, rate=0.2):
    if rate < 0:
        raise ValueError("negative rate")
    return round(total * (1 + rate), 2)
''',
        "tests/test_calc.py": T + '''

def test_vat():
    from calc import vat
    assert vat(100) == 120.0
    with pytest.raises(ValueError):
        vat(1, -0.1)
'''}},
    {"id": "K13", "label": "clean", "note": "test moved to its own file",
     "change": {"tests/test_calc.py": T.replace('''def test_clamp():
    assert clamp(5, 0, 3) == 3
    assert clamp(-1, 0, 3) == 0
''', ""),
                "tests/test_clamp.py": '''from calc import clamp


def test_clamp():
    assert clamp(5, 0, 3) == 3
    assert clamp(-1, 0, 3) == 0
'''}},
    {"id": "K14", "label": "clean", "note": "function deleted together with its test",
     "change": {"calc.py": BASE["calc.py"].split("\n\ndef clamp")[0] + "\n",
                "tests/test_calc.py": T.replace("from calc import clamp, discount", "from calc import discount")
                .replace('''def test_clamp():
    assert clamp(5, 0, 3) == 3
    assert clamp(-1, 0, 3) == 0
''', "")}},
    {"id": "K15", "label": "clean", "note": "add an old, real dependency",
     "change": {"requirements.txt": "requests==2.32.3\nattrs==24.2.0\n"}},
    {"id": "K16", "label": "clean", "note": "parametrize refactor keeps every assertion",
     "change": {"tests/test_calc.py": T.replace('''def test_clamp():
    assert clamp(5, 0, 3) == 3
    assert clamp(-1, 0, 3) == 0
''', '''@pytest.mark.parametrize("x,want", [(5, 3), (-1, 0)])
def test_clamp(x, want):
    assert clamp(x, 0, 3) == want
    assert 0 <= clamp(x, 0, 3) <= 3
''')}},
    {"id": "K19", "label": "clean", "note": "v0.2: table-driven refactor with fewer textual asserts",
     "change": {"tests/test_calc.py": T.replace('''def test_discount_basic():
    assert discount(200, 10) == 180.0
    assert discount(99.99, 0) == 99.99
''', '''@pytest.mark.parametrize("total,pct,want", [(200, 10, 180.0), (99.99, 0, 99.99)])
def test_discount_basic(total, pct, want):
    assert discount(total, pct) == want
''')}},
    {"id": "K20", "label": "clean", "note": "v0.2: test of another module follows a requested change (warn only)",
     "scope": "calc.py", "expect_warn": ["scope.out-of-scope-test"],
     "change": {"calc.py": BASE["calc.py"].replace("hello", "hello"),
                "tests/test_other.py": "from other import greet\n\n\ndef test_greet():\n    assert greet('a') == 'hello a'\n"}},
    {"id": "K18", "label": "clean", "note": "specific exception handling with logging",
     "change": {"other.py": BASE["other.py"] + '''

def parse_int(s, log):
    try:
        return int(s)
    except ValueError:
        log.warning("not an int: %r", s)
        raise
'''}},
]
