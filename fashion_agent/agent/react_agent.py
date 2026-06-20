"""Pipeline ReAct làm baseline để so sánh trong luận văn.

Kiến trúc (ReAct baseline — Reason + Act loop):
  1. classify_intent     → 1 lần gọi Gemini (intent + confidence)
  2. _react_gate()       → bỏ qua loop nếu out_of_scope / unclear / confidence thấp
  3. orchestrate_with_gemini() → vòng lặp function calling của Gemini (1–4 vòng)
  4. _log_react_traces() → lưu telemetry theo từng tool call vào bảng react_traces
  5. Synthesis           → Gemini tổng hợp (cùng prompt với direct pipeline)

Khác biệt so với direct pipeline (fashion_agent.py):
  - Không tích lũy slot giữa các lượt chat
  - Không có clarification gate trước khi search
  - Gemini tự quyết định gọi tool nào và bao nhiêu lần
  - Chi phí thường là 2 + N lần gọi LLM

Ràng buộc thiết kế:
  - Module này độc lập hoàn toàn với fashion_agent.py.
  - Không chia sẻ state in-memory với direct pipeline.
  - api/main.py sẽ chọn một trong hai module tùy orchestration mode.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Generator, Optional

from agent.intent_classifier import classify_intent, ClassifiedIntent
from agent.agentic_orchestrator import (
    orchestrate_with_gemini,
    AgenticOrchestrationResult,
)
from agent.memory import (
    create_session,
    session_exists,
    add_message,
    get_history,
    get_session_model,
    get_session_gender,
    log_token_usage,
    Message,
)
from agent.prompts import (
    SYNTHESIS_PROMPT,
    STREAM_SYNTHESIS_PROMPT,
    detect_language,
    _LANG_NAMES,
)
from agent.utils import parse_llm_json, fallback_text_response, format_history_text
from shared.llm import get_client, TokenUsage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

REACT_CONFIDENCE_THRESHOLD = float(os.getenv("REACT_CONFIDENCE_THRESHOLD", "0.50"))

_OUT_OF_SCOPE_RESPONSES = {
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


# ---------------------------------------------------------------------------
# Data types (mirrors fashion_agent.py — kept compatible for api/main.py dispatch)
# ---------------------------------------------------------------------------


@dataclass
class ProductResult:
    """Kết quả sản phẩm chuẩn hóa cho pipeline ReAct."""

    image_id: str
    image_path: str
    label: str
    color: str
    caption: str
    score: float = 0.0


@dataclass
class AgentResponse:
    """Phản hồi cuối cùng của agent trong pipeline ReAct."""

    answer: str
    products: list[ProductResult] = field(default_factory=list)
    styling_suggestion: str = ""
    reasoning: str = ""
    session_id: str = ""
    intent: str = ""

    def to_dict(self) -> dict:
        """Chuyển AgentResponse sang dict để serialize."""
        return asdict(self)


# ---------------------------------------------------------------------------
# ReAct gate
# ---------------------------------------------------------------------------


def _react_gate(classified: ClassifiedIntent) -> bool:
    """Quyết định query có nên bỏ qua vòng tool-calling của Gemini hay không."""
    if classified.intent in ("out_of_scope", "unclear"):
        return False
    if classified.confidence < REACT_CONFIDENCE_THRESHOLD:
        return False
    return True


# ---------------------------------------------------------------------------
# ReAct trace logger
# ---------------------------------------------------------------------------


def _log_react_traces(
    session_id: str,
    query_text: str,
    result: AgenticOrchestrationResult,
) -> None:
    """Lưu một dòng react_traces cho mỗi tool call nhằm phục vụ telemetry."""
    if not result.tool_calls:
        return
    try:
        import json as _json
        from agent.memory import _db_conn  # reuse shared connection pool

        with _db_conn() as conn:
            with conn.cursor() as cur:
                for i, tc in enumerate(result.tool_calls):
                    cur.execute(
                        """
                        INSERT INTO react_traces
                            (session_id, query_text, iteration, tool_name,
                             tool_args, result_count, duration_ms)
                        VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s);
                        """,
                        (
                            session_id,
                            query_text,
                            i,
                            tc.tool,
                            _json.dumps(tc.args),
                            tc.result_count,
                            round(tc.duration_ms, 2),
                        ),
                    )
            conn.commit()
    except Exception as exc:
        logger.debug("react_traces logging failed: %s", exc)


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------


def _sse(event: str, data: dict) -> str:
    """Định dạng một chuỗi Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# Synthesis context builder (adapted for product dicts from agentic_orchestrator)
# ---------------------------------------------------------------------------


def _build_synthesis_context(
    query: str,
    products: list[dict],
    history: list[Message],
    session_id: Optional[str] = None,
) -> dict[str, str]:
    """Tạo context cho prompt synthesis, tương thích với dict sản phẩm."""
    lines = []
    for i, p in enumerate(products, 1):
        lines.append(
            f"{i}. {p.get('label', '')} | Color: {p.get('color', '')} | Caption: {p.get('caption', '')}"
        )
    products_text = "\n".join(lines) if lines else "No products found."
    history_text = format_history_text(history, limit=6)

    lang = detect_language(query)
    lang_name = _LANG_NAMES.get(lang, "English")

    cta_map = {
        "vi": "👉 Hãy cho tôi biết bạn thích cái nào — tôi sẽ thêm vào giỏ hàng ngay!",
        "es": "👉 Dime cuál te gusta, ¡lo añadiré al carrito!",
        "en": "👉 Tell me which one you like — I'll add it to your cart!",
    }
    cta_example = cta_map.get(lang, cta_map["en"])

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
            pass

    return {
        "products_text": products_text,
        "history_text": history_text,
        "preferences_text": "No preferences yet.",
        "language": lang_name,
        "gender_context": gender_context,
        "num_results": len(products),
        "cta_example": cta_example,
    }


def _extract_styling_from_text(full_text: str) -> str:
    """Tách phần styling suggestion được nối sau marker `💡 Styling tip:`."""
    for marker in ("💡 Styling tip:",):
        if marker in full_text:
            return full_text.split(marker, 1)[1].strip()
    return ""


# ---------------------------------------------------------------------------
# chat() — non-streaming entry point
# ---------------------------------------------------------------------------


def chat(
    query: str,
    session_id: Optional[str] = None,
) -> AgentResponse:
    """Entrypoint không streaming của baseline ReAct."""
    t0 = time.perf_counter()

    # ── Session setup ────────────────────────────────────────────────────────
    if not (session_id and session_exists(session_id)):
        session_id = create_session(orchestration_mode="react")

    model_name = get_session_model(session_id)
    client = get_client(model_name)

    add_message(session_id, "user", query)
    history = get_history(session_id, limit=20)
    history_text = format_history_text(history, limit=6)

    # ── Step 1: Classify intent ──────────────────────────────────────────────
    classified = classify_intent(query, history=history)
    intent = classified.intent

    try:
        log_token_usage(
            session_id=session_id,
            call_name="intent",
            model_name=model_name,
            input_tokens=classified.input_tokens,
            output_tokens=classified.output_tokens,
            orchestration_mode="react",
        )
    except Exception as _e:
        logger.debug("Intent token log failed: %s", _e)

    # ── Step 2: ReAct gate ───────────────────────────────────────────────────
    gate_pass = _react_gate(classified)

    products_list: list[dict] = []
    tool_calls_list: list[dict] = []
    orchestrator_in = 0
    orchestrator_out = 0
    orch_result: Optional[AgenticOrchestrationResult] = None

    if gate_pass:
        # ── Step 3: Gemini orchestration loop ────────────────────────────────
        gender_val: Optional[str] = None
        gender_hint = False
        try:
            gender_val, gender_hint = get_session_gender(session_id)
        except Exception:
            pass

        orch_result = orchestrate_with_gemini(
            query=classified.refined_query or query,
            history_text=history_text,
            gender=gender_val,
            gender_hint=gender_hint,
        )

        products_list = orch_result.products
        tool_calls_list = [tc.to_dict() for tc in orch_result.tool_calls]
        orchestrator_in = orch_result.orchestrator_input_tokens
        orchestrator_out = orch_result.orchestrator_output_tokens

        # ── Step 4: Log react traces ──────────────────────────────────────────
        _log_react_traces(session_id, query, orch_result)

    # ── Step 5: Synthesize ───────────────────────────────────────────────────
    answer = ""
    styling = ""

    if not gate_pass:
        lang = detect_language(query)
        answer = _OUT_OF_SCOPE_RESPONSES.get(lang, _OUT_OF_SCOPE_RESPONSES["en"])
    elif orch_result is not None and orch_result.clarification_question:
        answer = orch_result.clarification_question
        products_list = []
    else:
        ctx = _build_synthesis_context(query, products_list, history, session_id)
        prompt = SYNTHESIS_PROMPT.format(query=query, **ctx)
        try:
            raw = client.generate(prompt)
            data = parse_llm_json(raw)
            answer = data.get("answer", "")
            styling = data.get("styling_suggestion", "")
        except Exception:
            answer = fallback_text_response(products_list)

    add_message(session_id, "assistant", answer)

    latency_ms = (time.perf_counter() - t0) * 1000
    llm_call_count = 2 + (len(orch_result.tool_calls) if orch_result else 0)

    try:
        log_token_usage(
            session_id=session_id,
            call_name="synthesis",
            model_name=model_name,
            input_tokens=0,
            output_tokens=0,
            orchestration_mode="react",
            orchestrator_model="gemini-2.5-flash",
            synthesizer_model=model_name,
            tool_calls_json=tool_calls_list,
            orchestrator_input_tokens=orchestrator_in,
            orchestrator_output_tokens=orchestrator_out,
        )
    except Exception as _e:
        logger.debug("Synthesis token log failed: %s", _e)

    product_results = [
        ProductResult(
            image_id=p.get("image_id", ""),
            image_path=p.get("image_path", ""),
            label=p.get("label", ""),
            color=p.get("color", ""),
            caption=p.get("caption", ""),
            score=float(p.get("score", 0.0) or 0.0),
        )
        for p in products_list
    ]

    n_tools = len(orch_result.tool_calls) if orch_result else 0
    return AgentResponse(
        answer=answer,
        products=product_results,
        styling_suggestion=styling,
        reasoning=(
            f"ReAct: gate={'pass' if gate_pass else 'block'}, "
            f"tools={n_tools}, latency={latency_ms:.0f}ms"
        ),
        session_id=session_id,
        intent=intent,
    )


# ---------------------------------------------------------------------------
# chat_stream() — streaming entry point
# ---------------------------------------------------------------------------


def chat_stream(
    query: str,
    session_id: Optional[str] = None,
) -> Generator:
    """Phiên bản streaming của `chat()` và yield các SSE event."""
    orchestrate_start = time.time()

    # ── Session setup ────────────────────────────────────────────────────────
    if not (session_id and session_exists(session_id)):
        session_id = create_session(orchestration_mode="react")

    model_name = get_session_model(session_id)
    client = get_client(model_name)

    add_message(session_id, "user", query)
    history = get_history(session_id, limit=20)
    history_text = format_history_text(history, limit=6)

    yield _sse("thinking_start", {"text": "🔄 ReAct: Analyzing your question..."})

    # ── Step 1: Classify intent ──────────────────────────────────────────────
    yield _sse("thinking_step", {"step": "classify", "detail": "Classifying intent..."})
    classified = classify_intent(query, history=history)
    intent = classified.intent

    intent_tokens = TokenUsage(
        input_tokens=classified.input_tokens,
        output_tokens=classified.output_tokens,
        call_name="intent",
    )
    yield _sse("thinking_step", {
        "step": "classify_done",
        "detail": f"Intent: {intent} (confidence: {classified.confidence:.2f}) | "
                  f"📊 {intent_tokens.input_tokens} in / {intent_tokens.output_tokens} out",
    })

    try:
        log_token_usage(
            session_id=session_id,
            call_name="intent",
            model_name=model_name,
            input_tokens=intent_tokens.input_tokens,
            output_tokens=intent_tokens.output_tokens,
            orchestration_mode="react",
        )
    except Exception as _e:
        logger.debug("Intent token log failed: %s", _e)

    # ── Step 2: ReAct gate ───────────────────────────────────────────────────
    gate_pass = _react_gate(classified)

    products_list: list[dict] = []
    tool_calls_list: list[dict] = []
    orchestrator_in = 0
    orchestrator_out = 0
    orch_result: Optional[AgenticOrchestrationResult] = None

    if not gate_pass:
        yield _sse("thinking_step", {
            "step": "gate_block",
            "detail": f"⛔ Gate blocked: intent='{intent}', conf={classified.confidence:.2f} < threshold={REACT_CONFIDENCE_THRESHOLD}",
        })
    else:
        # ── Step 3: Gemini orchestration loop ────────────────────────────────
        yield _sse("thinking_step", {
            "step": "react_start",
            "detail": "🔄 Starting Gemini ReAct tool-calling loop...",
        })

        gender_val: Optional[str] = None
        gender_hint = False
        try:
            gender_val, gender_hint = get_session_gender(session_id)
        except Exception:
            pass

        orch_result = orchestrate_with_gemini(
            query=classified.refined_query or query,
            history_text=history_text,
            gender=gender_val,
            gender_hint=gender_hint,
        )

        products_list = orch_result.products
        tool_calls_list = [tc.to_dict() for tc in orch_result.tool_calls]
        orchestrator_in = orch_result.orchestrator_input_tokens
        orchestrator_out = orch_result.orchestrator_output_tokens

        # Emit one thinking step per tool call
        for i, tc in enumerate(orch_result.tool_calls):
            yield _sse("thinking_step", {
                "step": f"tool_{i + 1}",
                "detail": (
                    f"🔧 Tool [{i + 1}]: {tc.tool}("
                    f"{', '.join(f'{k}={v!r}' for k, v in list(tc.args.items())[:3])})"
                    f" → {tc.result_count} results ({tc.duration_ms:.0f}ms)"
                ),
            })

        yield _sse("thinking_step", {
            "step": "react_done",
            "detail": (
                f"✅ ReAct loop finished: {len(orch_result.tool_calls)} tool call(s), "
                f"{len(products_list)} products total | "
                f"📊 Orch: {orchestrator_in} in / {orchestrator_out} out"
            ),
        })

        # ── Step 4: Log react traces ──────────────────────────────────────────
        _log_react_traces(session_id, query, orch_result)

    # Thinking end
    duration_ms = int((time.time() - orchestrate_start) * 1000)
    yield _sse("thinking_end", {
        "duration_ms": duration_ms,
        "input_tokens": intent_tokens.input_tokens,
        "output_tokens": intent_tokens.output_tokens,
    })

    # ── Early exit for gate-blocked intents ──────────────────────────────────
    if not gate_pass:
        lang = detect_language(query)
        answer = _OUT_OF_SCOPE_RESPONSES.get(lang, _OUT_OF_SCOPE_RESPONSES["en"])
        add_message(session_id, "assistant", answer)
        yield _sse("clarification", {"text": answer, "intent": intent})
        yield _sse("done", {
            "session_id": session_id,
            "intent": intent,
            "styling": "",
            "orchestration_mode": "react",
            "total_input_tokens": intent_tokens.input_tokens,
            "total_output_tokens": intent_tokens.output_tokens,
        })
        return

    # ── Early exit when the orchestrator chose ask_user ──────────────────────
    if orch_result is not None and orch_result.clarification_question:
        answer = orch_result.clarification_question
        add_message(session_id, "assistant", answer)
        yield _sse("clarification", {"text": answer, "intent": intent})
        yield _sse("done", {
            "session_id": session_id,
            "intent": intent,
            "styling": "",
            "orchestration_mode": "react",
            "total_input_tokens": intent_tokens.input_tokens + orchestrator_in,
            "total_output_tokens": intent_tokens.output_tokens + orchestrator_out,
        })
        return

    # ── Emit products ────────────────────────────────────────────────────────
    product_dicts_for_ui = [
        {
            "image_id": p.get("image_id", ""),
            "image_path": os.path.basename(p.get("image_path", "") or ""),
            "label": p.get("label", ""),
            "color": p.get("color", ""),
            "caption": p.get("caption", ""),
            "score": round(float(p.get("score", 0.0) or 0.0), 4),
            "path_mode": "path1",
            "search_query": query,
        }
        for p in products_list
    ]
    yield _sse("products", {"products": product_dicts_for_ui})

    # ── Step 5: Stream synthesis ─────────────────────────────────────────────
    ctx = _build_synthesis_context(query, products_list, history, session_id)
    prompt = STREAM_SYNTHESIS_PROMPT.format(query=query, **ctx)

    full_text_parts: list[str] = []
    synthesis_tokens = TokenUsage()

    try:
        gen = client.stream(prompt)
        while True:
            try:
                text = next(gen)
                full_text_parts.append(text)
                yield _sse("token", {"text": text})
            except StopIteration as e:
                usage = e.value
                if isinstance(usage, TokenUsage):
                    synthesis_tokens = usage
                break
    except Exception as exc:
        logger.error("ReAct synthesis stream error: %s", exc)
        fallback = fallback_text_response(products_list)
        full_text_parts.append(fallback)
        yield _sse("token", {"text": fallback})

    full_text = "".join(full_text_parts)
    styling = _extract_styling_from_text(full_text)

    add_message(session_id, "assistant", full_text)

    # ── Persist synthesis token usage ────────────────────────────────────────
    try:
        log_token_usage(
            session_id=session_id,
            call_name="synthesis",
            model_name=model_name,
            input_tokens=synthesis_tokens.input_tokens,
            output_tokens=synthesis_tokens.output_tokens,
            orchestration_mode="react",
            orchestrator_model="gemini-2.5-flash",
            synthesizer_model=model_name,
            tool_calls_json=tool_calls_list,
            orchestrator_input_tokens=orchestrator_in,
            orchestrator_output_tokens=orchestrator_out,
        )
    except Exception as _e:
        logger.debug("Synthesis token log failed: %s", _e)

    total_in = (
        intent_tokens.input_tokens
        + synthesis_tokens.input_tokens
        + orchestrator_in
    )
    total_out = (
        intent_tokens.output_tokens
        + synthesis_tokens.output_tokens
        + orchestrator_out
    )

    yield _sse("done", {
        "session_id": session_id,
        "intent": intent,
        "styling": styling,
        "orchestration_mode": "react",
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
    })
