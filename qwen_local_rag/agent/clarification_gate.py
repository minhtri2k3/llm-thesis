"""Clarification gate: LLM-based clarification for vague/unclear queries."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClarificationResult:
    needs_clarification: bool
    question: str = ""


CLARIFICATION_PROMPT = """You are a fashion shopping assistant. The user's query is unclear or too vague.
Based on the query and conversation history, generate a helpful clarification question
to understand what the user is looking for.

Your question should:
1. Be in the same language as the user's query (Vietnamese or English)
2. Give specific examples to guide the user
3. Ask about: type of clothing, color, occasion, or style

Conversation history:
{history_text}

User query: {query}

Respond ONLY with valid JSON:
{{
    "question": "<your clarification question>"
}}
"""


def check_clarification(
    query: str,
    history: list | None = None,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
) -> ClarificationResult:
    """
    LLM-based clarification gate.

    Generates a dynamic clarification question using Gemini when the query
    is too vague. Always returns needs_clarification=True since this function
    is only called when confidence < 0.6 or intent == "unclear".
    """
    try:
        import google.generativeai as genai
    except ImportError:
        # Fallback to hardcoded if Gemini not available
        return ClarificationResult(
            needs_clarification=True,
            question="Bạn muốn tìm loại trang phục nào? (áo, quần, váy, giày...) Màu sắc ưa thích?",
        )

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return ClarificationResult(
            needs_clarification=True,
            question="Bạn có thể mô tả cụ thể hơn không? Ví dụ: loại trang phục, màu sắc, dịp sử dụng?",
        )

    genai.configure(api_key=key)
    model = genai.GenerativeModel(model_name)

    # Format history
    history_lines = []
    if history:
        for msg in history[-4:]:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", str(msg))
            history_lines.append(f"{role}: {content[:100]}")
    history_text = "\n".join(history_lines) if history_lines else "No prior conversation."

    prompt = CLARIFICATION_PROMPT.format(
        query=query,
        history_text=history_text,
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        data = json.loads(text)
        question = data.get("question", "")
        if question:
            return ClarificationResult(
                needs_clarification=True,
                question=question,
            )
    except Exception:
        pass

    # Fallback
    return ClarificationResult(
        needs_clarification=True,
        question=(
            "Bạn có thể mô tả cụ thể hơn không? Ví dụ:\n"
            "- Loại trang phục: áo sơ mi, váy, quần jeans...\n"
            "- Màu sắc: trắng, đen, xanh navy...\n"
            "- Dịp sử dụng: đi làm, đi chơi, dự tiệc..."
        ),
    )
