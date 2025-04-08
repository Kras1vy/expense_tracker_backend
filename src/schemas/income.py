from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class IncomeCreate(BaseModel):
    amount: Decimal
    category: str
    source: str


class IncomeResponse(BaseModel):
    id: str
    amount: Decimal
    category: str
    source: str
    date: datetime
