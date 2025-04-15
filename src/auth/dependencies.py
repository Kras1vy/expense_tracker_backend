# Annotated нужен для объявления зависимостей (здесь — токен из запроса)
from typing import Annotated

# Импорт зависимостей из FastAPI
from fastapi import Depends, HTTPException, status

# Специальный класс, который позволяет получать токен из заголовка Authorization
from fastapi.security import OAuth2PasswordBearer

# JWTError — ошибка, которую выбрасывает библиотека при проблемах с токеном
from jose import JWTError

# Импорт функций для обработки ошибок
from src.auth.exceptions import raise_unauthorized_error

# Импорт нашей функции для верификации токена
from src.auth.jwt import verify_access_token

# Импорт модели пользователя из базы (Beanie модель)
from src.models import User

# Создаём схему авторизации — FastAPI будет искать токен в заголовке Authorization: Bearer <токен>
# И передавать его в зависимость
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Эта функция будет использоваться в защищённых эндпоинтах для получения текущего пользователя
# Она принимает токен как зависимость и возвращает объект User, если токен валидный
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    try:
        # Раскодируем токен и получаем payload (например: {"sub": "user_id"})
        payload = verify_access_token(token)

        # Получаем user_id из payload
        user_id = payload.get("sub")

        # Если ID нет в payload, значит токен невалидный
        if user_id is None:
            raise_unauthorized_error("Invalid token: user ID not found")

        # Ищем пользователя по ID в базе данных
        user = await User.get(user_id)

        # Если пользователь не найден — значит токен "указал" на несуществующего
        if user is None:
            raise_unauthorized_error("User not found")

    except JWTError:
        raise_unauthorized_error("Could not validate credentials")
    else:
        return user


def validate_google_names(given_name: str | None, family_name: str | None) -> None:
    """Проверяет наличие имени и фамилии в профиле Google."""
    if not given_name or not family_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google profile must include first and last name",
        )
