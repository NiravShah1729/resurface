"""LLM and embedding abstraction layer using google-genai."""

import json
import logging
import os
import re
import time
from typing import Any, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

logger = logging.getLogger(__name__)

VALID_TYPES = {"book", "movie", "job", "skill", "recipe", "other"}
VALID_ACTIONS = {"read", "watch", "apply", "learn", "try", "other"}


def _get_client() -> genai.Client:
    """Return an initialized Google GenAI client."""
    api_key = os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=api_key) if api_key else genai.Client()


def _strip_code_fences(text: str) -> str:
    """Remove markdown code blocks (e.g. ```json ... ```) from response."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def generate(
    prompt: str, system: Optional[str] = None, json_mode: bool = False
) -> str:
    """Generate content from the configured model with retries and fallback."""
    model = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")
    client = _get_client()
    max_retries = 3

    for attempt in range(max_retries):
        try:
            config = types.GenerateContentConfig(
                temperature=0.0,
                system_instruction=system if system else None,
                response_mime_type="application/json" if json_mode else None,
            )
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            text = response.text or ""
            return _strip_code_fences(text) if json_mode else text
        except errors.APIError as exc:
            # Fall back if model rejects system instruction or json mime type
            if exc.code == 400 and (system or json_mode):
                try:
                    fallback_prompt = (
                        f"Instructions:\n{system}\n\nTask:\n{prompt}"
                        if system
                        else prompt
                    )
                    fallback_config = types.GenerateContentConfig(temperature=0.0)
                    response = client.models.generate_content(
                        model=model,
                        contents=fallback_prompt,
                        config=fallback_config,
                    )
                    text = response.text or ""
                    return _strip_code_fences(text) if json_mode else text
                except Exception as inner_exc:
                    logger.warning("Fallback generation failed: %s", inner_exc)

            # Retry on rate-limit (429) or server errors (5xx)
            if exc.code in {429, 500, 502, 503, 504} and attempt < max_retries - 1:
                sleep_sec = 2**attempt
                logger.warning(
                    "APIError %s on attempt %d. Backing off %ss...",
                    exc.code,
                    attempt + 1,
                    sleep_sec,
                )
                time.sleep(sleep_sec)
                continue
            raise
        except Exception as exc:
            if attempt < max_retries - 1:
                sleep_sec = 2**attempt
                time.sleep(sleep_sec)
                continue
            raise

    raise RuntimeError("Failed to generate content after retries.")


def embed(text: str) -> list[float]:
    """Generate vector embedding for the given text."""
    model = os.getenv("EMBED_MODEL", "gemini-embedding-001")
    client = _get_client()
    response = client.models.embed_content(model=model, contents=text)
    if response.embeddings and len(response.embeddings) > 0:
        return [float(v) for v in response.embeddings[0].values]
    return []


def _validate_extract_dict(data: Any) -> Optional[dict[str, Any]]:
    """Validate extracted fields against target schema."""
    if not isinstance(data, dict):
        return None

    item_type = str(data.get("type", "")).strip().lower()
    if item_type not in VALID_TYPES:
        return None

    title = str(data.get("title", "")).strip()
    if not title:
        return None

    why_saved = str(data.get("why_saved", "")).strip()
    if not why_saved:
        return None

    action = str(data.get("action", "")).strip().lower()
    if action not in VALID_ACTIONS:
        return None

    raw_tags = data.get("tags", [])
    if not isinstance(raw_tags, list):
        return None
    tags = [str(t).strip().lower() for t in raw_tags if str(t).strip()][:4]

    try:
        score = int(data.get("learning_score", 0))
        if not (1 <= score <= 5):
            return None
    except (ValueError, TypeError):
        return None

    return {
        "type": item_type,
        "title": title,
        "why_saved": why_saved,
        "action": action,
        "tags": tags,
        "learning_score": score,
    }


def _get_fallback_extract(raw_text: str) -> dict[str, Any]:
    """Provide a safe fallback dictionary if parsing fails."""
    title = "Untitled Save"
    noise_headers = {"instagram", "linkedin", "x", "twitter", "reels", "tiktok"}
    for line in raw_text.splitlines():
        cleaned = line.strip()
        if (
            cleaned
            and not cleaned.startswith(("#", "http", "http://", "https://"))
            and cleaned.lower() not in noise_headers
        ):
            title = cleaned[:60]
            break

    return {
        "type": "other",
        "title": title,
        "why_saved": "Saved for future reference.",
        "action": "other",
        "tags": ["saved"],
        "learning_score": 3,
    }


def extract_save(raw_text: str) -> dict[str, Any]:
    """Extract structured metadata from scraped post text using Gemma."""
    system = (
        "You are an intelligent bookmark analyzer. The input is scraped social media "
        "or web text and may include clutter (navigation menus, 'Sign in' prompts, comments, ads). "
        "Focus on the main post or resource content.\n"
        "Return a valid JSON object matching this schema:\n"
        "{\n"
        '  "type": "book" | "movie" | "job" | "skill" | "recipe" | "other",\n'
        '  "title": "<short descriptive title>",\n'
        '  "why_saved": "<one sentence guessing why the user saved it>",\n'
        '  "action": "read" | "watch" | "apply" | "learn" | "try" | "other",\n'
        '  "tags": ["<tag1>", "<tag2>", ... up to 4 lowercase tags],\n'
        '  "learning_score": <integer 1 to 5 indicating educational or actionable value>\n'
        "}"
    )

    prompt = f"Scraped text to analyze:\n\n{raw_text}"

    for attempt in range(2):
        try:
            raw_json = generate(prompt=prompt, system=system, json_mode=True)
            parsed = json.loads(raw_json)
            validated = _validate_extract_dict(parsed)
            if validated:
                return validated
            logger.warning("Attempt %d: Output failed schema validation", attempt + 1)
        except Exception as exc:
            logger.warning("Attempt %d: Extraction error: %s", attempt + 1, exc)

    return _get_fallback_extract(raw_text)
