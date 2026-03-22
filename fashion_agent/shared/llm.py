"""Centralized Gemini LLM client — singleton pattern.

All agent modules import `get_model()` from here instead of
calling `genai.configure()` + `GenerativeModel()` inline.
"""

from __future__ import annotations

import os
from typing import Optional

import google.generativeai as genai

# ---------------------------------------------------------------------------
# Singleton holder
# ---------------------------------------------------------------------------

_configured = False
_models: dict[str, genai.GenerativeModel] = {}

DEFAULT_MODEL = "gemini-2.5-flash"


def get_model(model_name: Optional[str] = None) -> genai.GenerativeModel:
    """Return a cached ``GenerativeModel`` instance.

    On first call, configures the SDK with ``GEMINI_API_KEY`` from env.
    Subsequent calls reuse the same model object (keyed by *model_name*).

    Raises:
        RuntimeError: If ``GEMINI_API_KEY`` is not set.
    """
    global _configured

    if not _configured:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is required but not set."
            )
        genai.configure(api_key=api_key)
        _configured = True

    name = model_name or DEFAULT_MODEL
    if name not in _models:
        _models[name] = genai.GenerativeModel(name)
    return _models[name]
