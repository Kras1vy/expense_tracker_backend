from datetime import (  # Работа с текущим временем и вычислением срока действия токена
    UTC,
    datetime,
    timedelta,
)
from typing import Any, Dict, Union  # Типизация: Dict — словарь, Union — объединение типов

from jose import JWTError, jwt  # Библиотека для создания и верификации JWT токенов

from ..config import config

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
