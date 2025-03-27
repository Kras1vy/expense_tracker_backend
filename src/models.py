from beanie import Document  # базовая модель от Beanie
from pydantic import EmailStr  # проверка email


class User(Document):  # Document = модель для MongoDB
    email: EmailStr  # поле "email", обязательно, тип — email
    hashed_password: str  # хэш пароля, обязательно

    class Settings:
        name = "users"  # имя коллекции в MongoDB
