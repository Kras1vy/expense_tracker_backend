from datetime import datetime
from decimal import Decimal

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class BudgetCreate(BaseModel):
    """
    📥 Создание нового бюджета
    """

    category: str  # Категория, для которой задаётся лимит
    limit: Decimal = Field(..., ge=0)  # Обязательное поле — сумма лимита


class BudgetUpdate(BaseModel):
    """
    🛠 Обновление лимита бюджета
    """

    limit: Decimal = Field(..., ge=0)  # Только лимит можно обновлять


class BudgetPublic(BaseModel):
    """
    📤 Ответ клиенту: информация о бюджете
    """

    id: PydanticObjectId  # Mongo ID
    category: str
    limit: Decimal
    created_at: datetime

