from decimal import Decimal
from typing import Any


def convert_decimal128(value: Any) -> Decimal:
    """
    Конвертирует MongoDB Decimal128 в Python Decimal.

    Args:
        value: Значение для конвертации (Decimal128 или другой тип)

    Returns:
        Decimal: Сконвертированное значение
    """
    if hasattr(value, "to_decimal"):
        return value.to_decimal()
    return value
