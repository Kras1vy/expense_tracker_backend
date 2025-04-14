from typing import Annotated, Any, cast

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.dependencies import get_current_user
from src.models import BankTransaction, Transaction, TransactionType, User
from src.schemas.base import TransactionCreate, TransactionPublic

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_in: TransactionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> TransactionPublic:
    """
    Создать новую транзакцию (расход или доход)
    """
    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID is required")

    # Создаём объект транзакции
    transaction = Transaction(
        **transaction_in.model_dump(), user_id=PydanticObjectId(current_user.id)
    )

    _ = await transaction.insert()  # Сохраняем в MongoDB

    # Обновляем баланс пользователя
    if transaction.type == TransactionType.EXPENSE:
        current_user.balance -= transaction.amount
    else:  # income
        current_user.balance += transaction.amount

    _ = await current_user.save()

    return TransactionPublic(**transaction.model_dump())


@router.get("/")
async def get_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_type: Annotated[TransactionType | None, Query()] = None,
) -> list[TransactionPublic]:
    """
    Получить список транзакций с опциональной фильтрацией по типу
    """
    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID is required")

    # Базовый запрос для текущего пользователя
    query = Transaction.find(Transaction.user_id == current_user.id)

    # Добавляем фильтр по типу, если он указан
    if transaction_type:
        query = query.find(Transaction.type == transaction_type)

    # Получаем транзакции
    transactions = await query.to_list()

    # Преобразуем в формат ответа
    return [TransactionPublic(**transaction.model_dump()) for transaction in transactions]


@router.get("/{transaction_id}")
async def get_transaction_by_id(
    transaction_id: PydanticObjectId,
    current_user: Annotated[User, Depends(get_current_user)],
) -> TransactionPublic:
    """
    Получить транзакцию по ID
    """
    transaction = await Transaction.get(transaction_id)

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this transaction")

    return TransactionPublic(**transaction.model_dump())


@router.put("/{transaction_id}")
async def update_transaction(
    transaction_id: PydanticObjectId,
    transaction_in: TransactionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """
    Обновить транзакцию
    """
    transaction = await Transaction.get(transaction_id)

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this transaction")

    # Обновляем баланс пользователя
    if transaction.type == TransactionType.EXPENSE:
        current_user.balance += transaction.amount  # Возвращаем старую сумму
    else:  # income
        current_user.balance -= transaction.amount  # Возвращаем старую сумму

    # Применяем новую сумму
    if transaction_in.type == TransactionType.EXPENSE:
        current_user.balance -= transaction_in.amount
    else:  # income
        current_user.balance += transaction_in.amount

    _ = await current_user.save()

    # Обновляем поля транзакции
    transaction.type = transaction_in.type
    transaction.amount = transaction_in.amount
    transaction.category = transaction_in.category
    transaction.payment_method = transaction_in.payment_method
    transaction.description = transaction_in.description

    if transaction_in.date:
        transaction.date = transaction_in.date

    _ = await transaction.save()

    return {"message": "Transaction updated successfully"}


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: PydanticObjectId,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """
    Удалить транзакцию
    """
    transaction = await Transaction.get(transaction_id)

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this transaction")

    # Обновляем баланс пользователя
    if transaction.type == TransactionType.EXPENSE:
        current_user.balance += transaction.amount  # Возвращаем сумму расхода
    else:  # income
        current_user.balance -= transaction.amount  # Возвращаем сумму дохода

    _ = await current_user.save()

    # Удаляем транзакцию
    _ = await transaction.delete()

    return {"message": "Transaction deleted successfully"}


@router.get("/all")
async def get_all_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    source_filter: Annotated[str | None, Query(None, pattern="^(manual|plaid)$")] = None,
) -> list[dict[str, Any]]:
    # Ручные транзакции (у них уже есть type и category)
    manual = await Transaction.find(Transaction.user_id == current_user.id).to_list()
    manual_data = [txn.model_dump() | {"source": "manual"} for txn in manual]

    # Банковские транзакции (добавим type, source и нормализуем category)
    plaid = await BankTransaction.find(BankTransaction.user_id == current_user.id).to_list()
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

    # Объединяем
    all_txns = manual_data + plaid_data

    # Фильтрация по source
    if source_filter:
        all_txns = [txn for txn in all_txns if txn["source"] == source_filter]

    # Сортировка по дате (сначала новые)
    all_txns.sort(key=lambda x: x["date"], reverse=True)

    return all_txns
