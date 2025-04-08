from typing import Annotated  # ✅ Современный способ аннотировать Depends

from fastapi import APIRouter, Depends, HTTPException, status  # 🚀 FastAPI-инструменты

from src.auth.dependencies import get_current_user  # 🔐 Получаем текущего пользователя
from src.models import Budget, User  # 🧠 Модель бюджета и пользователя
from src.schemas.budget import BudgetCreate, BudgetPublic, BudgetUpdate  # 📦 Схемы для работы

# ⚙️ Роутер с префиксом /budgets
router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_budget(
    budget_in: BudgetCreate,  # 🔽 Получаем данные от клиента (категория + лимит)
    current_user: Annotated[User, Depends(get_current_user)],  # 🔐 Авторизованный пользователь
) -> BudgetPublic:
    """
    ➕ Создать пользовательский бюджет по категории
    """
    # 🔍 Проверяем, существует ли уже бюджет на эту категорию
    existing = await Budget.find_one(
        Budget.user_id == str(current_user.id),
        Budget.category == budget_in.category,
    )
    if existing:
        # ⚠️ Если уже есть — бросаем 409 ошибку (конфликт)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Budget for this category already exists.",
        )

    # 🆕 Создаём новый бюджет
    budget = Budget(user_id=str(current_user.id), **budget_in.model_dump())

    # 💾 Сохраняем в базу
    await budget.insert()

    # 📤 Возвращаем клиенту публичную схему
    return BudgetPublic(**budget.model_dump())


@router.get("/")
async def get_budgets(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[BudgetPublic]:
    """
    📄 Получить все бюджеты пользователя
    """
    # 📦 Забираем все бюджеты пользователя
    budgets = await Budget.find(Budget.user_id == str(current_user.id)).to_list()

    # 🧾 Преобразуем в список публичных схем
    return [BudgetPublic(**b.model_dump()) for b in budgets]


@router.put("/{category}")
async def update_budget(
    category: str,  # 🏷 Имя категории в URL
    update: BudgetUpdate,  # 🛠 Новое значение лимита
    current_user: Annotated[User, Depends(get_current_user)],  # 🔐 Пользователь
) -> BudgetPublic:
    """
    ✏️ Обновить лимит бюджета по категории
    """
    # 🔎 Ищем бюджет по категории и пользователю
    budget = await Budget.find_one(
        Budget.user_id == str(current_user.id),
        Budget.category == category,
    )
    if not budget:
        # ❌ Если не найден — 404
        raise HTTPException(status_code=404, detail="Budget not found")

    # 💸 Обновляем лимит
    budget.limit = update.limit

    # 💾 Сохраняем
    await budget.save()

    # 📤 Возвращаем
    return BudgetPublic(**budget.model_dump())


@router.delete("/{category}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    category: str,  # 🏷 Категория в URL
    current_user: Annotated[User, Depends(get_current_user)],  # 🔐 Пользователь
) -> None:
    """
    ❌ Удалить бюджет по категории
    """
    # 🔎 Ищем бюджет
    budget = await Budget.find_one(
        Budget.user_id == str(current_user.id),
        Budget.category == category,
    )
    if not budget:
        # ❌ Не найден — 404
        raise HTTPException(status_code=404, detail="Budget not found")

    # 🧹 Удаляем
    await budget.delete()
