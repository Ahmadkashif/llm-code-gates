from decimal import Decimal as D

import pytest

from quotesvc.validation import ValidationError, parse_request


def test_valid_request_is_normalised():
    r = parse_request({"weight_kg": 1.5, "zone": "eu", "quantity": 3, "promo": "welcome10"})
    assert r == {"weight_kg": D("1.5"), "zone": "eu", "quantity": 3, "promo": "WELCOME10"}


def test_defaults():
    assert parse_request({"weight_kg": "2", "zone": "domestic"})["quantity"] == 1


@pytest.mark.parametrize("body,field", [
    ([], "body"),
    ({"zone": "eu"}, "weight_kg"),
    ({"weight_kg": "abc", "zone": "eu"}, "weight_kg"),
    ({"weight_kg": 0, "zone": "eu"}, "weight_kg"),
    ({"weight_kg": 31, "zone": "eu"}, "weight_kg"),
    ({"weight_kg": "NaN", "zone": "eu"}, "weight_kg"),
    ({"weight_kg": 1, "zone": "moon"}, "zone"),
    ({"weight_kg": 1, "zone": "eu", "quantity": 0}, "quantity"),
    ({"weight_kg": 1, "zone": "eu", "quantity": True}, "quantity"),
    ({"weight_kg": 1, "zone": "eu", "quantity": 501}, "quantity"),
    ({"weight_kg": 1, "zone": "eu", "promo": "x" * 33}, "promo"),
])
def test_invalid_requests(body, field):
    with pytest.raises(ValidationError) as e:
        parse_request(body)
    assert e.value.field == field
