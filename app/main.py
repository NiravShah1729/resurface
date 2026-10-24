"""FastAPI application entry point for Resurface."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.bot import notify_new_save, start_bot, stop_bot
from app.db import get_all_saves, init_db, insert_save
from app.llm import embed, extract_save

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup (DB, Telegram bot) and graceful shutdown."""
    init_db()
    await start_bot()
    yield
    await stop_bot()


app = FastAPI(
    title="Resurface",
    description="Local-first app to capture and resurface what you save.",
    lifespan=lifespan,
)


class SaveCreateRequest(BaseModel):
    raw_text: str = Field(..., description="Raw text of the post or bookmark")
    url: Optional[str] = Field(None, description="Source URL")
    source: Optional[str] = Field("manual", description="Source (instagram, linkedin, manual)")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/saves")
def list_saves(status: Optional[str] = None) -> list[dict[str, Any]]:
    """Retrieve saved items, optionally filtered by status."""
    return get_all_saves(status=status)


@app.post("/saves")
async def create_save(payload: SaveCreateRequest) -> dict[str, Any]:
    """Ingest a new save: extract metadata with Gemma, generate embedding, store, and notify Telegram."""
    extracted = extract_save(payload.raw_text)

    try:
        embedding_vec = embed(payload.raw_text)
    except Exception:
        embedding_vec = []

    save_data: dict[str, Any] = {
        "url": payload.url,
        "source": payload.source or "manual",
        "raw_text": payload.raw_text,
        "type": extracted.get("type", "other"),
        "title": extracted.get("title", "Untitled"),
        "why_saved": extracted.get("why_saved", ""),
        "action": extracted.get("action", "other"),
        "tags": extracted.get("tags", []),
        "learning_score": extracted.get("learning_score", 3),
        "embedding": embedding_vec,
        "status": "new",
        "times_surfaced": 0,
    }

    save_id = insert_save(save_data)
    save_data["id"] = save_id

    # Notify Telegram bot
    await notify_new_save(save_data)

    return save_data
