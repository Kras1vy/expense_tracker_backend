from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    MONGODB_URI: str
    SECRET_KEY: str


def get_config() -> Config:
    return Config()  # pyright: ignore[reportCallIssue]


config = get_config()  # Создаем экземпляр только когда модуль импортируется
