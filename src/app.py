from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv

_ = load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database import init_db
from src.routers import account, ai, analytics, auth, budget, categories, expenses, payment_methods


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[Any]:
    await init_db()
    yield


app = FastAPI(
    title="Expense Tracker API",
    description="API for tracking expenses and managing budgets",
    version="1.0.0",
    lifespan=lifespan,
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth.router)  # Аутентификация и авторизация
app.include_router(account.router)  # Управление аккаунтом
app.include_router(categories.router)  # Категории расходов
app.include_router(expenses.router)  # Расходы
app.include_router(budget.router)  # Бюджеты
app.include_router(ai.router)  # AI
app.include_router(analytics.router)  # Аналитика
app.include_router(payment_methods.router)  # Способы оплаты


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Welcome to Expense Tracker API"}
