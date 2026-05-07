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

from agent.utils import (
    parse_llm_json, fallback_text_response, format_history_text,
    SUPPORTED_CATEGORIES, _find_category_suggestions,
)
from agent.prompts import (
    SYNTHESIS_PROMPT,
    STREAM_SYNTHESIS_PROMPT,
    detect_language,
    _LANG_NAMES,
    build_unsupported_category_message,
)
from shared.llm import get_client, LLMClient, TokenUsage

from agent.intent_classifier import classify_intent, ClassifiedIntent, ExtractedSlots
from agent.slot_completeness import (
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

# Gender category sets (mirrors analytics.py to avoid circular import)
_MALE_CATEGORIES: frozenset[str] = frozenset({
    "Longsleeve", "T-Shirt", "Shirt", "Hoodie", "Shorts", "Pants", "Blazer", "Polo"
})
_FEMALE_CATEGORIES: frozenset[str] = frozenset({
    "Dress", "Skirt", "Blouse", "Top"
})


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
        cta_example = "👉 Hãy cho tôi biết bạn thích cái nào — tôi sẽ thêm vào giỏ hàng ngay!"
    elif lang == "es":
        cta_example = "👉 Dime cuál te gusta, ¡lo añadiré al carrito!"
    else:
        cta_example = "👉 Tell me which one you like — I'll add it to your cart!"

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
DEFAULT_SEARCH_CONFIDENCE_THRESHOLD = 0.75
_RANKED_SLOT_WEIGHTS = {
    "category": 4,
    "color": 3,
    "style": 2,
    "occasion": 3,
}

# In-memory storage for accumulated slots per session (auto-evicted after 30 min)
# Key: session_id, Value: ExtractedSlots
from cachetools import TTLCache

_session_accumulated_slots: TTLCache = TTLCache(maxsize=100, ttl=1800)
_session_ranked_slots: TTLCache = TTLCache(maxsize=100, ttl=1800)

# Product selection caches
_session_last_results: TTLCache = TTLCache(maxsize=1000, ttl=1800)   # 30 min
_session_pending_selection: TTLCache = TTLCache(maxsize=1000, ttl=300)  # 5 min


def _get_search_confidence_threshold() -> float:
    """Return configured confidence threshold for pre-search gating."""
    raw = os.getenv(
        "SEARCH_CONFIDENCE_THRESHOLD",
        str(DEFAULT_SEARCH_CONFIDENCE_THRESHOLD),
    ).strip()
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_SEARCH_CONFIDENCE_THRESHOLD
    return min(1.0, max(0.0, value))


def _empty_ranked_slots() -> dict[str, str]:
    return {"category": "", "color": "", "style": "", "occasion": ""}


def _normalize_slot_text(value: Optional[str]) -> str:
    return (value or "").strip()


def _merge_ranked_slots(
    session_id: str,
    intent_result: ClassifiedIntent,
    accumulated: ExtractedSlots,
    *,
    reset: bool = False,
) -> dict[str, str]:
    base = _empty_ranked_slots() if reset else {
        **_empty_ranked_slots(),
        **(_session_ranked_slots.get(session_id) or {}),
    }
    filters = intent_result.filters or {}

    category = _normalize_slot_text(accumulated.category) or _normalize_slot_text(
        filters.get("category")
    )
    color = _normalize_slot_text(accumulated.color) or _normalize_slot_text(
        filters.get("color")
    )
    style = _normalize_slot_text(filters.get("style")) or _normalize_slot_text(
        accumulated.aesthetic
    )
    occasion = _normalize_slot_text(filters.get("occasion"))

    if category:
        base["category"] = category
    if color:
        base["color"] = color
    if style:
        base["style"] = style
    if occasion:
        base["occasion"] = occasion

    _session_ranked_slots[session_id] = base
    return base


def _ranked_slot_score(ranked_slots: dict[str, str]) -> int:
    return sum(
        weight
        for slot, weight in _RANKED_SLOT_WEIGHTS.items()
        if _normalize_slot_text(ranked_slots.get(slot))
    )


def _readiness_missing_slots(intent: str, ranked_slots: dict[str, str]) -> list[str]:
    has_category = bool(_normalize_slot_text(ranked_slots.get("category")))
    has_color = bool(_normalize_slot_text(ranked_slots.get("color")))
    has_style = bool(_normalize_slot_text(ranked_slots.get("style")))
    has_occasion = bool(_normalize_slot_text(ranked_slots.get("occasion")))

    if intent == "text_search":
        missing: list[str] = []
        if not has_category:
            missing.append("category")
        if not has_color:
            missing.append("color")
        return missing
    if intent == "outfit_request":
        missing = []
        if not has_occasion:
            missing.append("occasion")
        if not (has_style or has_category):
            missing.append("style_or_category")
        return missing
    if intent == "follow_up":
        if has_category or has_color or has_style or has_occasion:
            return []
        return ["one_of_four"]
    return []


def _is_query_ready(intent: str, ranked_slots: dict[str, str]) -> tuple[bool, list[str]]:
    missing = _readiness_missing_slots(intent, ranked_slots)
    if missing:
        return False, missing

    # Secondary score guard to reduce unnecessary broad retrieval.
    min_score = {
        "text_search": 7,     # category + color baseline
        "outfit_request": 5,  # occasion + one supporting signal
        "follow_up": 2,       # at least one strong signal
    }.get(intent, 0)
    return _ranked_slot_score(ranked_slots) >= min_score, [] if _ranked_slot_score(ranked_slots) >= min_score else ["one_of_four"]


def _build_ranked_clarification_question(
    intent: str,
    query: str,
    missing_slots: list[str],
    *,
    low_confidence: bool = False,
) -> str:
    lang = detect_language(query)
    missing = set(missing_slots)

    if lang == "vi":
        prefix = "Mình cần rõ hơn một chút trước khi tìm kiếm. " if low_confidence else ""
        if intent == "text_search":
            if {"category", "color"}.issubset(missing):
                return prefix + "Bạn muốn loại trang phục nào và màu gì? (ví dụ: áo sơ mi trắng)."
            if "category" in missing:
                return prefix + "Bạn muốn loại trang phục nào? (áo, quần, váy, blazer...)."
            if "color" in missing:
                return prefix + "Bạn muốn màu gì? (đen, trắng, xanh navy...)."
        if intent == "outfit_request":
            if {"occasion", "style_or_category"}.issubset(missing):
                return prefix + "Bạn đi dịp nào và muốn phong cách hoặc loại đồ gì? (ví dụ: hẹn hò, style lịch sự, váy/áo sơ mi)."
            if "occasion" in missing:
                return prefix + "Bạn cần outfit cho dịp nào? (hẹn hò, đi làm, tiệc tối...)."
            if "style_or_category" in missing:
                return prefix + "Bạn thích phong cách nào hoặc loại đồ nào? (casual, lịch sự, váy, áo sơ mi...)."
        return prefix + "Bạn cho mình thêm một chi tiết nhé: loại đồ, màu, phong cách hoặc dịp sử dụng."

    if lang == "es":
        prefix = "Necesito un poco más de detalle antes de buscar. " if low_confidence else ""
        if intent == "text_search":
            if {"category", "color"}.issubset(missing):
                return prefix + "¿Qué tipo de prenda y qué color prefieres? (ej.: camisa blanca)."
            if "category" in missing:
                return prefix + "¿Qué tipo de prenda buscas? (camisa, pantalón, vestido, blazer...)."
            if "color" in missing:
                return prefix + "¿Qué color prefieres? (negro, blanco, azul marino...)."
        if intent == "outfit_request":
            if {"occasion", "style_or_category"}.issubset(missing):
                return prefix + "¿Para qué ocasión y qué estilo o tipo de prenda prefieres?"
            if "occasion" in missing:
                return prefix + "¿Para qué ocasión necesitas el outfit? (cita, trabajo, fiesta...)."
            if "style_or_category" in missing:
                return prefix + "¿Qué estilo o tipo de prenda prefieres? (casual, formal, vestido, camisa...)."
        return prefix + "Compárteme un detalle más: prenda, color, estilo u ocasión."

    prefix = "I need a bit more detail before searching. " if low_confidence else ""
    if intent == "text_search":
        if {"category", "color"}.issubset(missing):
            return prefix + "What clothing type and color do you want? (e.g., white shirt)."
        if "category" in missing:
            return prefix + "What clothing type are you looking for? (shirt, pants, dress, blazer...)."
        if "color" in missing:
            return prefix + "Which color do you prefer? (black, white, navy...)."
    if intent == "outfit_request":
        if {"occasion", "style_or_category"}.issubset(missing):
            return prefix + "What occasion is this for, and what style or clothing type do you want?"
        if "occasion" in missing:
            return prefix + "What occasion is this outfit for? (date, office, party...)."
        if "style_or_category" in missing:
            return prefix + "What style or clothing type do you prefer? (casual, formal, dress, shirt...)."
    return prefix + "Please add one more detail: clothing type, color, style, or occasion."


@dataclass
class PendingSelection:
    """Items awaiting user confirmation before saving."""
    items: list[ProductResult]
    search_query: str
    numbers: list[int]
    path_mode: str = "path1"


def cache_external_results(
    session_id: str,
    path_mode: str,
    products: list[dict],
) -> None:
    """Cache externally produced products (e.g. PATH 2 endpoint) for selection flow."""
    normalized_mode = "path2" if path_mode == "path2" else "path1"
    cached_products = [
        ProductResult(
            image_id=p.get("image_id", ""),
            image_path=p.get("image_path", ""),
            label=p.get("label", ""),
            color=p.get("color", ""),
            caption=p.get("caption", ""),
            score=float(p.get("score", 0.0) or 0.0),
        )
        for p in products
    ]
    _session_last_results[session_id] = {
        "path_mode": normalized_mode,
        "products": cached_products,
        "updated_at": time.time(),
    }


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
    preferences: Optional[dict] = None,  # NEW: soft personalisation hints
) -> tuple[list[NodeWithScore], str]:
    """Deterministic routing based on intent — no planner LLM call.

    Routes:
    - text_search / follow_up → ``hybrid_search``
    - outfit_request → search + outfit hint via LLM
    - out_of_scope → empty products + template message
    - unclear → empty products (caller handles clarification)

    Returns:
        (products, reasoning_text)
    """
    # Soft preference injection: append top colour/category as hints
    if preferences:
        pref_hints: list[str] = []
        top_color = (preferences.get("preferred_colors") or [None])[0]
        top_cat   = (preferences.get("preferred_categories") or [None])[0]
        if top_color and top_color.lower() not in search_query.lower():
            pref_hints.append(top_color)
        if top_cat and top_cat.lower() not in search_query.lower():
            pref_hints.append(top_cat)
        if pref_hints:
            search_query = search_query + " " + " ".join(pref_hints)

    if intent in ("text_search", "follow_up"):
        use_expansion = (intent == "follow_up")  # broader results for follow-ups
        products = hybrid_search(
            search_query,
            top_k=6,
            use_query_expansion=use_expansion,
            filters=filters,
        )
        products = _filter_by_gender(products, session_id)
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
        products = _filter_by_gender(products, session_id)
        reasoning = f"Outfit search '{search_query}' → {len(products)} results"
        return products, reasoning

    # out_of_scope / unclear — no products
    return [], f"Intent '{intent}' — no search performed"


def _filter_by_gender(
    products: list[NodeWithScore],
    session_id: Optional[str],
) -> list[NodeWithScore]:
    """Post-search label filter: remove gender-inappropriate products.

    - Skips filtering when ``gender_hint_enabled`` is False or gender is None.
    - Safety net: if filtering leaves 0 results, returns original list.
    - Non-fatal: any exception returns original products unchanged.
    """
    if not session_id:
        return products
    try:
        gender, hint_enabled = get_session_gender(session_id)
        if not hint_enabled or not gender:
            return products
        if gender == "male":
            filtered = [p for p in products if p.label not in _FEMALE_CATEGORIES]
        elif gender == "female":
            filtered = [p for p in products if p.label not in _MALE_CATEGORIES]
        else:
            return products
        return filtered if filtered else products
    except Exception:
        return products


# ---------------------------------------------------------------------------
# Slot gate helper
# ---------------------------------------------------------------------------


def _resolve_search_query(
    intent: str,
    intent_result: ClassifiedIntent,
    session_id: str,
    history: list[Message],
    query: str = "",
) -> tuple[str, str, "ExtractedSlots"]:
    """Resolve the search query for the current turn.

    Applies pre-search readiness checks for search-like intents so the
    system asks clarifying questions before retrieval when confidence or
    slot completeness is insufficient.

    Returns:
        (search_query, clarification_message, accumulated_slots)
        ``clarification_message`` is non-empty when the caller should
        return early with a clarification question.
        ``accumulated_slots`` is the merged slot state for use in the
        follow-up turn.
    """
    if intent in ("text_search", "follow_up", "outfit_request"):
        new_slots = intent_result.extracted_slots
        accumulated = _session_accumulated_slots.get(session_id, ExtractedSlots())
        did_reset = False
        if intent == "text_search" and should_reset_slots(accumulated, new_slots):
            accumulated = ExtractedSlots()
            did_reset = True
        accumulated = merge_slots(accumulated, new_slots)
        _session_accumulated_slots[session_id] = accumulated
        ranked_slots = _merge_ranked_slots(
            session_id,
            intent_result,
            accumulated,
            reset=did_reset,
        )

        # ── Category validation guard (kept pre-search) ───────────────────
        # Unsupported categories must be caught before search; the index
        # has no data for them so search would return irrelevant results.
        slot_category = _normalize_slot_text(ranked_slots.get("category")) or accumulated.category
        if slot_category and slot_category not in SUPPORTED_CATEGORIES:
            lang = detect_language(query)
            suggestions = _find_category_suggestions(slot_category)
            refusal = build_unsupported_category_message(slot_category, suggestions, lang)
            return "", refusal, accumulated

        search_confidence_threshold = _get_search_confidence_threshold()
        if intent_result.confidence < search_confidence_threshold:
            low_conf_missing = _readiness_missing_slots(intent, ranked_slots)
            if not low_conf_missing:
                low_conf_missing = ["one_of_four"]
            question = _build_ranked_clarification_question(
                intent,
                query,
                low_conf_missing,
                low_confidence=True,
            )
            return "", question, accumulated

        is_ready, missing_slots = _is_query_ready(intent, ranked_slots)
        if not is_ready:
            question = _build_ranked_clarification_question(
                intent,
                query,
                missing_slots,
            )
            return "", question, accumulated

        # Build ranked query from high-value slots once readiness checks pass.
        ranked_parts = [
            _normalize_slot_text(ranked_slots.get("color")),
            _normalize_slot_text(ranked_slots.get("style")),
            _normalize_slot_text(ranked_slots.get("occasion")),
            _normalize_slot_text(ranked_slots.get("category")),
        ]
        search_query = " ".join([p for p in ranked_parts if p])
        if not search_query:
            search_query = compose_refined_query_from_slots(accumulated)
        if not search_query:
            search_query = intent_result.refined_query or query
        return search_query, "", accumulated

    # unclear and other non-search intents
    if intent_result.confidence < 0.6 or intent == "unclear":
        clarification = check_clarification(
            intent_result.refined_query or "", history=history,
        )
        if clarification.needs_clarification:
            return "", clarification.question, ExtractedSlots()

    return intent_result.refined_query or "", "", ExtractedSlots()


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
            # Emit thinking_end BEFORE delegating so the frontend always
            # transitions out of the "thinking" state, even if _handle_confirm
            # raises an exception partway through.
            yield ThinkingEvent("done", "Confirming selection...")
            yield from _handle_confirm(session_id, query)
            return
        if normalized in REJECT_KEYWORDS:
            yield ThinkingEvent("done", "Cancelling selection...")
            yield from _handle_reject(session_id, query)
            return
        # Not a keyword match — ask for clarification instead of clearing
        yield ThinkingEvent("done", "Clarifying selection...")
        yield from _handle_ambiguous_response(session_id, query)
        return

    # --- Offer-declined sentinel (0 LLM calls) ---
    if query.strip() == "__offer_declined__":
        yield from _handle_offer_declined(session_id)
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

    # Step 3: Search query resolution (pre-search readiness gate enabled)
    search_query, clarification, accumulated_slots = _resolve_search_query(
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
        preferences=preferences,  # soft personalisation hints
    )
    yield ThinkingEvent(
        "search_done",
        f"Found {len(products)} products — reranking...",
    )

    # ── Post-search zero-results clarification gate ──────────────────────
    # Fires when retrieval has already run but returned no products.
    # Pre-search readiness gating is handled in _resolve_search_query().
    if not products and intent in ("text_search", "follow_up"):
        clarify_count = _count_clarification_turns(history)
        if clarify_count < MAX_CLARIFICATION_TURNS:
            question = build_template_question(
                missing_slots=["category"],
                slots=accumulated_slots,
                query=query,
            )
            add_message(session_id, "assistant", question)
            yield ThinkingEvent(
                "done",
                f"No results — clarification turn "
                f"{clarify_count + 1}/{MAX_CLARIFICATION_TURNS} — "
                f"{time.time() - start_time:.1f}s",
            )
            yield OrchestrateResult(
                intent="clarification",
                session_id=session_id,
                clarification=question,
                reasoning="Zero search results — requesting more detail.",
                history=history,
                filters=intent_result.filters,
            )
            return
        # MAX_CLARIFICATION_TURNS reached — fall through so synthesis LLM
        # can handle zero-results gracefully ("I couldn't find anything...")
    # ── End post-search gate ────────────────────────────────────────

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
        _session_last_results[session_id] = {
            "path_mode": "path1",
            "products": cached_products,
            "updated_at": time.time(),
        }

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
    cached_entry_raw = _session_last_results.get(session_id)
    if isinstance(cached_entry_raw, dict):
        cached_results = cached_entry_raw.get("products", [])
        path_mode = cached_entry_raw.get("path_mode", "path1")
    else:
        cached_results = cached_entry_raw or []
        path_mode = "path1"
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
        items=valid_items,
        search_query=search_query,
        numbers=selected_numbers,
        path_mode=path_mode,
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
        yield _sse("done", {"session_id": session_id, "intent": "product_confirm", "styling": ""})
        return

    try:
        # Batch both the position lookup and the insert into a single
        # _db_conn() borrow to avoid exhausting the pool (maxconn=5) under
        # concurrent load when two sequential getconn() calls are needed.
        items_to_save = []
        for it in pending.items:
            position = get_last_click_position(session_id, it.image_id, pending.path_mode)
            items_to_save.append({
                "image_id": it.image_id,
                "label": it.label,
                "color": it.color,
                "caption": it.caption,
                "image_path": it.image_path,
                "search_query": pending.search_query,
                "position": position,
                "path_mode": pending.path_mode,
            })
        inserted = save_selected_items(session_id, items_to_save)
    except Exception as exc:
        logger.error("_handle_confirm DB error: %s", exc)
        err_text = (
            "⚠️ Không thể lưu sản phẩm do lỗi hệ thống. Vui lòng thử lại."
            if lang == "vi"
            else "⚠️ Could not save products due to a system error. Please try again."
        )
        yield _sse("error", {"message": err_text})
        yield _sse("done", {"session_id": session_id, "intent": "product_confirm", "styling": ""})
        return

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

    cached_entry_raw = _session_last_results.get(session_id)
    if isinstance(cached_entry_raw, dict):
        cached_results = cached_entry_raw.get("products", [])
    else:
        cached_results = cached_entry_raw or []

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
        lines = ["❌ Không sao! Đây là các sản phẩm — hãy cho tôi biết bạn muốn thêm cái nào vào giỏ hàng.\n"]
    elif lang == "es":
        lines = ["❌ ¡Sin problema! Aquí están los artículos — dime cuál quieres añadir al carrito.\n"]
    else:
        lines = ["❌ No problem! Here are the items again — tell me which one you'd like to add to your cart.\n"]

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


def _handle_offer_declined(session_id: str) -> Generator:
    """Handle the __offer_declined__ sentinel from the frontend offer dialog."""
    try:
        gender, _ = get_session_gender(session_id)
    except Exception:
        gender = None

    # Detect language from session history
    try:
        history = get_history(session_id, limit=4)
        last_user_msgs = [m.content for m in history if m.role == "user"]
        lang = detect_language(last_user_msgs[-1]) if last_user_msgs else "en"
    except Exception:
        lang = "en"

    decline_texts = {
        "vi": "Không sao! Hãy tiếp tục tìm thêm, hoặc gõ 'đặt hàng' khi bạn sẵn sàng. 😊",
        "es": "¡Sin problema! Sigue buscando o escribe 'pedir' cuando estés listo. 😊",
        "en": "No problem! Keep browsing, or say 'order' whenever you're ready to checkout. 😊",
    }
    text = decline_texts.get(lang, decline_texts["en"])
    add_message(session_id, "assistant", text)
    yield _sse("clarification", {"text": text, "intent": "offer_declined"})
    yield _sse("done", {"session_id": session_id, "intent": "offer_declined", "styling": ""})


# ---------------------------------------------------------------------------
# Orchestration mode helpers
# ---------------------------------------------------------------------------


def _get_orchestration_mode(model_id: str) -> tuple[str, str, str]:
    """Map a session model ID to (mode, orchestrator_model, synthesizer_model).

    Gemini-only: direct routing + Gemini synthesis.

    Returns:
        Tuple of (mode, orchestrator_model, synthesizer_model).
    """
    return "direct", "gemini-2.5-flash", model_id


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

    # Emit product cards (direct mode only)
    product_dicts = [
        {
            "image_id": p.image_id,
            "image_path": os.path.basename(p.image_path),  # strip full path → filename only
            "label": p.label,
            "color": p.color,
            "caption": p.caption,
            "score": round(p.score, 4),
            "path_mode": "path1",
            "search_query": result.search_query,
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
        # Direct mode: regular stream synthesis
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

    # Emit offer_prompt only after a successful product search
    if result.intent in ("text_search", "follow_up") and len(result.products) > 0:
        lang = detect_language(query)
        offer_texts = {
            "vi": "Bạn muốn đặt hàng những sản phẩm này không, hay muốn tiếp tục tìm thêm? 🛒",
            "es": "¿Te gustaría realizar un pedido con estos artículos o seguir buscando? 🛒",
            "en": "Would you like to place an order for these items, or continue looking? 🛒",
        }
        offer_text = offer_texts.get(lang, offer_texts["en"])
        yield _sse("offer_prompt", {"text": offer_text, "lang": lang})


def _sse(event: str, data: dict) -> str:
    """Format a single Server-Sent Event line."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
