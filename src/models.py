from datetime import UTC, datetime  # Импортируем UTC и datetime для работы с временем
from decimal import Decimal  # Добавляем импорт Decimal

from beanie import (  # Document — модель для MongoDB, PydanticObjectId — ID-шка
    Document,
    PydanticObjectId,
)
from pydantic import (  # EmailStr — проверка email, Field — для задания default значений
    EmailStr,
    Field,
)


class User(Document):
    email: EmailStr  # Обязательное поле email, автоматически проверяется
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
    user_id: str  # ID пользователя, которому принадлежит токен
    token: str  # Сам refresh токен (уникальная строка)
    created_at: datetime  # Дата и время, когда токен был создан
    expires_at: datetime  # Срок действия токена (после этой даты он считается недействительным)

    class Settings:
        name = "refresh_tokens"  # 👈 Указываем имя коллекции в MongoDB
