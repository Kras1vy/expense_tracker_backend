from datetime import UTC, datetime
from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user
from src.models import Income, User
from src.schemas.income import IncomeCreate, IncomeResponse

router = APIRouter(prefix="/income", tags=["Income"])


@router.post("/")
async def create_income(
    income_data: IncomeCreate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> IncomeResponse:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID is required")

    income = Income(
        user_id=current_user.id,
        amount=income_data.amount,
        category=income_data.category,
        source=income_data.source,
        date=datetime.now(UTC),
    )
    await income.insert()

    # Обновляем баланс пользователя
    current_user.balance += income.amount
    await current_user.save()

    return IncomeResponse(
        id=str(income.id),
        amount=income.amount,
        category=income.category,
        source=income.source,
        date=income.date,
    )


@router.get("/")
async def get_incomes(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[IncomeResponse]:
    incomes = await Income.find(Income.user_id == current_user.id).to_list()
    return [
        IncomeResponse(
            id=str(income.id),
            amount=income.amount,
            category=income.category,
            source=income.source,
            date=income.date,
        )
        for income in incomes
    ]


@router.get("/{income_id}")
async def get_income(
    income_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> IncomeResponse:
    income = await Income.get(PydanticObjectId(income_id))
    if not income or income.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Income not found")
    return IncomeResponse(
        id=str(income.id),
        amount=income.amount,
        category=income.category,
        source=income.source,
        date=income.date,
    )


@router.put("/{income_id}")
async def update_income(
    income_id: str,
    income_data: IncomeCreate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> IncomeResponse:
    income = await Income.get(PydanticObjectId(income_id))
    if not income or income.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Income not found")

    # Обновляем баланс пользователя
    current_user.balance -= income.amount  # Убираем старую сумму
    current_user.balance += income_data.amount  # Добавляем новую сумму
    await current_user.save()

    # Обновляем доход
    income.amount = income_data.amount
    income.category = income_data.category
    income.source = income_data.source
    await income.save()

    return IncomeResponse(
        id=str(income.id),
        amount=income.amount,
        category=income.category,
        source=income.source,
        date=income.date,
    )


@router.delete("/{income_id}")
async def delete_income(
    income_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    income = await Income.get(PydanticObjectId(income_id))
    if not income or income.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Income not found")

    # Обновляем баланс пользователя
    current_user.balance -= income.amount
    await current_user.save()

    # Удаляем доход
    await income.delete()
    return {"message": "Income deleted successfully"}
