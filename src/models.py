from datetime import UTC, date, datetime  # Импортируем UTC и datetime для работы с временем
from decimal import Decimal  # Добавляем импорт Decimal
from enum import StrEnum
from typing import Any, ClassVar, Literal, override

from beanie import (  # Document — модель для MongoDB, PydanticObjectId — ID-шка
    Document,
    PydanticObjectId,
)
from pydantic import (  # EmailStr — проверка email, Field — для задания default значений
    EmailStr,
    Field,
    field_validator,
)

from src.utils.mongo_types import convert_decimal128


class User(Document):
    email: EmailStr  # Обязательное поле email, автоматически проверяется
    first_name: str  # Имя пользователя (обязательное)
    last_name: str  # Фамилия пользователя (обязательное)
    birth_date: datetime | None = None  # Дата рождения
    hashed_password: str | None = None  # Пароль в зашифрованном виде, может быть None для OAuth
    google_id: str | None = (
        None  # ID пользователя в Google, может быть None для обычной регистрации
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )  # 🕓 Автоматическое время регистрации

    balance: Decimal = Field(default=Decimal("0.00"))

    @field_validator("balance", mode="before")
    @classmethod
    def validate_balance(cls, v: Any) -> Decimal:
        return convert_decimal128(v)

    @override
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(*args, **kwargs)
        if "balance" in data:
            data["balance"] = float(data["balance"])
        return data

    class Settings:
        name = "users"  # Название коллекции в MongoDB
        indexes: ClassVar[list[str]] = [
            "email",  # Для быстрого поиска по email при логине
            "google_id",  # Для быстрого поиска пользователей Google
        ]
        json_encoders: ClassVar[dict[type, Any]] = {Decimal: float}


class TransactionType(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class Transaction(Document):
    """
    Модель для хранения как расходов, так и доходов
    """

    user_id: PydanticObjectId  # ID пользователя
    amount: Decimal  # Сумма транзакции
    source: Literal["manual", "plaid"] = "manual"
    type: TransactionType  # Тип: expense или income
    category: str | None = None  # Категория (например, "Еда", "Зарплата")
    payment_method: str | None = None  # Способ оплаты (для расходов)
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))  # Дата транзакции
    description: str | None = None  # Описание транзакции

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v: Any) -> Decimal:
        return convert_decimal128(v)

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v: datetime | None) -> datetime:
        if v is None:
            return datetime.now(UTC)
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v

    @override
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(*args, **kwargs)
        if "amount" in data:
            data["amount"] = float(data["amount"])
        # Convert ObjectId to string
        if "id" in data:
            data["id"] = str(data["id"])
        if "user_id" in data:
            data["user_id"] = str(data["user_id"])
        return data

    class Settings:
        name = "transactions"  # Название коллекции в MongoDB
        json_encoders: ClassVar[dict[type, Any]] = {
            Decimal: float,
            PydanticObjectId: str,
        }  # Конвертируем Decimal в float при сериализации
        indexes: ClassVar[list[str | tuple[str, ...]]] = [
            "user_id",  # Для быстрого получения всех транзакций пользователя
            ("user_id", "date"),  # Для временных отчетов и сортировки по дате
            ("user_id", "category"),  # Для группировки по категориям
            ("user_id", "type"),  # Для фильтрации по типу (расход/доход)
            ("user_id", "amount"),  # Для сортировки по сумме
            # Составной индекс для сложной аналитики: транзакции по категориям за период
            ("user_id", "category", "date"),
            # Составной индекс для фильтрации по типу и дате
            ("user_id", "type", "date"),
        ]


# 🔐 Модель для хранения refresh токенов в MongoDB
class RefreshToken(Document):
    user_id: PydanticObjectId
    token: str
    created_at: datetime
    expires_at: datetime

    class Settings:
        name = "refresh_tokens"
        indexes: ClassVar[list[str | tuple[str, ...]]] = [
            "token",
            "user_id",
            ("user_id", "expires_at"),
        ]
        json_encoders: ClassVar[dict[type, Any]] = {
            PydanticObjectId: str,
            datetime: str,
        }


class Category(Document):
    """
    📂 Категория расходов (кастомная или дефолтная)
    """

    name: str = Field(..., min_length=1, max_length=50)  # Название категории
    icon: str | None = Field(default=None, max_length=10)  # Эмодзи/иконка (опционально)
    color: str | None = Field(
        default=None,
        pattern="^#[0-9a-fA-F]{6}$",
        description="HEX color code (e.g. #FF5733)",
    )  # Цвет категории (опционально)
    user_id: PydanticObjectId | None = None  # Если None — дефолтная, иначе кастомная
    is_default: bool = False  # Используется для глобальных категорий

    @override
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(*args, **kwargs)
        if "user_id" in data and data["user_id"] is not None:
            data["user_id"] = str(data["user_id"])
        return data

    class Settings:
        name = "categories"
        indexes: ClassVar[list[str | tuple[str, str]]] = [
            "user_id",
            ("name", "user_id"),
        ]
        json_encoders: ClassVar[dict[type, Any]] = {
            PydanticObjectId: str,
        }


class PaymentMethod(Document):
    """
    💳 Кастомный платёжный метод пользователя
    """

    name: str  # Название: "TD Debit 1234"
    bank: str | None = None  # Название банка: TD, CIBC и т.д.
    card_type: str | None = Field(
        default=None, pattern="^(credit|debit)$"
    )  # Тип: debit или credit
    last4: str | None = Field(default=None, min_length=4, max_length=4)  # Последние 4 цифры
    icon: str | None = None  # 🎨 Эмодзи или иконка: 🏦 💳
    user_id: PydanticObjectId  # Привязка к пользователю

    @override
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(*args, **kwargs)
        if "user_id" in data:
            data["user_id"] = str(data["user_id"])
        return data

    class Settings:
        name = "payment_methods"
        indexes: ClassVar[list[str | tuple[str, ...]]] = [
            "user_id",
            ("user_id", "card_type"),
            ("user_id", "bank"),
        ]
        json_encoders: ClassVar[dict[type, Any]] = {
            PydanticObjectId: str,
        }


class Budget(Document):
    """
    💰 Модель пользовательского бюджета по категориям
    """

    user_id: PydanticObjectId  # ID пользователя
    category: str  # Название категории (например, "food")
    limit: Decimal = Field(..., ge=0)  # Сумма лимита (неотрицательная)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )  # 🕒 UTC-современное время

    @field_validator("limit", mode="before")
    @classmethod
    def validate_limit(cls, v: Any) -> Decimal:
        return convert_decimal128(v)

    @override
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(*args, **kwargs)
        if "limit" in data:
            data["limit"] = float(data["limit"])
        return data

    class Settings:
        name = "budgets"
        json_encoders: ClassVar[dict[type, Any]] = {
            Decimal: float,
            PydanticObjectId: str,
            datetime: str,
        }
        indexes: ClassVar[list[str | tuple[str, ...]]] = [
            "user_id",
            ("user_id", "category"),
            ("user_id", "created_at"),
        ]


class BankConnection(Document):
    user_id: PydanticObjectId
    access_token: str
    item_id: str
    institution_id: str | None = Field(default=None)
    institution_name: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @override
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(*args, **kwargs)
        if "user_id" in data:
            data["user_id"] = str(data["user_id"])
        return data

    class Settings:
        name = "bank_connections"
        json_encoders: ClassVar[dict[type, Any]] = {
            PydanticObjectId: str,
            datetime: str,
        }


class BankAccount(Document):
    user_id: PydanticObjectId
    bank_connection_id: PydanticObjectId  # связь с BankConnection
    account_id: str  # ID от Plaid
    name: str
    official_name: str | None = None
    type: str
    subtype: str | None = None
    mask: str | None = None
    current_balance: float | None = None
    available_balance: float | None = None
    iso_currency_code: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @override
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(*args, **kwargs)
        if "user_id" in data:
            data["user_id"] = str(data["user_id"])
        if "bank_connection_id" in data:
            data["bank_connection_id"] = str(data["bank_connection_id"])
        return data

    class Settings:
        name = "bank_accounts"
        json_encoders: ClassVar[dict[type, Any]] = {
            PydanticObjectId: str,
            datetime: str,
        }


class BankTransaction(Document):
    user_id: PydanticObjectId
    bank_account_id: PydanticObjectId  # связь с BankAccount
    transaction_id: str  # от Plaid
    source: Literal["manual", "plaid"] = "plaid"  # для BankTransaction
    name: str
    amount: float
    date: date
    category: list[str] | None = None
    payment_method: str | None = None
    payment_channel: str | None = None
    iso_currency_code: str | None = None
    pending: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @override
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(*args, **kwargs)
        if "user_id" in data:
            data["user_id"] = str(data["user_id"])
        if "bank_account_id" in data:
            data["bank_account_id"] = str(data["bank_account_id"])
        return data

    class Settings:
        name = "bank_transactions"
        json_encoders: ClassVar[dict[type, Any]] = {
            PydanticObjectId: str,
            datetime: str,
            date: str,
        }
