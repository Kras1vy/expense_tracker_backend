# Импортируем нужные зависимости от FastAPI
from fastapi import APIRouter, HTTPException, status

# Импорт для хеширования паролей
from passlib.context import CryptContext

# Импорт функции создания JWT токена
from src.auth.jwt import (
    create_access_token,  # если ты уже реализовал
    create_refresh_token,
    save_refresh_token_to_db,
)

# Импорт Beanie модели пользователя (работа с MongoDB)
from src.models import User

# Импорт Pydantic-схем для валидации входа и выхода
from src.schemas import Token, UserCreate, UserLogin, UserPublic

# Создаём роутер для группы маршрутов "/auth"
router = APIRouter(prefix="/auth", tags=["Auth"])

# Создаём объект для хеширования и проверки паролей с помощью bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Хешируем пароль при регистрации
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# Эндпоинт регистрации пользователя
@router.post("/register", response_model=UserPublic)  # Возвращает публичные данные пользователя
async def register(user_in: UserCreate):  # user_in — входящие данные (email + пароль)
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
    user = User(email=user_in.email, hashed_password=hashed)
    await user.insert()

    # Если по какой-то причине user.id не создался — ошибка
    if not user.id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user"
        )

    # Возвращаем публичные данные пользователя (без пароля)
    return UserPublic(id=user.id, email=user.email)


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
