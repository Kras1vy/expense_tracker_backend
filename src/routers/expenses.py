from decimal import Decimal
from typing import Annotated  # Для использования аннотаций зависимостей

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status  # FastAPI роутинг и утилиты

from src.auth.dependencies import get_current_user  # Зависимость для аутентификации
from src.models import Expense, User  # Модель расхода и пользователь
from src.schemas.base import ExpenseCreate, ExpensePublic  # Схемы для запроса и ответа

router = APIRouter(prefix="/expenses", tags=["Expenses"])  # Создаём роутер для /expenses


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_in: ExpenseCreate,
    current_user: Annotated[User, Depends(get_current_user)],  # Получаем текущего пользователя
) -> ExpensePublic:  # Возвращаем объект расхода в формате публичной схемы
    if not current_user.id:
        raise ValueError("User ID is required")

    # Создаём объект расхода, добавляя ID текущего пользователя
    expense = Expense(**expense_in.model_dump(), user_id=PydanticObjectId(current_user.id))

    await expense.insert()  # Сохраняем в MongoDB

    # Обновляем баланс пользователя
    current_user.balance -= expense.amount
    await current_user.save()

    return ExpensePublic(**expense.model_dump())  # Возвращаем клиенту данные расхода


@router.get(
    "/",
)  # Эндпоинт GET /expenses, возвращает список расходов
async def get_expenses(
    current_user: Annotated[User, Depends(get_current_user)],  # Получаем текущего пользователя
) -> list[ExpensePublic]:  # Возвращаем список расходов в формате схемы
    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID is required")

    # Получаем из базы все расходы, которые принадлежат текущему пользователю
    expenses = await Expense.find(Expense.user_id == current_user.id).to_list()

    # Преобразуем каждый объект в формат публичной схемы
    return [
        ExpensePublic(
            id=expense.id if expense.id else PydanticObjectId(),
            amount=Decimal(str(expense.amount)),
            category=expense.category,
            payment_method=expense.payment_method,
            date=expense.date,
            description=expense.description,
            user_id=expense.user_id,
        )
        for expense in expenses
    ]


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: PydanticObjectId,  # id расхода, который хотим удалить
    current_user: Annotated[
        User, Depends(get_current_user)
    ],  # Получаем авторизованного пользователя
) -> dict[str, str]:
    # Пытаемся найти расход по ID
    expense = await Expense.get(expense_id)

    # Если не нашли — кидаем 404
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Проверяем: владелец ли текущий пользователь
    if expense.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this expense")

    # Обновляем баланс пользователя
    current_user.balance += expense.amount  # Возвращаем сумму расхода
    await current_user.save()

    # Удаляем
    await expense.delete()

    return {"message": "Expense deleted successfully"}


@router.put("/{expense_id}")
async def update_expense(
    expense_id: PydanticObjectId,  # 1️⃣ ID расхода в URL
    expense_in: ExpenseCreate,  # 2️⃣ Новые данные из тела запроса
    current_user: Annotated[User, Depends(get_current_user)],  # Защищённый эндпоинт
) -> dict[str, str]:
    # Пытаемся найти расход по ID
    expense = await Expense.get(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Проверяем, что этот расход принадлежит текущему пользователю
    if expense.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this expense")

    # Обновляем баланс пользователя
    current_user.balance += expense.amount  # Возвращаем старую сумму
    current_user.balance -= expense_in.amount  # Вычитаем новую сумму
    await current_user.save()

    # Обновляем поля
    expense.description = expense_in.description
    expense.amount = expense_in.amount
    expense.category = expense_in.category
    expense.payment_method = expense_in.payment_method
    if expense_in.date:
        expense.date = expense_in.date

    await expense.save()  # Сохраняем в базу

    return {"message": "Expense updated successfully"}


@router.get("/{expense_id}")  # Эндпоинт: GET /expenses/123
async def get_expense_by_id(
    expense_id: PydanticObjectId,  # 🆔 ID расхода передаётся через URL
    current_user: Annotated[
        User, Depends(get_current_user)
    ],  # 🔐 Авторизация: получаем текущего пользователя
) -> ExpensePublic:
    expense = await Expense.get(expense_id)  # Пытаемся найти расход в базе
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")  # ❌ Если не найден

    if (
        expense.user_id != current_user.id
    ):  # 🛡️ Проверка: этот расход принадлежит текущему пользователю?
        raise HTTPException(status_code=403, detail="Not authorized to access this expense")

    return ExpensePublic(**expense.model_dump())  # ✅ Возвращаем найденный расход
