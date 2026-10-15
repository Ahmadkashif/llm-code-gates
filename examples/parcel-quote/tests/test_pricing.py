from decimal import Decimal as D

import pytest
from hypothesis import given
from hypothesis import strategies as st

from quotesvc.pricing import PricingError, band_price, quantity_discount, quote


def test_band_boundaries_are_inclusive():
    assert band_price(D("0.5")) == D("3.90")
    assert band_price(D("0.51")) == D("5.50")
    assert band_price(D("2")) == D("5.50")
    assert band_price(D("30")) == D("19.00")


def test_band_rejects_out_of_range():
    with pytest.raises(PricingError):
        band_price(D("0"))
    with pytest.raises(PricingError):
        band_price(D("30.01"))


def test_quantity_discount_thresholds():
    assert quantity_discount(9) == D("0")
    assert quantity_discount(10) == D("0.05")
    assert quantity_discount(49) == D("0.05")
    assert quantity_discount(50) == D("0.12")


def test_quote_zone_and_rounding():
    q = quote(D("1"), "eu")
    assert q.unit_price == D("8.80")
    assert q.total == D("8.80")
    w = quote(D("0.3"), "world", 3)
    assert w.unit_price == D("10.73")  # 3.90 * 2.75 = 10.725 -> half up
    assert w.subtotal == D("32.19")


def test_quote_promo_does_not_stack():
    q = quote(D("5"), "domestic", 10, "WELCOME10")
    assert q.discount == D("9.80")
    assert q.total == D("88.20")
    with pytest.raises(PricingError):
        quote(D("5"), "domestic", 1, "NOPE")


def test_quote_rejects_bad_zone_and_quantity():
    with pytest.raises(PricingError):
        quote(D("1"), "mars")
    with pytest.raises(PricingError):
        quote(D("1"), "eu", 0)


@given(st.decimals(min_value=D("0.01"), max_value=D("29.99"), places=2), st.sampled_from(["domestic", "eu", "world"]))
def test_price_is_monotonic_in_weight(w, zone):
    assert quote(w, zone).total <= quote(w + D("0.01"), zone).total
