from decimal import Decimal

from beanie import PydanticObjectId

from src.models import BankTransaction, Transaction, User


async def recalculate_user_balance(user_id: PydanticObjectId) -> None:
    user = await User.get(user_id)
    if not user:
        return

    balance = Decimal("0")

    # Ручные транзакции
    manual_txns = await Transaction.find(Transaction.user_id == user_id).to_list()
    for txn in manual_txns:
        if txn.type == "income":
            balance += txn.amount
        else:
            balance -= txn.amount

    # Банковские транзакции
    bank_txns = await BankTransaction.find(BankTransaction.user_id == user_id).to_list()
    for txn in bank_txns:
        # Plaid доходы — отрицательные по amount
        amount = Decimal(str(txn.amount))
        if txn.amount < 0:
            balance += abs(amount)
        else:
            balance -= amount

    user.balance = balance
    _ = await user.save()
