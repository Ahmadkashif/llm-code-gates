from decimal import Decimal as D

from quotesvc.store import QuoteStore


def test_roundtrip_and_count():
    s = QuoteStore()
    qid = s.save("eu", 2, D("17.60"))
    assert s.get(qid) == {"id": qid, "zone": "eu", "quantity": 2, "total": "17.60"}
    assert s.get("0" * 32) is None
    assert s.count() == 1


def test_lookup_is_not_injectable():
    s = QuoteStore()
    s.save("eu", 1, D("1"))
    assert s.get("x' OR '1'='1") is None
