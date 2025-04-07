from datetime import UTC, datetime  # Импортируем UTC и datetime для работы с временем
from decimal import Decimal  # Добавляем импорт Decimal

from beanie import (  # Document — модель для MongoDB, PydanticObjectId — ID-шка
    Document,
    PydanticObjectId,
)
from bson import ObjectId
from pydantic import (  # EmailStr — проверка email, Field — для задания default значений
    EmailStr,
    Field,
)


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

    class Settings:
        name = "users"  # Название коллекции в MongoDB


# Модель расхода (траты), будет храниться в коллекции "expenses"
class Expense(Document):
    title: str  # Название расхода (например, "Продукты", "Кафе")
    amount: Decimal  # Сумма расхода
    category: str | None = None  # Категория (например, "Еда", "Транспорт"), можно оставить пустым
    payment_method: str | None = (
        None  # 💳 Способ оплаты (например, "Visa", "Cash"), можно оставить пустым
    )
    saved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # Дата расхода, по умолчанию текущее время в UTC

    user_id: PydanticObjectId  # ID пользователя, которому принадлежит расход

    class Settings:
        name = "expenses"  # Название коллекции в MongoDB


# 🔐 Модель для хранения refresh токенов в MongoDB
class RefreshToken(Document):
    user_id: PydanticObjectId  # ID пользователя, которому принадлежит токен
    token: str  # Сам refresh токен (уникальная строка)
    created_at: datetime  # Дата и время, когда токен был создан
    expires_at: datetime  # Срок действия токена (после этой даты он считается недействительным)

    class Settings:
        name = "refresh_tokens"  # 👈 Указываем имя коллекции в MongoDB


class Category(Document):
    """
    📂 Категория расходов (кастомная или дефолтная)
    """

    name: str  # Название категории
    icon: str | None = None  # Эмодзи/иконка (опционально)
    color: str | None = None  # Цвет категории (опционально)
    user_id: PydanticObjectId | None = None  # Если None — дефолтная, иначе кастомная
    is_default: bool = False  # Используется для глобальных категорий

    class Settings:
        name = "categories"


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


class Budget(Document):
    """
    💰 Модель пользовательского бюджета по категориям
    """

    user_id: str  # ID пользователя
    category: str  # Название категории (например, "food")
    limit: Decimal = Field(..., ge=0)  # Сумма лимита (неотрицательная)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )  # 🕒 UTC-современное время

    class Settings:
        name = "budgets"  # Название коллекции
