from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    MONGODB_URI: str


config = Config()  # pyright: ignore[reportCallIssue]
