"""
Fashion Agent — main orchestrator.

Ties together intent classification, slot-based clarification, memory, search, and
Gemini synthesis into a single `chat()` function.

Architecture (v2 — direct routing, no ReAct loop):
  1. classify_intent → single LLM call for intent + slots
  2. slot gate → template clarification if incomplete (0 LLM)
  3. _route_and_execute → deterministic routing to search/clarify
  4. _synthesize_response → Gemini synthesis (1 LLM call)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Generator, Optional, Union

from agent.utils import parse_llm_json, fallback_text_response, format_history_text
from agent.prompts import SYNTHESIS_PROMPT, STREAM_SYNTHESIS_PROMPT
from shared.llm import get_model

from agent.intent_classifier import classify_intent, ClassifiedIntent, ExtractedSlots
from agent.slot_completeness import (
    check_slot_completeness,
    build_template_question,
    merge_slots,
    should_reset_slots,
    compose_refined_query_from_slots,
)
from agent.clarification_gate import check_clarification
from agent.memory import (
    create_session,
    session_exists,
    add_message,
    get_history,
    init_memory_tables,
    log_query,
    get_preferences,
    Message,
)
from search.search_engine import search as hybrid_search
from search.fusion import NodeWithScore

logger = logging.getLogger(__name__)


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


@dataclass
class ThinkingEvent:
    """Emitted during orchestration to show pipeline progress to the user."""

    step: str        # e.g. "start", "classify_done", "search_done"
    detail: str      # human-readable detail text
    timestamp: float = field(default_factory=time.time)


@dataclass
class ThinkingToken:
    """Gemini model thinking content (thought=True)."""

    text: str


@dataclass
class ResponseToken:
    """Gemini model response content (regular text)."""

    text: str


# Union type for synthesis stream output
SynthesisChunk = Union[ThinkingToken, ResponseToken]


# ---------------------------------------------------------------------------
# Synthesis context builder (shared between batch & stream)
# ---------------------------------------------------------------------------


def _build_synthesis_context(
    query: str,
    products: list,
    history: list[Message],
    preferences: Optional[dict] = None,
) -> dict[str, str]:
    """Format products, history, and preferences into text for synthesis prompts.

    Returns:
        Dict with keys ``products_text``, ``history_text``, ``preferences_text``.
    """
    # Format products
    products_lines = []
    for i, p in enumerate(products, 1):
        products_lines.append(
            f"{i}. {p.label} | Color: {p.color} | Caption: {p.caption[:80]}"
        )
    products_text = "\n".join(products_lines) if products_lines else "No products found."

    history_text = format_history_text(history, limit=6)

    # Format preferences
    prefs = preferences or {}
    prefs_parts = []
    if prefs.get("preferred_colors"):
        prefs_parts.append(f"Preferred colors: {', '.join(prefs['preferred_colors'])}")
    if prefs.get("preferred_categories"):
        prefs_parts.append(f"Preferred categories: {', '.join(prefs['preferred_categories'])}")
    preferences_text = "; ".join(prefs_parts) if prefs_parts else "No preferences yet."

    return {
        "products_text": products_text,
        "history_text": history_text,
        "preferences_text": preferences_text,
    }


# ---------------------------------------------------------------------------
# Gemini synthesis
# ---------------------------------------------------------------------------



def _synthesize_response(
    query: str,
    products: list[NodeWithScore],
    history: list[Message],
    intent: str,
    preferences: Optional[dict] = None,
) -> tuple[str, str]:
    """Use Gemini to synthesize a natural response from search results."""
    try:
        model = get_model()
    except RuntimeError:
        return fallback_text_response(products), ""

    ctx = _build_synthesis_context(query, products, history, preferences)

    prompt = SYNTHESIS_PROMPT.format(query=query, **ctx)

    try:
        response = model.generate_content(prompt)
        data = parse_llm_json(response.text)
        return data.get("answer", ""), data.get("styling_suggestion", "")
    except Exception:
        return fallback_text_response(products), ""


# ---------------------------------------------------------------------------
# Streaming Synthesis
# ---------------------------------------------------------------------------

def _synthesize_response_stream(
    query: str,
    products: list[NodeWithScore],
    history: list[Message],
    intent: str,
    preferences: Optional[dict] = None,
) -> Generator:
    """Streaming version of synthesis — yields ``SynthesisChunk`` instances.

    Uses ``stream=True`` with Gemini for token-by-token output.
    Separates Gemini thinking tokens (``part.thought=True``) from
    response tokens.

    Yields:
        ThinkingToken | ResponseToken: Chunks as they arrive from the LLM.
    """
    try:
        model = get_model()
    except RuntimeError:
        yield ResponseToken(fallback_text_response(products))
        return

    ctx = _build_synthesis_context(query, products, history, preferences)

    prompt = STREAM_SYNTHESIS_PROMPT.format(query=query, **ctx)

    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            # Try iterating parts for thinking/response separation
            if hasattr(chunk, "parts") and chunk.parts:
                for part in chunk.parts:
                    text = getattr(part, "text", None)
                    if not text:
                        continue
                    if getattr(part, "thought", False):
                        yield ThinkingToken(text)
                    else:
                        yield ResponseToken(text)
            elif chunk.text:
                # Fallback: SDK without parts support
                yield ResponseToken(chunk.text)
    except Exception as exc:
        logger.warning("Streaming synthesis failed: %s", exc)
        yield ResponseToken(fallback_text_response(products))


def _extract_styling_from_text(full_text: str) -> str:
    """Extract styling suggestion from streamed text."""
    for marker in ("💡 Styling tip:",):
        if marker in full_text:
            return full_text.split(marker, 1)[1].strip()
    return ""


# ---------------------------------------------------------------------------
# Direct routing (replacement for ReAct loop)
# ---------------------------------------------------------------------------

OUT_OF_SCOPE_RESPONSE = (
    "Sorry, I only help with fashion search and styling advice. "
    "Would you like to look for any outfit?"
)

MAX_CLARIFICATION_TURNS = 3

# In-memory storage for accumulated slots per session (auto-evicted after 30 min)
# Key: session_id, Value: ExtractedSlots
from cachetools import TTLCache

_session_accumulated_slots: TTLCache = TTLCache(maxsize=100, ttl=1800)


def _route_and_execute(
    intent: str,
    search_query: str,
    session_id: str,
    filters: Optional[dict] = None,
) -> tuple[list[NodeWithScore], str]:
    """Deterministic routing based on intent — no planner LLM call.

    Routes:
    - text_search / follow_up → ``hybrid_search(use_query_expansion=False)``
    - outfit_request → search + outfit hint via LLM
    - out_of_scope → empty products + template message
    - unclear → empty products (caller handles clarification)

    Returns:
        (products, reasoning_text)
    """
    if intent in ("text_search", "follow_up"):
        products = hybrid_search(
            search_query,
            top_k=6,
            use_query_expansion=False,
            filters=filters,
        )
        reasoning = f"Direct search '{search_query}' → {len(products)} results"
        if products:
            top = products[0]
            reasoning += f" (top: {top.label}, score={top.score:.3f})"
        return products, reasoning

    if intent == "outfit_request":
        products = hybrid_search(
            search_query,
            top_k=6,
            use_query_expansion=False,
            filters=filters,
        )
        reasoning = f"Outfit search '{search_query}' → {len(products)} results"
        return products, reasoning

    # out_of_scope / unclear — no products
    return [], f"Intent '{intent}' — no search performed"


# ---------------------------------------------------------------------------
# Slot gate helper
# ---------------------------------------------------------------------------


def _resolve_search_query(
    intent: str,
    intent_result: ClassifiedIntent,
    session_id: str,
    history: list[Message],
) -> tuple[str, str]:
    """Resolve the search query and check if clarification is needed.

    Handles slot merging, completeness checking, and query composition
    for ``text_search`` and ``follow_up`` intents.

    Returns:
        (search_query, clarification_message)
        ``clarification_message`` is non-empty when the caller should
        return early with a clarification question.
    """
    if intent == "text_search":
        new_slots = intent_result.extracted_slots
        accumulated = _session_accumulated_slots.get(session_id, ExtractedSlots())

        if should_reset_slots(accumulated, new_slots):
            accumulated = ExtractedSlots()

        accumulated = merge_slots(accumulated, new_slots)
        _session_accumulated_slots[session_id] = accumulated

        is_complete, missing = check_slot_completeness(accumulated)
        if not is_complete:
            clarify_count = _count_clarification_turns(history)
            if clarify_count < MAX_CLARIFICATION_TURNS:
                question = build_template_question(
                    missing_slots=missing, slots=accumulated,
                )
                reasoning = (
                    f"Slots incomplete ({', '.join(missing)}). "
                    f"Turn {clarify_count + 1}/{MAX_CLARIFICATION_TURNS}."
                )
                return "", question

        search_query = compose_refined_query_from_slots(accumulated)
        if not search_query.strip():
            search_query = intent_result.refined_query or ""
        return search_query, ""

    if intent == "follow_up":
        new_slots = intent_result.extracted_slots
        accumulated = _session_accumulated_slots.get(session_id, ExtractedSlots())
        accumulated = merge_slots(accumulated, new_slots)
        _session_accumulated_slots[session_id] = accumulated

        slot_query = compose_refined_query_from_slots(accumulated)
        search_query = slot_query if slot_query.strip() else (intent_result.refined_query or "")
        return search_query, ""

    # outfit_request, unclear, etc.
    if intent_result.confidence < 0.6 or intent == "unclear":
        clarification = check_clarification(
            intent_result.refined_query or "", history=history,
        )
        if clarification.needs_clarification:
            return "", clarification.question

    return intent_result.refined_query or "", ""


# ---------------------------------------------------------------------------
# Orchestration (shared between chat and chat_stream)
# ---------------------------------------------------------------------------


@dataclass
class OrchestrateResult:
    """Intermediate result from ``_orchestrate()``.

    If ``clarification`` is non-empty, the caller should return early
    with the clarification text and skip synthesis.
    """

    intent: str
    session_id: str
    products: list[NodeWithScore] = field(default_factory=list)
    search_query: str = ""
    clarification: str = ""
    reasoning: str = ""
    preferences: dict = field(default_factory=dict)
    history: list[Message] = field(default_factory=list)
    filters: dict = field(default_factory=dict)


def _orchestrate(
    query: str,
    session_id: Optional[str] = None,
) -> OrchestrateResult:
    """Batch orchestration — consumes stream, returns final result.

    Internally delegates to ``_orchestrate_stream()`` and discards
    intermediate ``ThinkingEvent`` objects, keeping only the final
    ``OrchestrateResult``.
    """
    result = None
    for event in _orchestrate_stream(query, session_id):
        if isinstance(event, OrchestrateResult):
            result = event
    if result is None:
        raise RuntimeError("_orchestrate_stream() did not yield OrchestrateResult")
    return result


def _orchestrate_stream(
    query: str,
    session_id: Optional[str] = None,
) -> Generator:
    """Streaming orchestration — yields ThinkingEvent then OrchestrateResult.

    Same logic as _orchestrate() but emits thinking events between steps
    so the UI can show live progress. The final yield is always an
    OrchestrateResult.
    """
    start_time = time.time()

    # Immediate: yield thinking_start BEFORE any blocking work
    yield ThinkingEvent("start", "🔍 Analyzing your question...")

    # Session setup
    if not (session_id and session_exists(session_id)):
        session_id = create_session()

    add_message(session_id, "user", query)
    history = get_history(session_id, limit=20)

    # Step 1: Intent classification (1 LLM call)
    yield ThinkingEvent("classify", "Classifying intent...")
    intent_result = classify_intent(query, history=history)
    intent = intent_result.intent

    slots_detail = ""
    if intent_result.extracted_slots:
        slots = intent_result.extracted_slots
        parts = []
        if slots.category:
            parts.append(f"category={slots.category}")
        if slots.color:
            parts.append(f"color={slots.color}")
        if slots.fabric:
            parts.append(f"fabric={slots.fabric}")
        if slots.fit:
            parts.append(f"fit={slots.fit}")
        slots_detail = f" | Slots: {', '.join(parts)}" if parts else ""

    yield ThinkingEvent(
        "classify_done",
        f"Intent: {intent} (confidence: {intent_result.confidence:.2f}){slots_detail}",
    )

    # Step 2: Out-of-scope — early exit
    if intent == "out_of_scope":
        add_message(session_id, "assistant", OUT_OF_SCOPE_RESPONSE)
        yield ThinkingEvent("done", f"Out of scope — {time.time() - start_time:.1f}s")
        yield OrchestrateResult(
            intent="out_of_scope",
            session_id=session_id,
            clarification=OUT_OF_SCOPE_RESPONSE,
            history=history,
            filters=intent_result.filters,
        )
        return

    # Step 3: Slot gate + search query resolution
    search_query, clarification = _resolve_search_query(
        intent, intent_result, session_id, history,
    )

    if clarification:
        add_message(session_id, "assistant", clarification)
        yield ThinkingEvent("done", f"Need more information — {time.time() - start_time:.1f}s")
        yield OrchestrateResult(
            intent="clarification" if intent == "text_search" else "unclear",
            session_id=session_id,
            clarification=clarification,
            reasoning=f"Clarification needed for '{intent}'.",
            history=history,
            filters=intent_result.filters,
        )
        return

    # Fallback search query
    if not search_query:
        search_query = query

    # Step 4: Log + preferences
    log_query(session_id, query, intent, intent_result.filters)
    preferences = get_preferences(session_id)

    # Step 5: Route & execute search (0 LLM)
    yield ThinkingEvent("search", f"Searching: '{search_query[:50]}'...")
    products, reasoning = _route_and_execute(
        intent=intent,
        search_query=search_query,
        session_id=session_id,
        filters=intent_result.filters,
    )
    yield ThinkingEvent(
        "search_done",
        f"Tìm thấy {len(products)} sản phẩm — reranking...",
    )

    elapsed = time.time() - start_time
    yield ThinkingEvent("done", f"Hoàn tất — {elapsed:.1f}s")

    yield OrchestrateResult(
        intent=intent,
        session_id=session_id,
        products=products,
        search_query=search_query,
        reasoning=reasoning,
        preferences=preferences,
        history=history,
        filters=intent_result.filters,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def chat(
    query: str,
    session_id: Optional[str] = None,
) -> AgentResponse:
    """Main agent entry point — direct routing orchestrator.

    Orchestrates: intent → slot gate → route & search → synthesize.
    Typically costs 1-2 LLM calls (intent + synthesis).
    """
    result = _orchestrate(query, session_id)

    # Early return for clarification / out-of-scope
    if result.clarification:
        return AgentResponse(
            answer=result.clarification,
            session_id=result.session_id,
            intent=result.intent,
            reasoning=result.reasoning,
        )

    # Synthesize response (1 LLM call)
    answer, styling = _synthesize_response(
        query=query,
        products=result.products,
        history=result.history,
        intent=result.intent,
        preferences=result.preferences,
    )

    # Convert NodeWithScore → ProductResult
    product_results = [
        ProductResult(
            image_id=p.image_id,
            image_path=p.image_path,
            label=p.label,
            color=p.color,
            caption=p.caption,
            score=p.score,
        )
        for p in result.products
    ]

    add_message(result.session_id, "assistant", answer)

    return AgentResponse(
        answer=answer,
        products=product_results,
        styling_suggestion=styling,
        reasoning=result.reasoning,
        session_id=result.session_id,
        intent=result.intent,
    )


def _count_clarification_turns(history: list[Message]) -> int:
    """Count consecutive clarification turns (assistant messages that are questions)."""
    count = 0
    for msg in reversed(history):
        if msg.role == "assistant":
            if "?" in msg.content or "không?" in msg.content:
                count += 1
            else:
                break
        elif msg.role == "user":
            continue
    return count


# ---------------------------------------------------------------------------
# Streaming chat entry point
# ---------------------------------------------------------------------------

def chat_stream(
    query: str,
    session_id: Optional[str] = None,
) -> Generator:
    """Streaming variant of ``chat()`` — yields SSE-formatted events.

    Event types:
    - ``event: thinking_start``  → ``data: {"text": "..."}``
    - ``event: thinking_step``   → ``data: {"step": "...", "detail": "..."}``
    - ``event: thinking_end``    → ``data: {"duration_ms": ...}``
    - ``event: model_thinking``  → ``data: {"text": "..."}``
    - ``event: token``           → ``data: {"text": "..."}``
    - ``event: clarification``   → ``data: {"text": "...", "intent": "..."}``
    - ``event: products``        → ``data: {"products": [...]}``
    - ``event: done``            → ``data: {"session_id": "...", "intent": "...", "styling": "..."}``
    """
    orchestrate_start = time.time()
    result = None

    # Consume orchestration stream — emit thinking events as they arrive
    for event in _orchestrate_stream(query, session_id):
        if isinstance(event, ThinkingEvent):
            if event.step == "start":
                yield _sse("thinking_start", {"text": event.detail})
            elif event.step == "done":
                duration_ms = int((time.time() - orchestrate_start) * 1000)
                yield _sse("thinking_end", {"duration_ms": duration_ms})
            else:
                yield _sse("thinking_step", {
                    "step": event.step,
                    "detail": event.detail,
                })
        elif isinstance(event, OrchestrateResult):
            result = event

    if result is None:
        yield _sse("done", {"session_id": "", "intent": "error", "styling": ""})
        return

    # Early return for clarification / out-of-scope
    if result.clarification:
        event_intent = result.intent
        yield _sse("clarification", {"text": result.clarification, "intent": event_intent})
        yield _sse("done", {"session_id": result.session_id, "intent": event_intent, "styling": ""})
        return

    # Emit product cards
    product_dicts = [
        {
            "image_id": p.image_id,
            "image_path": p.image_path,
            "label": p.label,
            "color": p.color,
            "caption": p.caption[:100],
            "score": round(p.score, 4),
        }
        for p in result.products
    ]
    yield _sse("products", {"products": product_dicts})

    # Stream synthesis tokens — separate thinking vs response
    full_text_parts: list[str] = []
    for chunk in _synthesize_response_stream(
        query=query,
        products=result.products,
        history=result.history,
        intent=result.intent,
        preferences=result.preferences,
    ):
        if isinstance(chunk, ThinkingToken):
            yield _sse("model_thinking", {"text": chunk.text})
        elif isinstance(chunk, ResponseToken):
            full_text_parts.append(chunk.text)
            yield _sse("token", {"text": chunk.text})
        else:
            # Fallback for plain strings (shouldn't happen but defensive)
            full_text_parts.append(str(chunk))
            yield _sse("token", {"text": str(chunk)})

    full_text = "".join(full_text_parts)
    styling = _extract_styling_from_text(full_text)

    add_message(result.session_id, "assistant", full_text)

    yield _sse("done", {
        "session_id": result.session_id,
        "intent": result.intent,
        "styling": styling,
    })


def _sse(event: str, data: dict) -> str:
    """Format a single Server-Sent Event line."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
