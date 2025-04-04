from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import get_current_user
from src.models import Category, User
from src.schemas.category_schemas import CategoryCreate, CategoryPublic

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=list[CategoryPublic])
async def get_categories(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[CategoryPublic]:
    """
    🔍 Получить все категории (глобальные + кастомные юзера)
    """
    categories = await Category.find(
        {"$or": [{"user_id": current_user.id}, {"user_id": None}]}
    ).to_list()

    return [CategoryPublic.model_validate(cat) for cat in categories]
    # ✅ .model_validate() — современная альтернатива model_dump
    # Возвращаем список кастомных и дефолтных категорий


@router.post("/", response_model=CategoryPublic, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_in: CategoryCreate, current_user: Annotated[User, Depends(get_current_user)]
) -> CategoryPublic:
    """
    ➕ Создать кастомную категорию
    """
    category = Category(
        name=category_in.name,
        icon=category_in.icon,
        user_id=current_user.id,
        is_default=False,
    )
    await category.insert()

    return CategoryPublic.model_validate(category)


@router.delete("/{category_id}")
async def delete_category(
    category_id: PydanticObjectId, current_user: Annotated[User, Depends(get_current_user)]
) -> dict[str, str]:
    """
    ❌ Удалить свою кастомную категорию
    """
    category = await Category.get(category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You are not authorized to delete this category"
        )

    await category.delete()
    return {"detail": "Category deleted successfully"}
