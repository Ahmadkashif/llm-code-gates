"""Validate and normalise a quote request body."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .pricing import MAX_WEIGHT_KG, ZONE_MULTIPLIER

MAX_QUANTITY = 500


class ValidationError(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(f"{field}: {message}")
        self.field = field


def parse_request(body: Any) -> dict:
    if not isinstance(body, dict):
        raise ValidationError("body", "must be a JSON object")
    try:
        weight = Decimal(str(body.get("weight_kg")))
    except InvalidOperation:
        raise ValidationError("weight_kg", "must be a number") from None
    if not weight.is_finite() or weight <= 0 or weight > MAX_WEIGHT_KG:
        raise ValidationError("weight_kg", f"must be in (0, {MAX_WEIGHT_KG}]")
    zone = body.get("zone")
    if zone not in ZONE_MULTIPLIER:
        raise ValidationError("zone", f"must be one of {sorted(ZONE_MULTIPLIER)}")
    quantity = body.get("quantity", 1)
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= MAX_QUANTITY:
        raise ValidationError("quantity", f"must be an integer in [1, {MAX_QUANTITY}]")
    promo = body.get("promo")
    if promo is not None and (not isinstance(promo, str) or len(promo) > 32):
        raise ValidationError("promo", "must be a short string")
    return {"weight_kg": weight, "zone": zone, "quantity": quantity, "promo": promo.upper() if promo else None}
