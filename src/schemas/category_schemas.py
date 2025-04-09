from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str
    icon: str | None = None
    color: str | None = Field(
        default=None,
        pattern="^#[0-9a-fA-F]{6}$",
        description="HEX color code (e.g. #FF5733)",
    )


class CategoryPublic(BaseModel):
    id: PydanticObjectId
    name: str
    icon: str | None = None
    color: str | None = Field(
        default=None,
        pattern="^#[0-9a-fA-F]{6}$",
        description="HEX color code (e.g. #FF5733)",
    )


class CategoryUpdate(BaseModel):
    name: str | None = None
    color: str | None = Field(
        default=None,
        pattern="^#[0-9a-fA-F]{6}$",
        description="HEX color code (e.g. #FF5733)",
    )
    icon: str | None = None
