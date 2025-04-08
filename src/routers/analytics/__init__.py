from fastapi import APIRouter

from src.routers.analytics.expenses import router as expenses_router
from src.routers.analytics.incomes import router as incomes_router

# Создаем основной роутер для аналитики
router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Подключаем роутеры для расходов и доходов
router.include_router(expenses_router)
router.include_router(incomes_router)
