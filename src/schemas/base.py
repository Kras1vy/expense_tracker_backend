# Импортируем базовую модель из Pydantic — она используется для валидации и сериализации данных
# Импортируем тип ObjectId, который Beanie использует для MongoDB-документов
from datetime import datetime
from decimal import Decimal  # Добавляем импорт Decimal

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BaseModelWithConfig(BaseModel):
    """Базовая модель с настройками сериализации"""

    model_config = ConfigDict(
        json_encoders={
            PydanticObjectId: str,  # MongoDB ID -> строка
            Decimal: str,  # Decimal -> строка
        }
    )


class BaseModelWithDecimalAsFloat(BaseModel):
    """Базовая модель для транзакций, где Decimal конвертируется в float"""

    model_config = ConfigDict(
        json_encoders={
            PydanticObjectId: str,  # MongoDB ID -> строка
            Decimal: float,  # Decimal -> float для числовых полей
        }
    )


# ---------- 📥 Модели, получаемые от клиента (входящие данные) ----------


# Модель, которую клиент отправляет при регистрации
class UserCreate(BaseModelWithConfig):
    email: EmailStr  # Email — валидируется автоматически как email
    password: str  # Пароль в виде строки (в открытом виде на этом этапе)
    first_name: str  # Имя пользователя (обязательное)
    last_name: str  # Фамилия пользователя (обязательное)
    birth_date: datetime | None = None  # Дата рождения
    initial_balance: Decimal = Field(default=Decimal("0.00"))  # Начальный баланс


# Модель, которую клиент отправляет при логине
class UserLogin(BaseModelWithConfig):
    email: EmailStr  # Тоже email
    password: str  # Пароль, чтобы проверить его с хэшем из базы


# ---------- 📤 Модели, которые возвращаются клиенту (ответы API) ----------


# Публичная модель пользователя — без пароля
class UserPublic(BaseModelWithConfig):
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


# Выход: сервер возвращает созданный расход
class ExpensePublic(BaseModel):
    id: PydanticObjectId
    amount: Decimal
    category: str | None = None
    payment_method: str | None = None
    date: datetime | None = None
    description: str | None = None
    user_id: PydanticObjectId


# Модель для создания транзакции (доход или расход)
class TransactionCreate(BaseModelWithDecimalAsFloat):
    amount: Decimal
    type: str  # "expense" или "income"
    category: str | None = None
    payment_method: str | None = None
    source: str | None = None  # Для доходов
    date: datetime | None = None
    description: str | None = None


# Модель для возврата транзакции
class TransactionPublic(BaseModelWithDecimalAsFloat):
    id: PydanticObjectId
    amount: Decimal
    type: str
    category: str | None = None
    payment_method: str | None = None
    source: str | None = None
    date: datetime | None = None
    description: str | None = None
    user_id: PydanticObjectId


# Модель для Google OAuth
class GoogleLoginPayload(BaseModel):
    id_token: str


# Модель для ответа с токеном
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str


# Модель для обновления пароля
class PasswordUpdateRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=8)


# Модель для ответа на обновление пароля
class PasswordUpdateResponse(BaseModel):
    detail: str = "Password updated successfully."
