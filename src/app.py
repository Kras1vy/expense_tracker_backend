from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from beanie import PydanticObjectId
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder

from src.database import init_db
from src.routers import (
    account,
    ai,
    analytics,
    auth,
    budget,
    categories,
    payment_methods,
    plaid,
    transactions,
)

_ = load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[Any]:
    await init_db()
    yield


def custom_encoder(obj: Any) -> Any:
    if isinstance(obj, PydanticObjectId):
        return str(obj)
    return jsonable_encoder(obj)


app = FastAPI(
    title="Expense Tracker API",
    description="API for tracking expenses and managing budgets",
    version="1.0.0",
    lifespan=lifespan,
    json_encoders={PydanticObjectId: str},
)

# Настройка CORS


# Подключаем роутеры
app.include_router(auth.router)  # Аутентификация и авторизация
app.include_router(account.router)  # Управление аккаунтом
app.include_router(categories.router)  # Категории расходов
app.include_router(transactions.router)  # Транзакции
app.include_router(budget.router)  # Бюджеты
app.include_router(ai.router)  # AI
app.include_router(analytics.router)  # Аналитика
app.include_router(payment_methods.router)  # Способы оплаты
app.include_router(plaid.router)  # Plaid


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Welcome to Expense Tracker API"}
