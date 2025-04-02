from typing import Annotated  # Новый способ аннотирования зависимостей

from beanie import PydanticObjectId  # Для работы с MongoDB ID (если понадобится)
from fastapi import APIRouter, Depends, HTTPException, status  # Инструменты FastAPI

from src.auth.dependencies import (
    get_current_user,  # Зависимость для получения текущего пользователя
)
from src.models import User  # Модель пользователя

# Создаём роутер с префиксом /account и тегом Protected (будет отображаться в Swagger)
router = APIRouter(prefix="/account", tags=["Protected"])


@router.get("/me")  # Защищённый маршрут: получить текущего пользователя
async def get_me(
    current_user: Annotated[
        User, Depends(get_current_user)
    ],  # Используем Annotated вместо = Depends(...)
) -> dict[str, str]:
    return {
        "id": str(current_user.id),  # Возвращаем ID пользователя
        "email": current_user.email,  # Возвращаем его email
    }


@router.delete("/delete")  # Защищённый маршрут: удалить текущего пользователя
async def delete_account(
    current_user: Annotated[User, Depends(get_current_user)],  # Также защищён с помощью токена
) -> dict[str, str]:
    await current_user.delete()  # Удаляем из базы
    return {"message": "Account deleted successfully"}  # Ответ клиенту
