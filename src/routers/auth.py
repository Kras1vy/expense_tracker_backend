# Импортируем нужные зависимости от FastAPI
from typing import Annotated, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Request, status

# Импорт для хеширования паролей
from passlib.context import CryptContext

# Импорт Pydantic-схем для валидации входа и выхода
from schemas.base import GoogleLoginPayload, Token, UserCreate, UserLogin, UserPublic
from src.auth.dependencies import get_current_user
from src.auth.google_oauth import TokenResponse, handle_google_login

# Импорт функции создания JWT токена
from src.auth.jwt import (
    create_access_token,  # если ты уже реализовал
    create_refresh_token,
    save_refresh_token_to_db,
    verify_refresh_token,
)

# Импорт Beanie модели пользователя (работа с MongoDB)
from src.models import RefreshToken, User

# Создаём роутер для группы маршрутов "/auth"
router = APIRouter(prefix="/auth", tags=["Auth"])

# Создаём объект для хеширования и проверки паролей с помощью bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Хешируем пароль при регистрации
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# Эндпоинт регистрации пользователя
@router.post("/register")  # Возвращает публичные данные пользователя
async def register(
    user_in: UserCreate,
) -> UserPublic:  # user_in — входящие данные (email + пароль)
    # Проверяем, существует ли пользователь с таким email
    existing_user = await User.find_one(User.email == user_in.email)
    if existing_user:
        # Если есть — выбрасываем исключение
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Хешируем пароль перед сохранением
    hashed = hash_password(user_in.password)

    # Создаём нового пользователя и сохраняем в базу
    user = User(
        email=user_in.email,
        hashed_password=hashed,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        birth_date=user_in.birth_date,
    )
    await user.insert()

    # Если по какой-то причине user.id не создался — ошибка
    if not user.id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user"
        )

    # Возвращаем публичные данные пользователя (без пароля)
    return UserPublic(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        birth_date=user.birth_date,
    )


# Эндпоинт логина пользователя
@router.post("/login", response_model=Token)
async def login(user_in: UserLogin):
    user = await User.find_one(User.email == user_in.email)
    if not user or not pwd_context.verify(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token, created_at, expires_at = create_refresh_token()

    await save_refresh_token_to_db(
        user_id=str(user.id),
        token=refresh_token,
        created_at=created_at,
        expires_at=expires_at,
    )

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/google")
async def google_login(payload: GoogleLoginPayload) -> TokenResponse:
    """
    🔐 Логин через Google:
    Принимает id_token от клиента, проверяет его через Google,
    создаёт юзера (если нужно) и возвращает токены.
    """
    # 📥 Получаем id_token из тела запроса
    id_token_str = payload.id_token

    # ❌ Если токена нет — ошибка
    if not id_token_str:
        raise HTTPException(status_code=400, detail="id_token required")

    # ✅ Вызываем функцию, которая делает всю магию
    return await handle_google_login(id_token_str)


@router.post("/refresh")
async def refresh_tokens(request: Request) -> dict[str, str]:
    """
    🔄 Обновление токенов
    """
    data = await request.json()
    incoming_token = data.get("refresh_token")

    if not incoming_token:
        raise HTTPException(status_code=400, detail="Refresh token required")

    # Проверяем refresh токен
    token_doc = await verify_refresh_token(incoming_token)

    # Удаляем старый refresh токен
    await token_doc.delete()

    # Генерируем новый refresh токен
    new_refresh_token, created_at, expires_at = create_refresh_token()

    # Сохраняем новый refresh токен
    await save_refresh_token_to_db(
        user_id=str(token_doc.user_id),
        token=new_refresh_token,
        created_at=created_at,
        expires_at=expires_at,
    )

    # Создаём новый access токен
    new_access_token = create_access_token({"sub": token_doc.user_id})

    return {"access_token": new_access_token, "refresh_token": new_refresh_token}


@router.post("/logout")
async def logout(request: Request) -> dict[str, str]:
    """
    🚪 Выход из системы
    """
    data = await request.json()
    incoming_token = data.get("refresh_token")

    if not incoming_token:
        raise HTTPException(status_code=400, detail="Refresh token required")

    # Проверяем токен
    token_doc = await verify_refresh_token(incoming_token)

    # Удаляем токен
    await token_doc.delete()

    return {"detail": "Successfully logged out"}


@router.post("/logout-all")
async def logout_all(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """
    🚪 Выход со всех устройств
    """
    if not current_user or not current_user.id:
        raise HTTPException(status_code=401, detail="Invalid user")

    # Удаляем все refresh токены пользователя
    await RefreshToken.find(RefreshToken.user_id == current_user.id).delete()

    return {"detail": "Logged out from all devices"}
