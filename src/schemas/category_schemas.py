from beanie import PydanticObjectId
from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    icon: str | None = None
    color: str | None = None  # 🎨 Цвет можно выбрать


class CategoryPublic(BaseModel):
    id: PydanticObjectId
    name: str
    icon: str | None = None
    color: str | None = None  # 🎨 Цвет можно выбрать


class CategoryUpdate(BaseModel):
    name: str | None
    color: str | None
    icon: str | None
