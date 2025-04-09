from fastapi import APIRouter

from src.routers.analytics.transactions import router as transactions_router

# Создаем основной роутер для аналитики
router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Подключаем роутер для транзакций
router.include_router(transactions_router)
