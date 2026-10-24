"""Action triggers, retrieval, and Q&A over saved bookmarks."""

import json
import logging
from typing import Any

import numpy as np

from app.db import get_all_saves
from app.llm import embed, generate

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two numeric vectors."""
    va, vb = np.array(a), np.array(b)
    norm = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / norm) if norm > 0 else 0.0


def ask_saves(question: str) -> str:
    """Answer user questions about their saved items using semantic search and Gemma."""
    saves = get_all_saves()
    if not saves:
        return "You don't have any saved items yet. Save a post first!"

    ranked_saves: list[dict[str, Any]] = []

    try:
        q_vec = embed(question)
        if q_vec:
            scored: list[tuple[float, dict[str, Any]]] = []
            for item in saves:
                raw_emb = item.get("embedding")
                if raw_emb:
                    try:
                        emb = json.loads(raw_emb) if isinstance(raw_emb, str) else raw_emb
                        if emb:
                            score = _cosine_similarity(q_vec, emb)
                            scored.append((score, item))
                            continue
                    except Exception:
                        pass
                scored.append((0.0, item))

            scored.sort(key=lambda x: x[0], reverse=True)
            ranked_saves = [item for _, item in scored[:10]]
    except Exception as exc:
        logger.warning("Embedding search failed, falling back to chronological order: %s", exc)

    if not ranked_saves:
        ranked_saves = saves[:10]

    context_lines = []
    for s in ranked_saves:
        title = s.get("title") or "Untitled"
        item_type = s.get("type") or "other"
        why = s.get("why_saved") or ""
        action = s.get("action") or "other"
        url = s.get("url") or ""
        context_lines.append(
            f"- [{item_type.upper()}] {title} (Action: {action}, URL: {url}): {why}"
        )

    context = "\n".join(context_lines)
    prompt = (
        f"Saved items:\n{context}\n\n"
        f"User question: {question}\n\n"
        "Answer the user's question concisely based on their saved items above. "
        "Include titles, links, and suggested actions when helpful."
    )

    try:
        return generate(
            prompt=prompt,
            system="You are Resurface assistant. You help the user recall and act on things they saved.",
        )
    except Exception as exc:
        logger.error("Failed to generate answer: %s", exc)
        return "Sorry, I had trouble answering that right now. Please try again."
