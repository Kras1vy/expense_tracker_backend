from datetime import UTC, datetime  # Импортируем UTC и datetime для работы с временем
from decimal import Decimal  # Добавляем импорт Decimal
from typing import Any, ClassVar

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

    class Settings:
        name = "users"  # Название коллекции в MongoDB
        indexes: ClassVar[list[str]] = [
            "email",  # Для быстрого поиска по email при логине
            "google_id",  # Для быстрого поиска пользователей Google
        ]


# Модель расхода (траты), будет храниться в коллекции "expenses"
class Expense(Document):
    amount: Decimal  # Сумма расхода
    category: str | None = None  # Категория (например, "Еда", "Транспорт"), можно оставить пустым
    payment_method: str | None = (
        None  # 💳 Способ оплаты (например, "Visa", "Cash"), можно оставить пустым
    )
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))  # Дата расхода
    description: str | None = None  # Описание расхода
    user_id: PydanticObjectId  # ID пользователя, которому принадлежит расход

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v: Any) -> Decimal:
        return convert_decimal128(v)

    class Settings:
        name = "expenses"  # Название коллекции в MongoDB
        indexes: ClassVar[list[str | tuple[str, ...]]] = [
            "user_id",  # Для быстрого получения всех расходов пользователя
            ("user_id", "date"),  # Для временных отчетов и сортировки по дате
            ("user_id", "category"),  # Для группировки по категориям
            ("user_id", "amount"),  # Для сортировки по сумме и поиска крупных трат
            ("user_id", "payment_method"),  # Для анализа по способам оплаты
            # Составной индекс для сложной аналитики: траты по категориям за период
            ("user_id", "category", "date"),
        ]


# 🔐 Модель для хранения refresh токенов в MongoDB
class RefreshToken(Document):
    user_id: PydanticObjectId  # ID пользователя, которому принадлежит токен
    token: str  # Сам refresh токен (уникальная строка)
    created_at: datetime  # Дата и время, когда токен был создан
    expires_at: datetime  # Срок действия токена (после этой даты он считается недействительным)

    class Settings:
        name = "refresh_tokens"  # 👈 Указываем имя коллекции в MongoDB
        indexes: ClassVar[list[str | tuple[str, ...]]] = [
            "token",  # Для быстрого поиска токена при обновлении
            "user_id",  # Для поиска всех токенов пользователя
            ("user_id", "expires_at"),  # Для очистки истекших токенов
        ]


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

    class Settings:
        name = "categories"
        indexes: ClassVar[list[str | tuple[str, str]]] = [
            "user_id",  # Индекс для быстрого поиска категорий пользователя
            ("name", "user_id"),  # Составной индекс для проверки уникальности
        ]


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

    class Settings:
        name = "payment_methods"
        indexes: ClassVar[list[str | tuple[str, ...]]] = [
            "user_id",  # Для быстрого получения методов оплаты пользователя
            ("user_id", "card_type"),  # Для фильтрации по типу карты
            ("user_id", "bank"),  # Для группировки по банкам
        ]


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

    class Settings:
        name = "budgets"  # Название коллекции
        indexes: ClassVar[list[str | tuple[str, ...]]] = [
            "user_id",  # Для быстрого получения всех бюджетов пользователя
            ("user_id", "category"),  # Уникальный бюджет для категории
            ("user_id", "created_at"),  # Для отслеживания истории изменений
        ]


class Income(Document):
    user_id: PydanticObjectId
    amount: Decimal
    category: str  # например: "зарплата", "фриланс", "подарок"
    source: str  # например: "банк", "наличные"
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v: Any) -> Decimal:
        return convert_decimal128(v)

    class Settings:
        name = "incomes"
        indexes: ClassVar[list[str | tuple[str, ...]]] = [
            "user_id",  # Для быстрого получения всех доходов
            ("user_id", "date"),  # Для отчетов по периодам
            ("user_id", "category"),  # Для анализа источников дохода
            ("user_id", "amount"),  # Для поиска крупных поступлений
            # Составной индекс для сложной аналитики: доходы по категориям за период
            ("user_id", "category", "date"),
        ]
