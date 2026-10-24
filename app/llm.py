"""LLM and embedding abstraction layer."""

from typing import Optional


def generate(prompt: str, system: Optional[str] = None, json_mode: bool = False) -> str:
    """Generate text completion from the configured LLM model."""
    raise NotImplementedError("LLM generation will be implemented in the next step.")


def embed(text: str) -> list[float]:
    """Generate vector embeddings for given text."""
    raise NotImplementedError("Embeddings will be implemented in the next step.")
