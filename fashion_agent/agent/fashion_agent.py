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
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Generator, Optional, Union

from agent.utils import parse_llm_json, fallback_text_response, format_history_text
from agent.prompts import (
    SYNTHESIS_PROMPT,
    STREAM_SYNTHESIS_PROMPT,
    STREAM_SYNTHESIS_PROMPT_AGENTIC,
    detect_language,
    _LANG_NAMES,
)
from shared.llm import get_client, LLMClient, TokenUsage

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
    save_selected_items,
    get_selected_items,
    get_session_model,
    get_session_gender,
    get_last_click_position,
    log_token_usage,
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
    tokens: Optional[TokenUsage] = None  # token usage for this step


@dataclass
class ThinkingToken:
    """Gemini model thinking content (thought=True)."""

    text: str


@dataclass
class ResponseToken:
    """Gemini model response content (regular text)."""

    text: str


# Union type for synthesis stream output
SynthesisChunk = Union[ThinkingToken, ResponseToken, TokenUsage]


# ---------------------------------------------------------------------------
# Synthesis context builder (shared between batch & stream)
# ---------------------------------------------------------------------------


def _build_synthesis_context(
    query: str,
    products: list,
    history: list[Message],
    preferences: Optional[dict] = None,
    session_id: Optional[str] = None,
) -> dict[str, str]:
    """Format products, history, preferences, language, and gender context for synthesis.

    Returns:
        Dict with keys: ``products_text``, ``history_text``, ``preferences_text``,
        ``language``, ``gender_context``, ``num_results``, ``cta_example``.
    """
    # Format products
    products_lines = []
    for i, p in enumerate(products, 1):
        products_lines.append(
            f"{i}. {p.label} | Color: {p.color} | Caption: {p.caption}"
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

    lang = detect_language(query)
    lang_name = _LANG_NAMES.get(lang, "English")

    if lang == "vi":
        cta_example = f"👉 Gõ một số (1-{len(products)}) để chọn sản phẩm bạn thích!"
    elif lang == "es":
        cta_example = f"👉 ¡Escribe un número (1-{len(products)}) para seleccionar tu favorito!"
    else:
        cta_example = f"👉 Type a number (1-{len(products)}) to select your favorite!"

    # Gender context: inject only when hint is enabled and gender is known
    gender_context = ""
    if session_id:
        try:
            gender, hint_enabled = get_session_gender(session_id)
            if hint_enabled and gender:
                wardrobe = "menswear" if gender == "male" else "womenswear"
                gender_context = (
                    f"\nUser profile: gender = {gender}. "
                    f"Prioritize {wardrobe} appropriate items.\n"
                )
        except Exception:
            pass  # Non-fatal — continue without gender hint

    return {
        "products_text": products_text,
        "history_text": history_text,
        "preferences_text": preferences_text,
        "language": lang_name,
        "gender_context": gender_context,
        "num_results": len(products),
        "cta_example": cta_example,
    }


# ---------------------------------------------------------------------------
# Gemini synthesis
# ---------------------------------------------------------------------------



def _synthesize_response(
    query: str,
    products: list[NodeWithScore],
    history: list[Message],
    intent: str,
    client: LLMClient,
    preferences: Optional[dict] = None,
    session_id: Optional[str] = None,
) -> tuple[str, str]:
    """Use Gemini/GPT/Claude to synthesize a natural response from search results."""
    ctx = _build_synthesis_context(query, products, history, preferences, session_id)
    prompt = SYNTHESIS_PROMPT.format(query=query, **ctx)
    try:
        response_text = client.generate(prompt)
        data = parse_llm_json(response_text)
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
    client: LLMClient,
    preferences: Optional[dict] = None,
    session_id: Optional[str] = None,
) -> Generator:
    """Streaming version of synthesis — yields ``SynthesisChunk`` instances."""
    ctx = _build_synthesis_context(query, products, history, preferences, session_id)
    prompt = STREAM_SYNTHESIS_PROMPT.format(query=query, **ctx)
    try:
        gen = client.stream(prompt)
        while True:
            try:
                text = next(gen)
                yield ResponseToken(text)
            except StopIteration as e:
                usage = e.value
                if usage:
                    usage.call_name = "synthesis"
                    yield usage
                break
    except Exception as e:
        logger.error(f"Synthesis stream error: {e}")
        yield ResponseToken(fallback_text_response(products))

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

OUT_OF_SCOPE_RESPONSE = {
    "en": (
        "Sorry, I only help with fashion search and styling advice. "
        "Would you like to look for any outfit?"
    ),
    "vi": (
        "Xin lỗi, tôi chỉ hỗ trợ tìm kiếm thời trang và tư vấn phối đồ. "
        "Bạn có muốn tìm trang phục nào không?"
    ),
    "es": (
        "Lo siento, solo puedo ayudarte con búsqueda de moda y consejos de estilo. "
        "¿Te gustaría buscar alguna prenda?"
    ),
}

MAX_CLARIFICATION_TURNS = 3

# In-memory storage for accumulated slots per session (auto-evicted after 30 min)
# Key: session_id, Value: ExtractedSlots
from cachetools import TTLCache

_session_accumulated_slots: TTLCache = TTLCache(maxsize=100, ttl=1800)

# Product selection caches
_session_last_results: TTLCache = TTLCache(maxsize=1000, ttl=1800)   # 30 min
_session_pending_selection: TTLCache = TTLCache(maxsize=1000, ttl=300)  # 5 min


@dataclass
class PendingSelection:
    """Items awaiting user confirmation before saving."""
    items: list[ProductResult]
    search_query: str
    numbers: list[int]


# Keyword sets for confirm/reject detection (0 LLM calls)
CONFIRM_KEYWORDS = {
    "yes", "ok", "okay", "confirm", "đúng", "đúng rồi", "oke",
    "sure", "yep", "yeah", "đồng ý", "lưu", "save", "y", "ừ",
    "uh", "uh huh", "được", "chốt", "vâng", "vâng ạ", "dạ", "da",
    "chốt đơn", "chuẩn", "có", "có ạ",
    # Spanish
    "sí", "si", "confirmar", "guardar", "claro", "dale", "bueno", "de acuerdo",
}
REJECT_KEYWORDS = {
    "no", "không", "cancel", "hủy", "thôi", "skip", "n",
    "nope", "bỏ", "không lưu",
    # Spanish
    "cancelar", "cancela", "omitir", "quitar", "no gracias",
}


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
    query: str = "",
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
                    missing_slots=missing, slots=accumulated, query=query,
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
        
    model_name = get_session_model(session_id)
    client = get_client(model_name)

    add_message(session_id, "user", query)
    history = get_history(session_id, limit=20)

    # --- Product selection: keyword confirm/reject check (0 LLM calls) ---
    if session_id in _session_pending_selection:
        normalized = query.strip().lower()
        if normalized in CONFIRM_KEYWORDS:
            yield from _handle_confirm(session_id, query)
            return
        if normalized in REJECT_KEYWORDS:
            yield from _handle_reject(session_id, query)
            return
        # Not a keyword match — ask for clarification instead of clearing
        yield from _handle_ambiguous_response(session_id, query)
        return

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

    # Build intent token info
    intent_tokens = TokenUsage(
        input_tokens=intent_result.input_tokens,
        output_tokens=intent_result.output_tokens,
        call_name="intent",
    )
    token_detail = f" | 📊 Intent: {intent_tokens.input_tokens} in / {intent_tokens.output_tokens} out"

    yield ThinkingEvent(
        "classify_done",
        f"Intent: {intent} (confidence: {intent_result.confidence:.2f}){slots_detail}{token_detail}",
        tokens=intent_tokens,
    )

    # Persist intent token usage to DB (non-fatal — never kill the stream)
    try:
        log_token_usage(
            session_id=session_id,
            call_name="intent",
            model_name=client.model_name,
            input_tokens=intent_tokens.input_tokens,
            output_tokens=intent_tokens.output_tokens,
        )
    except Exception as _tok_err:
        logger.debug("Token logging failed (intent): %s", _tok_err)

    # Step 2: Out-of-scope — early exit
    if intent == "out_of_scope":
        lang = detect_language(query)
        msg_text = OUT_OF_SCOPE_RESPONSE.get(lang, OUT_OF_SCOPE_RESPONSE["en"])
        add_message(session_id, "assistant", msg_text)
        yield ThinkingEvent("done", f"Out of scope — {time.time() - start_time:.1f}s")
        yield OrchestrateResult(
            intent="out_of_scope",
            session_id=session_id,
            clarification=msg_text,
            history=history,
            filters=intent_result.filters,
        )
        return

    # Step 2b: Product selection — early exit (0 extra LLM calls)
    if intent == "product_select":
        selected_nums = intent_result.extracted_slots.selected_numbers
        yield ThinkingEvent("done", f"Product selection — {time.time() - start_time:.1f}s")
        yield from _handle_product_select(
            session_id, selected_nums, intent_result.refined_query or query, query,
        )
        return

    # Step 2c: View selections — early exit (0 LLM calls)
    if intent == "view_selections":
        yield ThinkingEvent("done", f"View selections — {time.time() - start_time:.1f}s")
        yield from _handle_view_selections(session_id, query)
        return

    # Step 3: Slot gate + search query resolution
    search_query, clarification = _resolve_search_query(
        intent, intent_result, session_id, history, query,
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

    # Cache search results for product selection
    if products:
        cached_products = [
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
        _session_last_results[session_id] = cached_products

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
# Product selection handlers
# ---------------------------------------------------------------------------


def _handle_product_select(
    session_id: str,
    selected_numbers: list[int],
    search_query: str,
    query: str,
) -> Generator:
    """Validate selections against cached results and create pending confirmation."""
    lang = detect_language(query)
    cached_results = _session_last_results.get(session_id)
    if not cached_results:
        if lang == "vi":
            text = "⚠️ Không có kết quả tìm kiếm gần đây. Vui lòng tìm kiếm sản phẩm trước!"
        elif lang == "es":
            text = "⚠️ No hay resultados recientes. ¡Por favor busca productos primero!"
        else:
            text = "⚠️ No recent search results. Please search for products first!"
        yield _sse("clarification", {
            "text": text,
            "intent": "product_select",
        })
        return

    if not selected_numbers:
        if lang == "vi":
            text = f"Bạn muốn chọn sản phẩm nào? Vui lòng nhập một số (1-{len(cached_results)})."
        elif lang == "es":
            text = f"¿Qué artículo deseas? Por favor indica un número (1-{len(cached_results)})."
        else:
            text = f"Which item would you like? Please specify a number (1-{len(cached_results)})."
        yield _sse("clarification", {
            "text": text,
            "intent": "product_select",
        })
        return

    max_idx = len(cached_results)
    valid_items = []
    invalid_nums = []

    for num in selected_numbers:
        if 1 <= num <= max_idx:
            valid_items.append(cached_results[num - 1])  # 0-indexed
        else:
            invalid_nums.append(num)

    if not valid_items:
        if lang == "vi":
            text = f"❌ Số không hợp lệ! Vui lòng chọn từ 1 đến {max_idx}."
        elif lang == "es":
            text = f"❌ ¡Selección inválida! Por favor elige entre 1 y {max_idx}."
        else:
            text = f"❌ Invalid selection! Please choose between 1 and {max_idx}."
        yield _sse("clarification", {
            "text": text,
            "intent": "product_select",
        })
        return

    # Create pending selection
    pending = PendingSelection(
        items=valid_items, search_query=search_query, numbers=selected_numbers,
    )
    _session_pending_selection[session_id] = pending

    # Build confirmation preview
    if lang == "vi":
        lines = ["✅ **Bạn đã chọn:**\n"]
    elif lang == "es":
        lines = ["✅ **Has seleccionado:**\n"]
    else:
        lines = ["✅ **You selected:**\n"]
        
    for i, item in enumerate(valid_items, 1):
        color_str = f" — {item.color}" if item.color else ""
        lines.append(f"{i}. **{item.label}**{color_str}")
        if item.caption:
            lines.append(f"   _{item.caption}_")
        # Product image
        if item.image_path:
            filename = os.path.basename(item.image_path)
            lines.append(f"\n![{item.label}](/api/images/{filename})\n")
    
    if invalid_nums:
        if lang == "vi":
            lines.append(f"\n⚠️ Bỏ qua số không hợp lệ: {', '.join(str(n) for n in invalid_nums)} (chỉ từ 1-{max_idx})")
        elif lang == "es":
            lines.append(f"\n⚠️ Omitidos inválidos: {', '.join(str(n) for n in invalid_nums)} (solo entre 1-{max_idx})")
        else:
            lines.append(f"\n⚠️ Skipped invalid: {', '.join(str(n) for n in invalid_nums)} (only 1-{max_idx})")

    if lang == "vi":
        lines.append("\n**Xác nhận lưu? (có/không)**")
    elif lang == "es":
        lines.append("\n**¿Confirmar? (sí/no)**")
    else:
        lines.append("\n**Confirm? (yes/no)**")

    preview_text = "\n".join(lines)
    add_message(session_id, "assistant", preview_text)

    yield _sse("selection_confirm", {
        "text": preview_text,
        "items": [
            {
                "label": it.label,
                "color": it.color,
                "caption": it.caption,
                "image_path": it.image_path,
            }
            for it in valid_items
        ],
    })
    yield _sse("done", {
        "session_id": session_id,
        "intent": "product_select",
        "styling": "",
    })


def _handle_confirm(session_id: str, query: str) -> Generator:
    """Save pending items to DB and clear pending state."""
    lang = detect_language(query)
    pending = _session_pending_selection.pop(session_id, None)
    if not pending:
        text = (
            "Nothing to confirm. Please select products first." if lang == "en"
            else "Không có gì để lưu. Vui lòng chọn sản phẩm trước."
        )
        yield _sse("clarification", {
            "text": text,
            "intent": "product_confirm",
        })
        return

    items_to_save = []
    for it in pending.items:
        position = get_last_click_position(session_id, it.image_id)
        items_to_save.append({
            "image_id": it.image_id,
            "label": it.label,
            "color": it.color,
            "caption": it.caption,
            "image_path": it.image_path,
            "search_query": pending.search_query,
            "position": position,
        })
    inserted = save_selected_items(session_id, items_to_save)
    skipped = len(items_to_save) - inserted

    if lang == "vi":
        if inserted == 1:
            parts = [f"💾 **Đã lưu {inserted} sản phẩm!**"]
        else:
            parts = [f"💾 **Đã lưu {inserted} sản phẩm!**"]
        if skipped > 0:
            parts.append(f"({skipped} sản phẩm đã có trong danh sách)")
        parts.append('\n\nBạn có muốn tìm thêm gì không?')
        parts.append('Mình ở đây để giúp bạn tìm kiếm.')
        parts.append('Hoặc bạn có thể đặt hàng trong giỏ hàng.')
    elif lang == "es":
        if inserted == 1:
            parts = [f"💾 **¡{inserted} producto guardado!**"]
        else:
            parts = [f"💾 **¡{inserted} productos guardados!**"]
        if skipped > 0:
            parts.append(f"({skipped} ya estaban en tus selecciones)")
        parts.append('\n\n¿Quieres algo más?')
        parts.append('Estoy aquí para ayudarte a encontrar.')
        parts.append('O puedes hacer un pedido en el carrito.')
    else:
        if inserted == 1:
            parts = [f"💾 **Saved {inserted} product!**"]
        else:
            parts = [f"💾 **Saved {inserted} products!**"]
        if skipped > 0:
            parts.append(f"({skipped} already in your selections)")
        parts.append('\n\nDo you want anything else?')
        parts.append("I'm here to help you to find.")
        parts.append('Or you can make an order in the cart.')
    text = " ".join(parts)

    add_message(session_id, "assistant", text)
    yield _sse("selection_saved", {"text": text, "inserted": inserted, "skipped": skipped})
    yield _sse("done", {"session_id": session_id, "intent": "product_confirm", "styling": ""})


def _handle_reject(session_id: str, query: str) -> Generator:
    """Discard pending selection."""
    lang = detect_language(query)
    _session_pending_selection.pop(session_id, None)

    cached_results = _session_last_results.get(session_id)

    if not cached_results:
        if lang == "vi":
            text = "❌ Đã hủy chọn. Vui lòng tìm kiếm lại."
        elif lang == "es":
            text = "❌ Selección cancelada. Por favor busca de nuevo."
        else:
            text = "❌ Selection cancelled. Please search again."
        add_message(session_id, "assistant", text)
        yield _sse("selection_cancelled", {"text": text})
        yield _sse("done", {"session_id": session_id, "intent": "product_reject", "styling": ""})
        return

    if lang == "vi":
        lines = ["❌ Đã hủy chọn. Dưới đây là các sản phẩm. Gõ một số khác để chọn lại nhé!\n"]
    elif lang == "es":
        lines = ["❌ Selección cancelada. Aquí están los artículos. ¡Escribe un número diferente para seleccionar otro!\n"]
    else:
        lines = ["❌ Selection cancelled. Here are the items again. Type a number to select a different one!\n"]

    for i, item in enumerate(cached_results, 1):
        color_str = f" — {item.color}" if item.color else ""
        lines.append(f"{i}. **{item.label}**{color_str}")

    text = "\n".join(lines)
    add_message(session_id, "assistant", text)
    yield _sse("selection_cancelled", {"text": text})
    yield _sse("done", {"session_id": session_id, "intent": "product_reject", "styling": ""})


def _handle_ambiguous_response(session_id: str, query: str) -> Generator:
    """Handle ambiguous responses when pending selection exists — ask for confirmation."""
    lang = detect_language(query)
    pending = _session_pending_selection.get(session_id)
    
    if not pending:
        # Should not happen, but handle gracefully
        text = (
            "No pending selection. Please search for products first." if lang == "en"
            else "Không có sản phẩm đang chờ. Vui lòng tìm kiếm trước."
        )
        yield _sse("clarification", {"text": text, "intent": "product_confirm"})
        return

    # Re-display pending items with clarification prompt
    if lang == "vi":
        lines = ["🤔 **Vui lòng xác nhận:**\n"]
    elif lang == "es":
        lines = ["🤔 **Por favor confirma:**\n"]
    else:
        lines = ["🤔 **Please confirm:**\n"]

    for i, item in enumerate(pending.items, 1):
        color_str = f" — {item.color}" if item.color else ""
        lines.append(f"{i}. **{item.label}**{color_str}")
        if item.caption:
            lines.append(f"   _{item.caption}_")

    if lang == "vi":
        lines.append('\n**Gõ "có" hoặc "yes" để lưu vào giỏ hàng**')
        lines.append('**Gõ "không" hoặc "no" để hủy**')
    elif lang == "es":
        lines.append('\n**Escribe "sí" o "yes" para guardar en el carrito**')
        lines.append('**Escribe "no" para cancelar**')
    else:
        lines.append('\n**Type "yes" or "ok" to save to cart**')
        lines.append('**Type "no" to cancel**')

    text = "\n".join(lines)
    add_message(session_id, "assistant", text)
    yield _sse("clarification", {"text": text, "intent": "product_confirm"})
    yield _sse("done", {"session_id": session_id, "intent": "product_confirm", "styling": ""})


def _handle_view_selections(session_id: str, query: str) -> Generator:
    """Retrieve and display all saved selections for the session."""
    lang = detect_language(query)
    items = get_selected_items(session_id)
    
    if not items:
        if lang == "vi":
            text = "📋 Bạn chưa chọn sản phẩm nào. Hãy tìm kiếm và chọn sản phẩm yêu thích nhé!"
        elif lang == "es":
            text = "📋 Aún no has seleccionado nada. ¡Busca productos y elige tus favoritos!"
        else:
            text = "📋 You haven't selected anything yet. Search for products and pick your favorites!"
    else:
        if lang == "vi":
            lines = [f"📋 **Sản phẩm đã chọn ({len(items)}):**\n"]
        elif lang == "es":
            lines = [f"📋 **Tus Selecciones ({len(items)} artículos):**\n"]
        else:
            lines = [f"📋 **Your Selections ({len(items)} items):**\n"]
            
        for i, it in enumerate(items, 1):
            color_str = f" — {it['color']}" if it.get('color') else ""
            lines.append(f"{i}. **{it['label']}**{color_str}")
            if it.get('caption'):
                lines.append(f"   _{it['caption']}_")
            if it.get('search_query'):
                if lang == "vi":
                    found_prefix = "Tìm với:"
                elif lang == "es":
                    found_prefix = "Encontrado con:"
                else:
                    found_prefix = "Found via:"
                lines.append(f"   🔍 {found_prefix} _{it['search_query']}_")
        text = "\n".join(lines)

    add_message(session_id, "assistant", text)
    yield _sse("selections_list", {"text": text, "count": len(items)})
    yield _sse("done", {"session_id": session_id, "intent": "view_selections", "styling": ""})


# ---------------------------------------------------------------------------
# Orchestration mode helpers
# ---------------------------------------------------------------------------


def _get_orchestration_mode(model_id: str) -> tuple[str, str, str]:
    """Map a session model ID to (mode, orchestrator_model, synthesizer_model).

    Mode A (Gemini): direct routing + Gemini synthesis.
    Mode B (GPT-4o): Gemini orchestrates (agentic) + GPT-4o synthesizes.
    Mode C (Claude): GPT-4o orchestrates (agentic) + Claude synthesizes.

    Returns:
        Tuple of (mode, orchestrator_model, synthesizer_model).
    """
    if model_id.startswith("gpt-"):
        return "agentic", "gemini-2.0-flash", model_id
    elif model_id.startswith("claude-"):
        return "agentic", "gpt-4o", model_id
    else:
        return "direct", "fixed", model_id


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
    client = get_client(get_session_model(result.session_id))
    answer, styling = _synthesize_response(
        query=query,
        products=result.products,
        history=result.history,
        intent=result.intent,
        client=client,
        preferences=result.preferences,
        session_id=result.session_id,
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
    intent_tokens = TokenUsage()  # collect intent tokens

    # Consume orchestration stream — emit thinking events as they arrive
    for event in _orchestrate_stream(query, session_id):
        if isinstance(event, str):
            # Raw SSE from selection handlers — pass through directly
            yield event
        elif isinstance(event, ThinkingEvent):
            # Collect token info from thinking events
            if event.tokens:
                intent_tokens = event.tokens
            if event.step == "start":
                yield _sse("thinking_start", {"text": event.detail})
            elif event.step == "done":
                duration_ms = int((time.time() - orchestrate_start) * 1000)
                yield _sse("thinking_end", {
                    "duration_ms": duration_ms,
                    "input_tokens": intent_tokens.input_tokens,
                    "output_tokens": intent_tokens.output_tokens,
                })
            else:
                yield _sse("thinking_step", {
                    "step": event.step,
                    "detail": event.detail,
                })
        elif isinstance(event, OrchestrateResult):
            result = event

    if result is None:
        # Selection handlers don't yield OrchestrateResult — that's OK
        # Check if we already yielded a 'done' event via raw SSE
        return

    # Early return for clarification / out-of-scope
    if result.clarification:
        event_intent = result.intent
        yield _sse("clarification", {"text": result.clarification, "intent": event_intent})
        yield _sse("done", {
            "session_id": result.session_id,
            "intent": event_intent,
            "styling": "",
            "total_input_tokens": intent_tokens.input_tokens,
            "total_output_tokens": intent_tokens.output_tokens,
        })
        return

    # Emit product cards (only for direct / after agentic orchestration)
    product_dicts = [
        {
            "image_id": p.image_id,
            "image_path": p.image_path,
            "label": p.label,
            "color": p.color,
            "caption": p.caption,
            "score": round(p.score, 4),
        }
        for p in result.products
    ]
    yield _sse("products", {"products": product_dicts})

    # Determine orchestration mode and pick synthesizer
    preferred_model = get_session_model(result.session_id)
    orch_mode, orchestrator_model, synthesizer_model = _get_orchestration_mode(preferred_model)

    # Collect synthesis tokens and tool call metadata
    full_text_parts: list[str] = []
    synthesis_tokens = TokenUsage()
    tool_calls_for_log: list[dict] = []
    orchestrator_in_tokens = 0
    orchestrator_out_tokens = 0

    if orch_mode == "direct":
        # Mode A: regular stream synthesis (existing path)
        client = get_client(preferred_model)
        for chunk in _synthesize_response_stream(
            query=query,
            products=result.products,
            history=result.history,
            intent=result.intent,
            client=client,
            preferences=result.preferences,
            session_id=result.session_id,
        ):
            if isinstance(chunk, ThinkingToken):
                yield _sse("model_thinking", {"text": chunk.text})
            elif isinstance(chunk, ResponseToken):
                full_text_parts.append(chunk.text)
                yield _sse("token", {"text": chunk.text})
            elif isinstance(chunk, TokenUsage):
                synthesis_tokens = chunk
            else:
                full_text_parts.append(str(chunk))
                yield _sse("token", {"text": str(chunk)})
    else:
        # Mode B (Gemini orchestrates) or Mode C (GPT orchestrates)
        from agent.agentic_orchestrator import (
            orchestrate_with_gemini,
            orchestrate_with_gpt,
        )
        from agent.utils import format_history_text
        from agent.prompts import _LANG_NAMES

        history_text = format_history_text(result.history, limit=4)
        gender, gender_hint = None, False
        try:
            from agent.memory import get_session_gender
            gender, gender_hint = get_session_gender(result.session_id)
        except Exception:
            pass

        yield _sse("thinking_step", {"step": "agentic_start", "detail": f"{orchestrator_model} orchestrating..."})

        if orchestrator_model.startswith("gemini"):
            orch_result = orchestrate_with_gemini(
                query=query,
                history_text=history_text,
                gender=gender,
                gender_hint=gender_hint,
            )
        else:
            orch_result = orchestrate_with_gpt(
                query=query,
                history_text=history_text,
                gender=gender,
                gender_hint=gender_hint,
            )

        tool_calls_for_log = [tc.to_dict() for tc in orch_result.tool_calls]
        orchestrator_in_tokens = orch_result.orchestrator_input_tokens
        orchestrator_out_tokens = orch_result.orchestrator_output_tokens

        yield _sse("thinking_step", {"step": "agentic_done", "detail": f"{len(orch_result.tool_calls)} tool calls"})

        # Build synthesis context using agentic tool results
        lang = detect_language(query)
        lang_name = _LANG_NAMES.get(lang, "English")
        num_products = len(orch_result.products)
        if lang == "vi":
            cta = f"👉 Gõ một số (1-{num_products}) để chọn sản phẩm bạn thích!"
        elif lang == "es":
            cta = f"👉 ¡Escribe un número (1-{num_products}) para seleccionar tu favorito!"
        else:
            cta = f"👉 Type a number (1-{num_products}) to select your favorite!"

        gender_ctx = ""
        if gender_hint and gender:
            wardrobe = "menswear" if gender == "male" else "womenswear"
            gender_ctx = f"\nUser profile: gender = {gender}. Prioritize {wardrobe} appropriate items.\n"

        prefs = result.preferences or {}
        prefs_parts = []
        if prefs.get("preferred_colors"):
            prefs_parts.append(f"Preferred colors: {', '.join(prefs['preferred_colors'])}")
        if prefs.get("preferred_categories"):
            prefs_parts.append(f"Preferred categories: {', '.join(prefs['preferred_categories'])}")
        preferences_text = "; ".join(prefs_parts) or "No preferences yet."

        prompt = STREAM_SYNTHESIS_PROMPT_AGENTIC.format(
            language=lang_name,
            gender_context=gender_ctx,
            query=query,
            tool_results=orch_result.tool_results_text,
            preferences_text=preferences_text,
            history_text=format_history_text(result.history, limit=4),
            cta_example=cta,
        )

        synth_client = get_client(synthesizer_model)
        try:
            gen = synth_client.stream(prompt)
            while True:
                try:
                    chunk = next(gen)
                    if isinstance(chunk, str):
                        full_text_parts.append(chunk)
                        yield _sse("token", {"text": chunk})
                except StopIteration as e:
                    if isinstance(e.value, TokenUsage):
                        synthesis_tokens = e.value
                    break
        except Exception as _synth_err:
            logger.error("Agentic synthesis failed: %s", _synth_err)
            fallback = "I found some products for you. Please review the results above."
            full_text_parts.append(fallback)
            yield _sse("token", {"text": fallback})

    full_text = "".join(full_text_parts)
    styling = _extract_styling_from_text(full_text)

    add_message(result.session_id, "assistant", full_text)

    # Persist synthesis token usage + orchestration metadata to DB (non-fatal)
    try:
        log_token_usage(
            session_id=result.session_id,
            call_name="synthesis",
            model_name=synthesizer_model,
            input_tokens=synthesis_tokens.input_tokens,
            output_tokens=synthesis_tokens.output_tokens,
            orchestration_mode=orch_mode,
            orchestrator_model=orchestrator_model,
            synthesizer_model=synthesizer_model,
            tool_calls_json=tool_calls_for_log,
            orchestrator_input_tokens=orchestrator_in_tokens,
            orchestrator_output_tokens=orchestrator_out_tokens,
        )
    except Exception as _tok_err:
        logger.debug("Token logging failed (synthesis): %s", _tok_err)

    yield _sse("done", {
        "session_id": result.session_id,
        "intent": result.intent,
        "styling": styling,
        "orchestration_mode": orch_mode,
        "total_input_tokens": intent_tokens.input_tokens + synthesis_tokens.input_tokens + orchestrator_in_tokens,
        "total_output_tokens": intent_tokens.output_tokens + synthesis_tokens.output_tokens + orchestrator_out_tokens,
    })


def _sse(event: str, data: dict) -> str:
    """Format a single Server-Sent Event line."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
