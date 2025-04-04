from beanie import PydanticObjectId
from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    icon: str | None = None


class CategoryPublic(BaseModel):
    id: PydanticObjectId
    name: str
    icon: str | None = None
