from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import get_current_user
from src.models import Category, Transaction, User
from src.schemas.category_schemas import CategoryCreate, CategoryPublic, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/")
async def get_categories(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[CategoryPublic]:
    """
    🔍 Получить все категории (глобальные + кастомные юзера)
    """
    categories = await Category.find(
        {"$or": [{"user_id": current_user.id}, {"user_id": None}]}
    ).to_list()

    return [CategoryPublic.model_validate(cat.model_dump()) for cat in categories]
    # ✅ .model_validate() — современная альтернатива model_dump
    # Возвращаем список кастомных и дефолтных категорий


import re


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_category(
    category_in: CategoryCreate, current_user: Annotated[User, Depends(get_current_user)]
) -> CategoryPublic:
    """
    ➕ Создать кастомную категорию (без дублей, игнорируя регистр и пробелы)
    """
    # 🧼 Убираем пробелы вокруг имени
    clean_name = category_in.name.strip()

    # ⛔ Проверка на дублирование (без учёта регистра и с учётом пробелов)
    existing = await Category.find_one(
        {
            "user_id": current_user.id,
            "name": {"$regex": f"^{re.escape(clean_name)}$", "$options": "i"},
        }
    )

    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists.")

    # ✅ Создание новой категории
    category = Category(
        name=clean_name,
        icon=category_in.icon,
        user_id=PydanticObjectId(current_user.id),
        color=category_in.color,
        is_default=False,
    )
    _ = await category.insert()

    return CategoryPublic.model_validate(category.model_dump())


@router.delete("/{category_id}")
async def delete_category(
    category_id: PydanticObjectId, current_user: Annotated[User, Depends(get_current_user)]
) -> dict[str, str]:
    """
    ❌ Удалить свою кастомную категорию и заменить её в транзакциях на 'Uncategorized'
    """
    category = await Category.get(category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You are not authorized to delete this category"
        )

    # 👇 Обновляем все транзакции, где использовалась эта категория
    _ = await Transaction.find(
        Transaction.user_id == current_user.id, Transaction.category == category.name
    ).update_many({"$set": {"category": "Uncategorized"}})

    # �� Удаляем категорию
    _ = await category.delete()

    return {"detail": "Category deleted successfully"}


@router.put("/{category_id}")
async def update_category(
    category_id: PydanticObjectId,
    category_in: CategoryUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CategoryPublic:
    """
    ✏️ Обновление категории по ID
    """
    # Получаем категорию по ID
    category = await Category.get(category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this category")

    # Обновляем переданные поля
    if category_in.name is not None:
        category.name = category_in.name
    if category_in.color is not None:
        category.color = category_in.color
    if category_in.icon is not None:
        category.icon = category_in.icon

    _ = await category.save()

    return CategoryPublic.model_validate(category.model_dump())


@router.get("/{category_id}")
async def get_category_by_id(
    category_id: PydanticObjectId,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CategoryPublic:
    """
    🔍 Получить категорию по ID (современный стиль Beanie + FastAPI)
    """
    category = await Category.get(category_id)

    if not category or category.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    return CategoryPublic(**category.model_dump())
