# Импортируем базовую модель из Pydantic — она используется для валидации и сериализации данных
# Импортируем тип ObjectId, который Beanie использует для MongoDB-документов
from datetime import datetime
from decimal import Decimal  # Добавляем импорт Decimal

from beanie import PydanticObjectId
from pydantic import BaseModel, EmailStr, Field

# ---------- 📥 Модели, получаемые от клиента (входящие данные) ----------


# Модель, которую клиент отправляет при регистрации
class UserCreate(BaseModel):
    email: EmailStr  # Email — валидируется автоматически как email
    password: str  # Пароль в виде строки (в открытом виде на этом этапе)
    first_name: str  # Имя пользователя (обязательное)
    last_name: str  # Фамилия пользователя (обязательное)
    birth_date: datetime | None = None  # Дата рождения
    initial_balance: Decimal = Field(default=Decimal("0.00"))  # Начальный баланс


# Модель, которую клиент отправляет при логине
class UserLogin(BaseModel):
    email: EmailStr  # Тоже email
    password: str  # Пароль, чтобы проверить его с хэшем из базы


# ---------- 📤 Модели, которые возвращаются клиенту (ответы API) ----------


# Публичная модель пользователя — без пароля
class UserPublic(BaseModel):
    id: PydanticObjectId  # Уникальный идентификатор пользователя в базе MongoDB
    email: EmailStr  # Email пользователя, который мы можем безопасно вернуть
    first_name: str  # Имя пользователя
    last_name: str  # Фамилия пользователя
    birth_date: datetime | None = None  # Дата рождения
    balance: Decimal  # Текущий баланс пользователя


# Модель токена, возвращаемая после успешного логина
class Token(BaseModel):
    access_token: str  # JWT-токен, который мы создадим
    refresh_token: str | None = None  # JWT-токен, который мы создадим
    token_type: str = "bearer"  # Тип токена — всегда "bearer" для совместимости с OAuth2


# Вход: клиент создаёт новый расход
class ExpenseCreate(BaseModel):
    amount: Decimal
    category: str | None = None
    payment_method: str | None = None
    date: datetime | None = None
    description: str | None = None


# Ответ клиенту: публичная информация о расходе
class ExpensePublic(BaseModel):
    id: PydanticObjectId
    amount: Decimal
    category: str | None = None
    payment_method: str | None = None
    date: datetime | None = None
    description: str | None = None
    user_id: PydanticObjectId


class GoogleLoginPayload(BaseModel):
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str


class PasswordUpdateRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=8)


class PasswordUpdateResponse(BaseModel):
    detail: str = "Password updated successfully."
