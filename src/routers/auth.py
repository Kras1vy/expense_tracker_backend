# Импортируем нужные зависимости от FastAPI
from fastapi import APIRouter, Depends, HTTPException, status

# Импорт формы логина (не используем сейчас, но пригодится позже)
from fastapi.security import OAuth2PasswordRequestForm

# Импорт для хеширования паролей
from passlib.context import CryptContext

# Импорт функции создания JWT токена
from ..auth.jwt import create_access_token

# Импорт Beanie модели пользователя (работа с MongoDB)
from ..models import User

# Импорт Pydantic-схем для валидации входа и выхода
from ..schemas import Token, UserCreate, UserLogin, UserPublic

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
@router.post("/login", response_model=Token)  # Возвращает access_token
async def login(user_in: UserLogin):  # Входные данные: email и пароль
    # Ищем пользователя по email
    user = await User.find_one(User.email == user_in.email)

    # Если пользователь не найден или пароль не совпадает
    if not user or not pwd_context.verify(user_in.password, user.hashed_password):
        # Выбрасываем ошибку авторизации
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Создаём JWT токен с user_id (в payload → sub)
    access_token = create_access_token({"sub": str(user.id)})

    # Возвращаем токен и тип
    return {"access_token": access_token, "token_type": "bearer"}
