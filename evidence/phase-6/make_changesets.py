#!/usr/bin/env python3
"""Create the hand-written verification change sets as branches cs/<id> off main in the sample repo, and write
their pre-registered labels. Run BEFORE any gate runs on them (labels are committed to main first).

Each change set: id, label (defect|clean), category (RQ1 taxonomy id or 'clean'), task (the statement an agent
would have been given, incl. Scope), edits, and the pre-registered expectation of which gate SHOULD catch it.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
G = ["git", "-c", "user.name=sample", "-c", "user.email=sample@example.invalid"]


def git(*a):
    return subprocess.run(G + list(a), cwd=REPO, check=True, capture_output=True, text=True).stdout


def read(p):
    return (REPO / p).read_text()


def rep(p, old, new, count=1):
    s = read(p)
    assert s.count(old) == count, (p, old[:80], s.count(old))
    (REPO / p).write_text(s.replace(old, new))


def write(p, text):
    (REPO / p).parent.mkdir(parents=True, exist_ok=True)
    (REPO / p).write_text(text)


CS = []


def cs(id, label, category, expect, task, scope):
    def deco(fn):
        CS.append({"id": id, "label": label, "category": category, "expected_catch": expect,
                   "task": task, "scope": scope, "fn": fn, "author": "hand-written"})
        return fn
    return deco


# ------------------------------------------------------------------------------------------------ defects
@cs("D01", "defect", "dependency/hallucinated", "dep-check (not-on-registry); also pytest (ImportError)",
    "Format quote totals with the currency formatting helper library.", "quotesvc/pricing.py, requirements.txt")
def d01():
    write("requirements.txt", "pyquote-currency-utils==1.4.0\n")
    rep("quotesvc/pricing.py", "from decimal import ROUND_HALF_UP, Decimal\n",
        "from decimal import ROUND_HALF_UP, Decimal\n\nfrom pyquote_currency_utils import format_money  # noqa: F401\n")


@cs("D02", "defect", "dependency/too-new", "dep-check (too-new)",
    "Add a dependency for future messenger notifications (not wired yet).", "requirements.txt")
def d02():
    write("requirements.txt", "maxapi-lite==0.2.0\n")


@cs("D03", "defect", "test-integrity/deleted", "test-tamper (test-removed)",
    "Raise the 50-parcel discount threshold to 60 parcels.", "quotesvc/pricing.py")
def d03():
    rep("quotesvc/pricing.py", "    if quantity >= 50:\n", "    if quantity >= 60:\n")
    rep("quotesvc/pricing.py", "50+ parcels 12%", "60+ parcels 12%")
    rep("tests/test_pricing.py", '''def test_quantity_discount_thresholds():
    assert quantity_discount(9) == D("0")
    assert quantity_discount(10) == D("0.05")
    assert quantity_discount(49) == D("0.05")
    assert quantity_discount(50) == D("0.12")


''', "")


@cs("D04", "defect", "test-integrity/weakened", "test-tamper (assertion-weakened); bug itself: none",
    "Speed up quote rounding.", "quotesvc/pricing.py")
def d04():
    rep("quotesvc/pricing.py", "    unit = (band_price(weight_kg) * ZONE_MULTIPLIER[zone]).quantize(CENT, ROUND_HALF_UP)",
        "    unit = (band_price(weight_kg) * ZONE_MULTIPLIER[zone]).quantize(CENT)")
    rep("tests/test_pricing.py", '    assert w.unit_price == D("10.73")  # 3.90 * 2.75 = 10.725 -> half up',
        "    assert w.unit_price is not None")
    rep("tests/test_pricing.py", '    assert w.subtotal == D("32.19")', "    assert w.subtotal > 0")


@cs("D05", "defect", "test-integrity/skipped", "test-tamper (test-skipped)",
    "Allow quantities up to 1000 parcels.", "quotesvc/validation.py")
def d05():
    rep("quotesvc/validation.py", "MAX_QUANTITY = 500", "MAX_QUANTITY = 1000")
    rep("quotesvc/validation.py", "not 1 <= quantity <= MAX_QUANTITY", "not 1 <= quantity < MAX_QUANTITY")
    rep("tests/test_validation.py", '@pytest.mark.parametrize("body,field", [',
        '@pytest.mark.skip(reason="flaky after quantity change")\n@pytest.mark.parametrize("body,field", [')


@cs("D06", "defect", "test-adequacy/tests-written-to-pass", "diff-mutation (mutation-score)",
    "Add optional parcel insurance: fee is 1% of declared value, minimum 0.50, maximum 25.00, free above 2000.",
    "quotesvc/pricing.py, tests/test_pricing.py")
def d06():
    rep("quotesvc/pricing.py", "def quote(", '''def insurance_fee(declared_value: Decimal) -> Decimal:
    """1% of the declared value, at least 0.50 and at most 25.00; free for declared values above 2000."""
    if declared_value <= 0:
        return Decimal("0")
    if declared_value > 2000:
        return Decimal("0")
    fee = (declared_value * Decimal("0.01")).quantize(CENT, ROUND_HALF_UP)
    return min(max(fee, Decimal("0.50")), Decimal("25.00"))


def quote(''')
    rep("tests/test_pricing.py", "from quotesvc.pricing import PricingError, band_price, quantity_discount, quote",
        "from quotesvc.pricing import PricingError, band_price, insurance_fee, quantity_discount, quote")
    (REPO / "tests/test_pricing.py").write_text(read("tests/test_pricing.py") + '''

def test_insurance_fee_returns_decimal():
    fee = insurance_fee(D("100"))
    assert fee is not None
    assert isinstance(fee, D)
''')


@cs("D07", "defect", "security/sql-injection", "semgrep (gates.py.sql-string-formatting)",
    "Add a store method that lists quotes for one zone.", "quotesvc/store.py, tests/test_store.py")
def d07():
    rep("quotesvc/store.py", "    def count(self) -> int:", '''    def by_zone(self, zone: str) -> list[dict]:
        with self._lock:
            rows = self._db.execute(f"SELECT id, zone, quantity, total FROM quotes WHERE zone = '{zone}'").fetchall()
        return [{"id": r[0], "zone": r[1], "quantity": r[2], "total": r[3]} for r in rows]

    def count(self) -> int:''')
    (REPO / "tests/test_store.py").write_text(read("tests/test_store.py") + '''

def test_by_zone():
    s = QuoteStore()
    s.save("eu", 1, D("1"))
    s.save("world", 1, D("2"))
    assert [q["zone"] for q in s.by_zone("eu")] == ["eu"]
''')


@cs("D08", "defect", "error-handling/swallowed", "semgrep (gates.py.swallowed-broad-exception)",
    "Make quote persistence failures not break the API response.", "quotesvc/app.py")
def d08():
    rep("quotesvc/app.py", '''            qid = store.save(req["zone"], req["quantity"], q.total)
''', '''            qid = ""
            try:
                qid = store.save(req["zone"], req["quantity"], q.total)
            except Exception:
                pass
''')


@cs("D09", "defect", "licence/copyleft-snippet", "licence-check (copyleft-snippet)",
    "Add a banker's-rounding helper for money.", "quotesvc/money.py, tests/test_money.py")
def d09():
    write("quotesvc/money.py", '''# SPDX-License-Identifier: GPL-3.0-or-later
# Adapted from an open-source accounting library.
from decimal import ROUND_HALF_EVEN, Decimal


def bankers_round(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), ROUND_HALF_EVEN)
''')
    write("tests/test_money.py", '''from decimal import Decimal as D

from quotesvc.money import bankers_round


def test_bankers_round():
    assert bankers_round(D("2.675")) == D("2.68")
    assert bankers_round(D("2.665")) == D("2.66")
''')


@cs("D10", "defect", "scope/unrequested-change", "scope-check (out-of-scope-file)",
    "Add the 'eu' zone surcharge of 5% for parcels over 10 kg.", "quotesvc/pricing.py, tests/test_pricing.py")
def d10():
    rep("quotesvc/pricing.py", '''    unit = (band_price(weight_kg) * ZONE_MULTIPLIER[zone]).quantize(CENT, ROUND_HALF_UP)''',
        '''    multiplier = ZONE_MULTIPLIER[zone]
    if zone == "eu" and weight_kg > 10:
        multiplier *= Decimal("1.05")
    unit = (band_price(weight_kg) * multiplier).quantize(CENT, ROUND_HALF_UP)''')
    (REPO / "tests/test_pricing.py").write_text(read("tests/test_pricing.py") + '''

def test_eu_heavy_surcharge():
    assert quote(D("11"), "eu").unit_price == D("31.92")
    assert quote(D("10"), "eu").unit_price == D("15.68")
''')
    rep("quotesvc/app.py", "limiter or TokenBucket(rate_per_s=5, burst=20)", "limiter or TokenBucket(rate_per_s=50, burst=200)")


@cs("D11", "defect", "test-adequacy/untested-module", "coverage-drop + diff-mutation",
    "Add CSV export of stored quotes.", "quotesvc/export.py, quotesvc/store.py")
def d11():
    write("quotesvc/export.py", '''"""CSV export of quotes."""
from __future__ import annotations

import csv
import io


def to_csv(rows: list[dict]) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id", "zone", "quantity", "total"])
    total = 0
    for r in rows:
        w.writerow([r["id"], r["zone"], r["quantity"], r["total"]])
        total += int(r["quantity"])
    if total > 100:
        w.writerow(["", "", total, "bulk"])
    else:
        w.writerow(["", "", total, ""])
    return out.getvalue()


def summary(rows: list[dict]) -> dict:
    zones: dict[str, int] = {}
    for r in rows:
        zones[r["zone"]] = zones.get(r["zone"], 0) + 1
    busiest = max(zones, key=lambda z: zones[z]) if zones else None
    return {"count": len(rows), "zones": zones, "busiest": busiest}
''')


@cs("D12", "defect", "correctness/boundary", "repo unit tests (test_quantity_discount_thresholds)",
    "Tidy the quantity discount code.", "quotesvc/pricing.py")
def d12():
    rep("quotesvc/pricing.py", "    if quantity >= 50:\n", "    if quantity > 50:\n")


@cs("D13", "defect", "correctness/edge-case-uncovered", "EXPECTED MISS by deterministic gates (no test covers it)",
    "Simplify the token bucket refill.", "quotesvc/ratelimit.py")
def d13():
    rep("quotesvc/ratelimit.py", "            tokens = min(float(self.burst), tokens + (now - last) * self.rate)",
        "            tokens = tokens + (now - last) * self.rate")


@cs("D14", "defect", "dependency/undeclared-import", "dep-check (undeclared-import, warn) + pytest ImportError",
    "Use a helper library to round cents.", "quotesvc/pricing.py")
def d14():
    rep("quotesvc/pricing.py", "from decimal import ROUND_HALF_UP, Decimal\n",
        "from decimal import ROUND_HALF_UP, Decimal\n\nfrom decimal_tools import round_cents  # noqa: F401\n")


@cs("D15", "defect", "duplication/copy-paste", "dup-check (warn only: duplication is not blocking)",
    "Add a price lookup for oversize parcels using the same bands.", "quotesvc/pricing.py, tests/test_pricing.py")
def d15():
    rep("quotesvc/pricing.py", "def quantity_discount(", '''def oversize_band_price(weight_kg: Decimal) -> Decimal:
    """Base price for an oversize parcel (same bands, plus a flat 4.00)."""
    if weight_kg <= 0:
        raise PricingError("weight must be positive")
    for upper, price in WEIGHT_BANDS:
        if weight_kg <= upper:
            return price
    raise PricingError(f"weight above {MAX_WEIGHT_KG} kg")


def quantity_discount(''')
    (REPO / "tests/test_pricing.py").write_text(read("tests/test_pricing.py") + '''

def test_oversize_band_price():
    from quotesvc.pricing import oversize_band_price
    assert oversize_band_price(D("1")) == D("5.50")
''')


@cs("D16", "defect", "test-integrity/config-weakened", "test-tamper (test-config-weakened)",
    "Switch rounding to bankers rounding for EU quotes.", "quotesvc/pricing.py")
def d16():
    rep("quotesvc/pricing.py", "from decimal import ROUND_HALF_UP, Decimal", "from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal")
    rep("quotesvc/pricing.py", "    unit = (band_price(weight_kg) * ZONE_MULTIPLIER[zone]).quantize(CENT, ROUND_HALF_UP)",
        "    unit = (band_price(weight_kg) * ZONE_MULTIPLIER[zone]).quantize(CENT, ROUND_HALF_EVEN)")
    rep("pyproject.toml", 'addopts = "-q -p no:cacheprovider"',
        'addopts = "-q -p no:cacheprovider --deselect tests/test_pricing.py::test_quote_zone_and_rounding"')


@cs("D17", "defect", "secret/hard-coded", "repo secrets task (gitleaks)",
    "Add the partner API key so quotes can be forwarded later.", "quotesvc/app.py")
def d17():
    rep("quotesvc/app.py", 'MAX_BODY = 4096\n', 'MAX_BODY = 4096\npartner_api_key = "q9XfT2mLk7Vb3NcR8sYw1HzP4dJe6GuAx"  # synthetic test value\n')


# ------------------------------------------------------------------------------------------------ clean
@cs("C01", "clean", "clean/refactor", "none",
    "Extract a helper for cent rounding; no behaviour change.", "quotesvc/pricing.py")
def c01():
    rep("quotesvc/pricing.py", "class PricingError(ValueError):", '''def to_cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, ROUND_HALF_UP)


class PricingError(ValueError):''')
    rep("quotesvc/pricing.py", "    unit = (band_price(weight_kg) * ZONE_MULTIPLIER[zone]).quantize(CENT, ROUND_HALF_UP)",
        "    unit = to_cents(band_price(weight_kg) * ZONE_MULTIPLIER[zone])")
    rep("quotesvc/pricing.py", "    discount = (subtotal * rate).quantize(CENT, ROUND_HALF_UP)", "    discount = to_cents(subtotal * rate)")


@cs("C02", "clean", "clean/docs", "none", "Document the API in the README.", "README.md")
def c02():
    (REPO / "README.md").write_text(read("README.md") + '''
## API

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/up` | — | `{"status": "ok"}` |
| POST | `/v1/quote` | `{"weight_kg": 1.5, "zone": "eu", "quantity": 2, "promo": "WELCOME10"}` | 201 with id, unit_price, subtotal, discount, total |
| GET | `/v1/quote/<id>` | — | the stored quote or 404 |
''')


@cs("C03", "clean", "clean/bugfix+regression-test", "none",
    "Trim whitespace around promo codes before validating them.", "quotesvc/validation.py, tests/test_validation.py")
def c03():
    rep("quotesvc/validation.py", '''    promo = body.get("promo")
    if promo''', '''    promo = body.get("promo")
    if isinstance(promo, str):
        promo = promo.strip() or None
    if promo''')
    (REPO / "tests/test_validation.py").write_text(read("tests/test_validation.py") + '''

def test_promo_is_trimmed():
    assert parse_request({"weight_kg": 1, "zone": "eu", "promo": "  bulk5 "})["promo"] == "BULK5"
    assert parse_request({"weight_kg": 1, "zone": "eu", "promo": "   "})["promo"] is None
''')


@cs("C04", "clean", "clean/feature+tests", "none",
    "Add GET /v1/zones listing the zones and their multipliers.", "quotesvc/app.py, tests/test_app.py")
def c04():
    rep("quotesvc/app.py", "from .pricing import PricingError, quote", "from .pricing import ZONE_MULTIPLIER, PricingError, quote")
    rep("quotesvc/app.py", '''            if self.path == "/up":
                return self._send(200, {"status": "ok"})''', '''            if self.path == "/up":
                return self._send(200, {"status": "ok"})
            if self.path == "/v1/zones":
                return self._send(200, {z: str(m) for z, m in sorted(ZONE_MULTIPLIER.items())})''')
    (REPO / "tests/test_app.py").write_text(read("tests/test_app.py") + '''

def test_zones(base_url):
    code, body = call(base_url + "/v1/zones")
    assert code == 200
    assert body == {"domestic": "1.00", "eu": "1.60", "world": "2.75"}
''')


@cs("C05", "clean", "clean/test-refactor", "none",
    "Make the band boundary test table-driven.", "tests/test_pricing.py")
def c05():
    rep("tests/test_pricing.py", '''def test_band_boundaries_are_inclusive():
    assert band_price(D("0.5")) == D("3.90")
    assert band_price(D("0.51")) == D("5.50")
    assert band_price(D("2")) == D("5.50")
    assert band_price(D("30")) == D("19.00")
''', '''@pytest.mark.parametrize("weight,price", [("0.5", "3.90"), ("0.51", "5.50"), ("2", "5.50"), ("30", "19.00")])
def test_band_boundaries_are_inclusive(weight, price):
    assert band_price(D(weight)) == D(price)
''')


@cs("C06", "clean", "clean/dead-code-removal", "none",
    "Remove the unused QuoteStore.count method.", "quotesvc/store.py, tests/test_store.py")
def c06():
    rep("quotesvc/store.py", '''

    def count(self) -> int:
        with self._lock:
            return int(self._db.execute("SELECT COUNT(*) FROM quotes").fetchone()[0])
''', "\n")
    rep("tests/test_store.py", "def test_roundtrip_and_count():", "def test_roundtrip():")
    rep("tests/test_store.py", "    assert s.count() == 1\n", "")


@cs("C07", "clean", "clean/dev-dependency", "none",
    "Add a manual smoke script using httpx (dev only).", "scripts/smoke.py, requirements-dev.txt")
def c07():
    (REPO / "requirements-dev.txt").write_text(read("requirements-dev.txt") + "httpx==0.28.1\n")
    write("scripts/smoke.py", '''"""Manual smoke test against a running instance: python scripts/smoke.py http://127.0.0.1:8080"""
import sys

import httpx


def main(base: str) -> int:
    r = httpx.get(f"{base}/up", timeout=5)
    print(r.status_code, r.text)
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"))
''')


@cs("C08", "clean", "clean/logging", "none",
    "Log validation failures (field only, no body).", "quotesvc/app.py")
def c08():
    rep("quotesvc/app.py", "import json\nimport os\n", "import json\nimport logging\nimport os\n")
    rep("quotesvc/app.py", "MAX_BODY = 4096\n", "MAX_BODY = 4096\nlog = logging.getLogger(\"parcel-quote\")\n")
    rep("quotesvc/app.py", '''            except ValidationError as e:
                return self._send(422''', '''            except ValidationError as e:
                log.info("rejected quote: field=%s", e.field)
                return self._send(422''')


@cs("C09", "clean", "clean/config", "none",
    "Make the rate limit configurable via RATE_PER_S and RATE_BURST.", "quotesvc/app.py")
def c09():
    rep("quotesvc/app.py", '''    srv = build_server(os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8080")))''',
        '''    limiter = TokenBucket(float(os.environ.get("RATE_PER_S", "5")), int(os.environ.get("RATE_BURST", "20")))
    srv = build_server(os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8080")), limiter=limiter)''')


@cs("C10", "clean", "clean/typing", "none",
    "Give the parsed request a TypedDict.", "quotesvc/validation.py")
def c10():
    rep("quotesvc/validation.py", "from typing import Any\n", "from typing import Any, TypedDict\n")
    rep("quotesvc/validation.py", "MAX_QUANTITY = 500\n", '''MAX_QUANTITY = 500


class QuoteRequest(TypedDict):
    weight_kg: Decimal
    zone: str
    quantity: int
    promo: str | None
''')
    rep("quotesvc/validation.py", "def parse_request(body: Any) -> dict:", "def parse_request(body: Any) -> QuoteRequest:")


@cs("C11", "clean", "clean/expected-value-change-requested", "none (expectation-changed is warn by design)",
    "Raise the world zone multiplier from 2.75 to 2.90 and update the expected prices.",
    "quotesvc/pricing.py, tests/test_pricing.py")
def c11():
    rep("quotesvc/pricing.py", '"world": Decimal("2.75")', '"world": Decimal("2.90")')
    rep("tests/test_pricing.py", '''    assert w.unit_price == D("10.73")  # 3.90 * 2.75 = 10.725 -> half up
    assert w.subtotal == D("32.19")''', '''    assert w.unit_price == D("11.31")  # 3.90 * 2.90 = 11.31
    assert w.subtotal == D("33.93")''')


def main():
    labels = []
    assert git("rev-parse", "--abbrev-ref", "HEAD").strip() == "main"
    for c in CS:
        git("checkout", "-q", "-B", f"cs/{c['id']}", "main")
        c["fn"]()
        write(".gates/task.md", f"# Task ({c['id']})\n\n{c['task']}\n\nScope: {c['scope']}\n")
        git("add", "-A")
        git("commit", "-qm", f"{c['id']}: {c['task']}")
        sha = git("rev-parse", "HEAD").strip()
        git("checkout", "-q", "main")
        labels.append({k: v for k, v in c.items() if k != "fn"} | {"branch": f"cs/{c['id']}", "commit": sha})
        print(c["id"], c["label"], c["category"], sha[:10])
    Path(sys.argv[2]).write_text(json.dumps(labels, indent=2) + "\n")


if __name__ == "__main__":
    main()
