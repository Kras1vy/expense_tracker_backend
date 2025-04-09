import secrets
from datetime import (  # Работа с текущим временем и вычислением срока действия токена
    UTC,
    datetime,
    timedelta,
)
from typing import Any  # Removed Union import as it's no longer needed

import jwt
from beanie import PydanticObjectId
from fastapi import HTTPException, status

from src.config import config
from src.models import RefreshToken


def create_access_token(data: dict[str, Any]) -> str:
    """
    🔑 Создаёт JWT access token на основе переданных данных
    """
    # Копируем данные, чтобы не изменять оригинал
    to_encode = data.copy()

    # Конвертируем PydanticObjectId в строку, если он есть
    if "sub" in to_encode and isinstance(to_encode["sub"], (PydanticObjectId, str)):
        to_encode["sub"] = str(to_encode["sub"])

    # Добавляем время истечения токена
    expire = datetime.now(UTC) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    # Кодируем данные в JWT
    return jwt.encode(
        to_encode, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM
    )  # Возвращаем сгенерированный токен (строка)


def verify_access_token(token: str) -> dict[str, Any]:
    """
    Проверка и декодирование access токена.
    Аргументы:
    - token: токен, полученный от пользователя

    Возвращает:
    - Словарь (payload), если токен валидный
    - Ошибка, если токен подделан или истёк
    """
    try:
        # 🔐 Пытаемся расшифровать токен с помощью секретного ключа
        return jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        # ❌ Если токен невалидный или истёк - возвращаем 401 Unauthorized
        # from None - скрываем оригинальный traceback, так как он не нужен клиенту
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from None


def create_refresh_token() -> tuple[str, datetime, datetime]:
    """
    Создаёт безопасный случайный refresh токен, дату создания и дату истечения.
    """
    token = secrets.token_urlsafe(64)  # 🔐 Безопасная строка, как сессионный ID
    created_at = datetime.now(UTC)
    expires_at = created_at + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS)
    return token, created_at, expires_at


async def verify_refresh_token(token: str) -> RefreshToken:
    """
    Проверяет, существует ли переданный refresh токен в базе,
    и не истёк ли его срок действия.
    Возвращает Beanie-документ, если токен валиден.
    """

    # 🔎 Ищем токен в MongoDB по значению токена
    token_doc = await RefreshToken.find_one(RefreshToken.token == token)

    # ❌ Если токен не найден — выбрасываем ошибку 401
    if not token_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # ⏳ Если токен просрочен
    if token_doc.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        await token_doc.delete()  # 💀 Удаляем просроченный токен из базы
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
        )

    # ✅ Всё в порядке — возвращаем найденный документ
    return token_doc


async def save_refresh_token_to_db(
    user_id: str, token: str, created_at: datetime, expires_at: datetime
) -> None:
    """
    Создаёт документ RefreshToken и сохраняет его в коллекции MongoDB.
    """
    refresh_token_doc = RefreshToken(
        user_id=PydanticObjectId(user_id),  # Convert string ID to PydanticObjectId
        token=token,  # Уникальный токен, безопасно сгенерированный
        created_at=created_at,  # Время создания токена
        expires_at=expires_at,  # Время, когда токен истекает
    )

    _ = await refresh_token_doc.insert()  # 🧠 Сохраняем документ в MongoDB
