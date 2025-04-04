from typing import Annotated  # Новый способ аннотирования зависимостей

from fastapi import APIRouter, Depends, HTTPException, Request

from src.auth.dependencies import (
    get_current_user,  # Зависимость для получения текущего пользователя
)
from src.auth.jwt import (
    create_access_token,  # если ты уже реализовал
    create_refresh_token,
    save_refresh_token_to_db,
    verify_refresh_token,
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


@router.post("/refresh")
async def refresh_tokens(request: Request):
    """
    Обновляет access и refresh токены, если передан валидный refresh токен.
    """
    # 📥 Получаем тело запроса как JSON
    data = await request.json()
    incoming_token = data.get("refresh_token")

    if not incoming_token:
        raise HTTPException(status_code=400, detail="Refresh token required")

    # 🔍 Проверяем refresh токен
    token_doc = await verify_refresh_token(incoming_token)

    # ❌ Удаляем старый refresh токен (ротация)
    await token_doc.delete()

    # 🆕 Генерируем новый refresh токен
    new_refresh_token, created_at, expires_at = create_refresh_token()

    # 💾 Сохраняем его в базу
    await save_refresh_token_to_db(
        user_id=token_doc.user_id,
        token=new_refresh_token,
        created_at=created_at,
        expires_at=expires_at,
    )

    # 🪪 Создаём новый access токен (с payload на основе user_id)
    new_access_token = create_access_token({"sub": token_doc.user_id})

    # 📤 Отправляем оба токена клиенту
    return {"access_token": new_access_token, "refresh_token": new_refresh_token}


@router.post("/logout")
async def logout(request: Request):
    """
    Удаляет refresh токен из базы. Выход с текущей сессии.
    """
    # 📥 Получаем тело запроса
    data = await request.json()
    incoming_token = data.get("refresh_token")

    if not incoming_token:
        raise HTTPException(status_code=400, detail="Refresh token required")

    # 🔍 Проверяем токен
    token_doc = await verify_refresh_token(incoming_token)

    # 🗑 Удаляем токен (выход)
    await token_doc.delete()

    return {"detail": "Successfully logged out"}
