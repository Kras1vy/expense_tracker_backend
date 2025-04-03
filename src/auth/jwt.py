import secrets
from datetime import (  # Работа с текущим временем и вычислением срока действия токена
    UTC,
    datetime,
    timedelta,
)
from typing import Any, Dict, Union  # Типизация: Dict — словарь, Union — объединение типов

from fastapi import HTTPException, status
from jose import JWTError, jwt  # Библиотека для создания и верификации JWT токенов

from ..config import config
from ..models import RefreshToken

# Устанавливаем алгоритм шифрования токена — HMAC с SHA-256
ALGORITHM = "HS256"

# Задаём время жизни access токена — 30 минут
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: Dict[str, Any], expires_delta: Union[timedelta, None] = None) -> str:
    """
    Создание access токена.
    Аргументы:
    - data: данные, которые надо зашифровать (например, {"sub": user_id})
    - expires_delta: сколько токен живёт (по умолчанию 30 минут)
    """

    # Проверяем: если ключ не установлен — выбрасываем ошибку
    if not config.SECRET_KEY:
        raise ValueError(
            "❌ SECRET_KEY is not set in your .env file!"
        )  # Без ключа нельзя генерировать токены

    to_encode = data.copy()  # Копируем, чтобы не изменять оригинальный словарь
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )  # Считаем время истечения токена
    to_encode.update({"exp": expire})  # Добавляем в токен ключ "exp" (expiration)

    # Генерируем токен с помощью секретного ключа и выбранного алгоритма
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt  # Возвращаем сгенерированный токен (строка)


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Проверка и декодирование access токена.
    Аргументы:
    - token: токен, полученный от пользователя

    Возвращает:
    - Словарь (payload), если токен валидный
    - Ошибка, если токен подделан или истёк
    """

    try:
        # Пытаемся расшифровать токен
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # Если всё хорошо — возвращаем расшифрованные данные
    except JWTError:
        # Если токен неправильный или устарел — бросаем ошибку
        raise JWTError("Could not validate credentials")


REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_refresh_token() -> tuple[str, datetime, datetime]:
    """
    Создаёт безопасный случайный refresh токен, дату создания и дату истечения.
    """
    token = secrets.token_urlsafe(64)  # 🔐 Безопасная строка, как сессионный ID
    created_at = datetime.now(UTC)
    expires_at = created_at + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
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
    if token_doc.expires_at < datetime.now(UTC):
        await token_doc.delete()  # 💀 Удаляем просроченный токен из базы
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
        )

    # ✅ Всё в порядке — возвращаем найденный документ
    return token_doc


async def save_refresh_token_to_db(
    user_id: str, token: str, created_at: datetime, expires_at: datetime
):
    """
    Создаёт документ RefreshToken и сохраняет его в коллекции MongoDB.
    """
    refresh_token_doc = RefreshToken(
        user_id=user_id,  # ID пользователя, которому принадлежит токен
        token=token,  # Уникальный токен, безопасно сгенерированный
        created_at=created_at,  # Время создания токена
        expires_at=expires_at,  # Время, когда токен истекает
    )

    await refresh_token_doc.insert()  # 🧠 Сохраняем документ в MongoD
