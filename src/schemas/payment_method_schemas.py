from beanie import PydanticObjectId  # Для ID объектов из MongoDB
from pydantic import BaseModel, Field  # Pydantic для схем, Field для валидации


class PaymentMethodCreate(BaseModel):
    """
    📝 Схема для создания способа оплаты (от клиента)
    """

    name: str  # Название метода (например, "TD Credit 1234")
    bank: str | None = None  # Название банка (опционально)
    card_type: str | None = Field(default=None, pattern="^(credit|debit)$")  # Тип карты
    last4: str | None = Field(default=None, min_length=4, max_length=4)  # Последние 4 цифры карты
    icon: str | None = None  # Иконка: 💳, 🏦, 🧾 и т.д.


class PaymentMethodPublic(BaseModel):
    """
    📤 Схема, возвращаемая клиенту
    """

    id: PydanticObjectId  # Уникальный ID MongoDB
    name: str
    bank: str | None = None
    card_type: str | None = None
    last4: str | None = None
    icon: str | None = None


class PaymentMethodUpdate(BaseModel):
    name: str | None = None
    bank: str | None = None
    card_type: str | None = None
    icon: str | None = None
