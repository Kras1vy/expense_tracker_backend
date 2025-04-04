from decimal import Decimal
from typing import Final

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    MONGODB_URI: str
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


def get_config() -> Config:
    return Config()  # pyright: ignore[reportCallIssue]


config = get_config()  # Создаем экземпляр только когда модуль импортируется

# ────────────── 📊 Константы для аналитики ──────────────
# Допустимые временные интервалы для графиков
TIME_FRAMES: Final[set[str]] = {"day", "week", "month", "year"}

# Бюджеты по умолчанию для основных категорий
DEFAULT_BUDGETS: Final[dict[str, Decimal]] = {
    "food": Decimal("500.0"),  # Бюджет на еду
    "transport": Decimal("200.0"),  # Бюджет на транспорт
    "entertainment": Decimal("300.0"),  # Бюджет на развлечения
}
