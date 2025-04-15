from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.config import config
from src.models import (
    BankAccount,
    BankConnection,
    BankTransaction,
    Budget,
    Category,
    PaymentMethod,
    RefreshToken,
    Transaction,
    User,
)


async def init_db() -> None:
    client = AsyncIOMotorClient(config.MONGODB_URI)
    db = client.get_default_database()
    await init_beanie(
        database=db,
        document_models=[
            User,
            RefreshToken,
            Category,
            Budget,
            PaymentMethod,
            Transaction,
            BankConnection,
            BankAccount,
            BankTransaction,
        ],
    )
    print("✅ MongoDB успешно подключена к базе:", db.name)
