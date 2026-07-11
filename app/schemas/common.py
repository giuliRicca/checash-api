from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANT = Decimal("0.01")
RATE_QUANT = Decimal("0.000001")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def quantize_rate(value: Decimal) -> Decimal:
    return value.quantize(RATE_QUANT, rounding=ROUND_HALF_UP)
