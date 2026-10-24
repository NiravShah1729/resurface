"""FastAPI application entry point for Resurface."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from dotenv import load_dotenv
from fastapi import FastAPI

from app.db import init_db

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle handler."""
    init_db()
    yield


app = FastAPI(
    title="Resurface",
    description="Local-first app to capture and resurface what you save.",
    lifespan=lifespan,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
