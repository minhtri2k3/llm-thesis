"""Centralized LLM client factory — Gemini-only support."""

from __future__ import annotations

import os
from typing import Generator, Optional, Any
from typing_extensions import Protocol
import google.generativeai as genai
from dataclasses import dataclass

@dataclass
class TokenUsage:
    """Token counts from a single LLM call."""
    input_tokens: int = 0
    output_tokens: int = 0
    call_name: str = ""  # e.g. "intent", "synthesis"

class LLMClient(Protocol):
    model_name: str

    def generate(self, prompt: str) -> str:
        """Generate a complete text response synchronously."""
        ...

    def stream(self, prompt: str) -> Generator[str, None, TokenUsage]:
        """Generate stream of tokens, returning TokenUsage when complete."""
        ...

# ---------------------------------------------------------------------------
# Provider Adapters
# ---------------------------------------------------------------------------

class GeminiClient:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._ensure_configured()
        self._model = genai.GenerativeModel(model_name)

    def _ensure_configured(self):
        # We configure once per process globally for google-generativeai
        if not hasattr(GeminiClient, "_configured"):
            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY environment variable is required but not set.")
            genai.configure(api_key=api_key)
            GeminiClient._configured = True

    def generate(self, prompt: str) -> str:
        res = self._model.generate_content(prompt)
        return res.text

    def stream(self, prompt: str) -> Generator[str, None, TokenUsage]:
        res = self._model.generate_content(prompt, stream=True)
        usage = TokenUsage()
        for chunk in res:
            if chunk.text:
                yield chunk.text
        # Optional: capture usage if available. Gemini Python SDK doesn't consistently return it on streams
        # but we'll try if usage_metadata is present on the response.
        if hasattr(res, "usage_metadata") and res.usage_metadata is not None:
            usage.input_tokens = getattr(res.usage_metadata, "prompt_token_count", 0)
            usage.output_tokens = getattr(res.usage_metadata, "candidates_token_count", 0)
        return usage


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_clients: dict[str, LLMClient] = {}

def get_client(model_id: Optional[str] = None) -> LLMClient:
    """Return a cached GeminiClient instance. Only Gemini is supported."""
    name = model_id or "gemini-2.5-flash"
    
    if name not in _clients:
        _clients[name] = GeminiClient(name)
    
    return _clients[name]

# Helper for backwards-compatibility or scripts that expect `get_model`
def get_model(model_name: Optional[str] = None) -> genai.GenerativeModel:
    name = model_name or "gemini-2.5-flash"
    client = get_client(name)
    if isinstance(client, GeminiClient):
        return client._model
    else:
        raise ValueError("get_model() called for non-Gemini model.")
