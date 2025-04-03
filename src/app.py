from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from src.database import init_db
from src.routers import auth, expenses, protected


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[Any]:
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


app.include_router(auth.router)
app.include_router(expenses.router)
app.include_router(protected.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello World 2"}
