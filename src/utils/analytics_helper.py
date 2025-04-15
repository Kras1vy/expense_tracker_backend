from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from beanie import PydanticObjectId

from src.models import BankTransaction, Transaction, TransactionType


def round_decimal(value: Decimal) -> Decimal:
    """Округление Decimal до 2 знаков после запятой"""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_percent(amount: Decimal, total: Decimal) -> Decimal:
    """Расчет процента от общей суммы"""
    if total == Decimal("0"):
        return Decimal("0")
    return round_decimal((amount / total) * Decimal("100"))


def to_decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def sum_amounts(transactions: list[dict[str, Any]]) -> Decimal:
    return sum((to_decimal(t["amount"]) for t in transactions), start=Decimal("0"))


async def get_paginated_transactions_for_user(
    user_id: PydanticObjectId,
    source_filter: Literal["manual", "plaid"] | None = None,
    transaction_type: TransactionType | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    manual_data: list[dict[str, Any]] = []
    plaid_data: list[dict[str, Any]] = []

    if source_filter == "manual":
        base_query = Transaction.find(Transaction.user_id == user_id)
        if transaction_type:
            base_query = base_query.find(Transaction.type == transaction_type)

        total = await base_query.count()
        manual = await base_query.sort("-date").skip(offset).limit(limit).to_list()
        manual_data = [txn.model_dump() | {"source": "manual"} for txn in manual]

        return {
            "items": manual_data,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_next": offset + len(manual_data) < total,
        }

    if source_filter == "plaid":
        base_query = BankTransaction.find(BankTransaction.user_id == user_id)
        plaid_all = await base_query.sort("-date").to_list()

        plaid_data_filtered = [
            {
                **txn.model_dump(),
                "type": "income" if txn.amount < 0 else "expense",
                "category": ", ".join(txn.category) if txn.category else None,
                "source": "plaid",
            }
            for txn in plaid_all
            if transaction_type is None
            or ("income" if txn.amount < 0 else "expense") == transaction_type
        ]

        total = len(plaid_data_filtered)
        paginated = plaid_data_filtered[offset : offset + limit]

        return {
            "items": paginated,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_next": offset + len(paginated) < total,
        }

    # If no source filter or both sources
    manual = await Transaction.find(Transaction.user_id == user_id).to_list()
    plaid = await BankTransaction.find(BankTransaction.user_id == user_id).to_list()

    manual_data = [
        txn.model_dump() | {"source": "manual"}
        for txn in manual
        if transaction_type is None or txn.type == transaction_type
    ]

    plaid_data = [
        {
            **txn.model_dump(),
            "type": "income" if txn.amount < 0 else "expense",
            "category": ", ".join(txn.category) if txn.category else None,
            "source": "plaid",
        }
        for txn in plaid
        if transaction_type is None
        or ("income" if txn.amount < 0 else "expense") == transaction_type
    ]

    all_txns = manual_data + plaid_data
    all_txns.sort(key=lambda x: x["date"], reverse=True)
    total = len(all_txns)
    paginated = all_txns[offset : offset + limit]

    return {
        "items": paginated,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_next": offset + len(paginated) < total,
    }


async def get_all_transactions_for_user(user_id: PydanticObjectId) -> list[dict[str, Any]]:
    """
    Возвращает все транзакции пользователя без пагинации (нужно для аналитики).
    """
    result = await get_paginated_transactions_for_user(user_id=user_id, limit=10_000_000)
    return result["items"]
