"""Gemini configuration and safe API key handling for InventoryIQ V2."""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv


def _load_api_key() -> Optional[str]:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        return None
    return api_key.strip()


def get_gemini_api_key() -> Optional[str]:
    """Return the Gemini API key if configured, otherwise None."""
    return _load_api_key()


def is_gemini_configured() -> bool:
    """Return True if a Gemini API key is available."""
    return get_gemini_api_key() is not None
