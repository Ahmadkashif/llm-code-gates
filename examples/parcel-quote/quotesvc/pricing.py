"""Quote pricing: weight bands, zone multipliers, quantity and promo discounts. Money is Decimal, rounded to cents."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# (upper weight bound in kg, inclusive) -> base price per parcel
WEIGHT_BANDS: list[tuple[Decimal, Decimal]] = [
    (Decimal("0.5"), Decimal("3.90")),
    (Decimal("2"), Decimal("5.50")),
    (Decimal("10"), Decimal("9.80")),
    (Decimal("30"), Decimal("19.00")),
]
ZONE_MULTIPLIER = {"domestic": Decimal("1.00"), "eu": Decimal("1.60"), "world": Decimal("2.75")}
PROMO_CODES = {"WELCOME10": Decimal("0.10"), "BULK5": Decimal("0.05")}
MAX_WEIGHT_KG = WEIGHT_BANDS[-1][0]
CENT = Decimal("0.01")


class PricingError(ValueError):
    pass


@dataclass(frozen=True)
class Quote:
    unit_price: Decimal
    quantity: int
    subtotal: Decimal
    discount: Decimal
    total: Decimal


def band_price(weight_kg: Decimal) -> Decimal:
    """Base price for one parcel of the given weight (bands are inclusive at the top)."""
    if weight_kg <= 0:
        raise PricingError("weight must be positive")
    for upper, price in WEIGHT_BANDS:
        if weight_kg <= upper:
            return price
    raise PricingError(f"weight above {MAX_WEIGHT_KG} kg")


def quantity_discount(quantity: int) -> Decimal:
    """Fractional discount for multi-parcel orders: 10+ parcels 5%, 50+ parcels 12%."""
    if quantity >= 50:
        return Decimal("0.12")
    if quantity >= 10:
        return Decimal("0.05")
    return Decimal("0")


def quote(weight_kg: Decimal, zone: str, quantity: int = 1, promo: str | None = None) -> Quote:
    if zone not in ZONE_MULTIPLIER:
        raise PricingError(f"unknown zone {zone!r}")
    if quantity < 1:
        raise PricingError("quantity must be at least 1")
    unit = (band_price(weight_kg) * ZONE_MULTIPLIER[zone]).quantize(CENT, ROUND_HALF_UP)
    subtotal = unit * quantity
    rate = quantity_discount(quantity)
    if promo is not None:
        if promo not in PROMO_CODES:
            raise PricingError("unknown promo code")
        rate = max(rate, PROMO_CODES[promo])  # discounts do not stack: the larger one wins
    discount = (subtotal * rate).quantize(CENT, ROUND_HALF_UP)
    return Quote(unit, quantity, subtotal, discount, subtotal - discount)
