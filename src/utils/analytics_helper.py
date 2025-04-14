import decimal
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, cast

from beanie import PydanticObjectId

from src.models import BankTransaction, Transaction


def round_decimal(value: Decimal) -> Decimal:
    """Округление Decimal до 2 знаков после запятой"""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_percent(amount: Decimal, total: Decimal) -> Decimal:
    """Расчет процента от общей суммы"""
    if total == Decimal("0"):
        return Decimal("0")
    return round_decimal((amount / total) * Decimal("100"))


async def get_all_transactions_for_user(user_id: PydanticObjectId) -> list[dict[str, Any]]:
    manual = await Transaction.find(Transaction.user_id == user_id).to_list()
    manual_data = [txn.model_dump() | {"source": "manual"} for txn in manual]

    plaid = await BankTransaction.find(BankTransaction.user_id == user_id).to_list()
    plaid_data = []
    for txn in plaid:
        data = txn.model_dump()
        txn_type = "income" if data["amount"] < 0 else "expense"
        category = (
            ", ".join(cast("list[str]", data["category"]))
            if isinstance(data["category"], list)
            else None
        )

        plaid_data.append(
            {
                **data,
                "type": txn_type,
                "category": category,
                "source": "plaid",
            }
        )

    all_txns = manual_data + plaid_data
    all_txns.sort(key=lambda x: x["date"], reverse=True)
    return all_txns


def to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(cast("float", value)))
    except (ValueError, TypeError, decimal.InvalidOperation):
        return Decimal("0")


def sum_amounts(transactions: Sequence[dict[str, Any]]) -> Decimal:
    amounts = [to_decimal(t["amount"]) for t in transactions if "amount" in t]
    return sum(amounts, start=Decimal("0"))
