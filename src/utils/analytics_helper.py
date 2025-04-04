from decimal import ROUND_HALF_UP, Decimal


def round_decimal(value: Decimal) -> Decimal:
    """Округление Decimal до 2 знаков после запятой"""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_percent(amount: Decimal, total: Decimal) -> Decimal:
    """Расчет процента от общей суммы"""
    if total == Decimal("0"):
        return Decimal("0")
    return round_decimal((amount / total) * Decimal("100"))
