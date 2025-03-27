from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from src.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any]:
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello World"}
