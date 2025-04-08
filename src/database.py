from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.config import config
from src.models import Budget, Category, Expense, Income, PaymentMethod, RefreshToken, User


async def init_db() -> None:
    client = AsyncIOMotorClient(config.MONGODB_URI)
    db = client.get_default_database()
    await init_beanie(
        database=db,
        document_models=[User, Expense, RefreshToken, Category, Budget, PaymentMethod, Income],
    )
    print("✅ MongoDB успешно подключена к базе:", db.name)
