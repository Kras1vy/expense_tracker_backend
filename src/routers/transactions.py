from typing import Annotated, Any, Literal

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.dependencies import get_current_user
from src.models import Transaction, TransactionType, User
from src.schemas.base import PaginatedTransactionsResponse, TransactionCreate, TransactionPublic
from src.utils.analytics_helper import get_paginated_transactions_for_user

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


@router.get(
    "/all",
)
async def get_all_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    source_filter: Annotated[Literal["manual", "plaid"] | None, Query] = None,
    transaction_type: Annotated[TransactionType | None, Query] = None,
    limit: Annotated[int, Query] = 20,
    offset: Annotated[int, Query] = 0,
) -> PaginatedTransactionsResponse:
    """
    🔄 Получить все транзакции (ручные и банковские) с пагинацией и фильтрами:
    - по source (manual / plaid)
    - по типу транзакции (income / expense)
    """
    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID is missing")

    result = await get_paginated_transactions_for_user(
        user_id=current_user.id,
        source_filter=source_filter,
        transaction_type=transaction_type,
        limit=limit,
        offset=offset,
    )
    return PaginatedTransactionsResponse(**result)


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
