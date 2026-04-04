"""Clarification gate: LLM-based clarification for vague/unclear queries."""

from __future__ import annotations

from dataclasses import dataclass

from agent.utils import parse_llm_json, format_history_text
from agent.prompts import CLARIFICATION_PROMPT, FALLBACK_QUESTION, detect_language
from shared.llm import get_model


@dataclass
class ClarificationResult:
    needs_clarification: bool
    question: str = ""


def check_clarification(
    query: str,
    history: list | None = None,
) -> ClarificationResult:
    """LLM-based clarification gate for unclear intents.

    Generates a dynamic clarification question using Gemini when the query
    is too vague. Always returns ``needs_clarification=True`` since this
    function is only called when confidence < 0.6 or intent == "unclear".
    """
    lang = detect_language(query)
    fallback_q = FALLBACK_QUESTION.get(lang, FALLBACK_QUESTION["en"])

    try:
        model = get_model()
    except RuntimeError:
        return ClarificationResult(
            needs_clarification=True,
            question=fallback_q,
        )

    history_text = format_history_text(history, limit=4)

    prompt = CLARIFICATION_PROMPT.format(
        query=query,
        history_text=history_text,
    )

    try:
        response = model.generate_content(prompt)
        data = parse_llm_json(response.text)
        question = data.get("question", "")
        if question:
            return ClarificationResult(
                needs_clarification=True,
                question=question,
            )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Clarification LLM failed: %s", exc)

    # Fallback
    return ClarificationResult(
        needs_clarification=True,
        question=fallback_q,
    )
