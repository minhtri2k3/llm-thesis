"""
Fashion Agent — main orchestrator.

Ties together intent classification, clarification, memory, search, and
Gemini synthesis into a single `chat()` function.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

from agent.intent_classifier import classify_intent, ClassifiedIntent
from agent.clarification_gate import check_clarification
from agent.memory import (
    create_session,
    session_exists,
    add_message,
    get_history,
    init_memory_tables,
    Message,
)
from search.search_engine import search as hybrid_search
from search.fusion import NodeWithScore


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ProductResult:
    image_id: str
    image_path: str
    label: str
    color: str
    caption: str
    score: float


@dataclass
class AgentResponse:
    answer: str
    products: list[ProductResult] = field(default_factory=list)
    styling_suggestion: str = ""
    reasoning: str = ""
    session_id: str = ""
    intent: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Gemini synthesis
# ---------------------------------------------------------------------------

SYNTHESIS_PROMPT = """You are a helpful fashion shopping assistant. Based on the search results and user query, provide a natural, helpful response in the same language as the user's query.

User query: {query}

Search results (top products):
{products_text}

Conversation history:
{history_text}

Instructions:
1. Respond naturally in the same language as the user's query (Vietnamese or English).
2. Briefly describe the top recommendations and why they match.
3. If this is a "recommend" intent, include styling suggestions.
4. Keep the response concise (2-4 sentences for search, 3-5 for recommendations).
5. Reference specific products by their attributes (category, color, style).

Respond with ONLY a JSON object:
{{
    "answer": "<your natural language response>",
    "styling_suggestion": "<optional styling tips, empty string if not applicable>"
}}
"""


def _synthesize_response(
    query: str,
    products: list[NodeWithScore],
    history: list[Message],
    intent: str,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
) -> tuple[str, str]:
    """Use Gemini to synthesize a natural response from search results."""
    try:
        import google.generativeai as genai
    except ImportError:
        # Fallback if Gemini not available
        if products:
            labels = [p.label for p in products[:3]]
            return f"Tìm thấy {len(products)} sản phẩm: {', '.join(labels)}.", ""
        return "Không tìm thấy sản phẩm phù hợp.", ""

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        if products:
            labels = [p.label for p in products[:3]]
            return f"Tìm thấy {len(products)} sản phẩm: {', '.join(labels)}.", ""
        return "Không tìm thấy sản phẩm phù hợp.", ""

    genai.configure(api_key=key)
    model = genai.GenerativeModel(model_name)

    # Format products
    products_lines = []
    for i, p in enumerate(products, 1):
        products_lines.append(
            f"{i}. {p.label} | Color: {p.color} | Caption: {p.caption[:80]}"
        )
    products_text = "\n".join(products_lines) if products_lines else "No products found."

    # Format history
    history_lines = []
    for msg in history[-6:]:  # last 6 messages
        history_lines.append(f"{msg.role}: {msg.content[:100]}")
    history_text = "\n".join(history_lines) if history_lines else "No prior conversation."

    prompt = SYNTHESIS_PROMPT.format(
        query=query,
        products_text=products_text,
        history_text=history_text,
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        data = json.loads(text)
        return data.get("answer", ""), data.get("styling_suggestion", "")
    except Exception:
        if products:
            labels = [p.label for p in products[:3]]
            return f"Tìm thấy {len(products)} sản phẩm: {', '.join(labels)}.", ""
        return "Không tìm thấy sản phẩm phù hợp.", ""


# ---------------------------------------------------------------------------
# Main chat function
# ---------------------------------------------------------------------------

MAX_REACT_ITERATIONS = 2
LOW_CONFIDENCE_THRESHOLD = 0.5


def chat(
    query: str,
    session_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> AgentResponse:
    """
    Main agent entry point.

    Orchestrates: intent → clarify → memory → search → (ReAct) → synthesize.

    Args:
        query:       User message.
        session_id:  Optional existing session ID. Creates new if None.
        api_key:     Gemini API key override.

    Returns:
        AgentResponse with answer, products, and metadata.
    """
    # Ensure memory tables exist
    try:
        init_memory_tables()
    except Exception:
        pass  # Tables may already exist

    # Session management
    if session_id and session_exists(session_id):
        pass
    else:
        session_id = create_session()

    # Save user message
    add_message(session_id, "user", query)

    # Load history
    history = get_history(session_id, limit=20)

    # Step 1: Intent classification
    intent_result = classify_intent(query, api_key=api_key)

    # Step 2: Handle chat intent (no search needed)
    if intent_result.intent == "chat":
        answer, _ = _synthesize_response(
            query=query,
            products=[],
            history=history,
            intent="chat",
            api_key=api_key,
        )
        if not answer:
            answer = "Xin chào! Tôi là Fashion Agent, trợ lý tìm kiếm thời trang. Bạn muốn tìm trang phục gì?"
        add_message(session_id, "assistant", answer)
        return AgentResponse(
            answer=answer,
            session_id=session_id,
            intent="chat",
        )

    # Step 3: Clarification gate
    clarification = check_clarification(query)
    if clarification.needs_clarification and intent_result.intent == "clarify":
        add_message(session_id, "assistant", clarification.question)
        return AgentResponse(
            answer=clarification.question,
            session_id=session_id,
            intent="clarify",
            reasoning="Query too vague for meaningful search.",
        )

    # Step 4: Search with ReAct loop
    search_query = intent_result.refined_query or query
    products: list[NodeWithScore] = []
    reasoning_steps: list[str] = []

    for iteration in range(MAX_REACT_ITERATIONS):
        reasoning_steps.append(f"Iteration {iteration + 1}: searching '{search_query}'")
        products = hybrid_search(search_query, top_k=6)

        if products and products[0].score > LOW_CONFIDENCE_THRESHOLD:
            reasoning_steps.append(
                f"High confidence (top score: {products[0].score:.3f}). Proceeding to synthesis."
            )
            break

        if iteration < MAX_REACT_ITERATIONS - 1 and (not products or products[0].score <= LOW_CONFIDENCE_THRESHOLD):
            # Refine query for next iteration
            search_query = f"{query} {intent_result.filters.get('category', '')} fashion"
            reasoning_steps.append(f"Low confidence. Refining query to: '{search_query}'")

    # Step 5: Synthesize response
    answer, styling = _synthesize_response(
        query=query,
        products=products,
        history=history,
        intent=intent_result.intent,
        api_key=api_key,
    )

    # Convert NodeWithScore to ProductResult
    product_results = [
        ProductResult(
            image_id=p.image_id,
            image_path=p.image_path,
            label=p.label,
            color=p.color,
            caption=p.caption,
            score=p.score,
        )
        for p in products
    ]

    # Save assistant response
    add_message(session_id, "assistant", answer)

    return AgentResponse(
        answer=answer,
        products=product_results,
        styling_suggestion=styling,
        reasoning=" → ".join(reasoning_steps),
        session_id=session_id,
        intent=intent_result.intent,
    )
