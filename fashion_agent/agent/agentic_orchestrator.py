"""Tầng điều phối agentic cho Mode B (Gemini→GPT) và Mode C (GPT→Claude).

Thiết kế:
    Mỗi orchestrator nhận vào một bộ tool schema (search, recommend, filter)
    và chạy vòng lặp gọi tool nhiều lượt cho đến khi sẵn sàng tổng hợp.
    Kết quả search thô được giữ lại để synthesize, còn metadata tool-call
    được trả về cho mục đích logging và phân tích.

Các mode được hỗ trợ:
    - Mode B: Gemini điều phối (google.generativeai function calling), GPT-4o tổng hợp.
    - Mode C: GPT-4o điều phối (openai function calling), Claude tổng hợp.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool-call tracking dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ToolCall:
    """Ghi lại một lần orchestrator gọi tool."""
    tool: str
    args: dict
    result_count: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        """Chuyển tool call sang dict để dễ serialize và log."""
        return {
            "tool": self.tool,
            "args": self.args,
            "result_count": self.result_count,
            "duration_ms": round(self.duration_ms, 1),
        }


@dataclass
class AgenticOrchestrationResult:
    """Kết quả của một vòng điều phối agentic."""
    # Aggregated products across all tool calls (flat list of product dicts)
    products: list[dict] = field(default_factory=list)
    # FORMATTED string of all product results for use in the synthesis prompt
    tool_results_text: str = ""
    # Ordered list of tool calls made
    tool_calls: list[ToolCall] = field(default_factory=list)
    # Token usage of the orchestrator (separate from synthesizer)
    orchestrator_input_tokens: int = 0
    orchestrator_output_tokens: int = 0
    # If the orchestrator chose to ask the user a follow-up instead of searching,
    # this holds the question text. When set, callers should emit a clarification
    # event and skip synthesis.
    clarification_question: Optional[str] = None
    # Error, if any
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Tool schemas (OpenAI / Gemini format helpers)
# ---------------------------------------------------------------------------

# Canonical action schemas
_TOOL_DEFINITIONS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "search_fashion",
            "description": "Search for fashion products by text query. Use this for generic product searches.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query."},
                    "top_k": {"type": "integer", "description": "Max results to return (default 5).", "default": 5},
                    "gender": {"type": "string", "enum": ["male", "female", "unisex", ""], "description": "Gender filter."},
                    "category": {"type": "string", "description": "Product category filter (e.g. shirts, dresses)."},
                    "color": {"type": "string", "description": "Color filter."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_outfit",
            "description": "Generate outfit recommendations based on style, occasion or preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "style": {"type": "string", "description": "Target style (e.g. casual, formal, bohemian)."},
                    "occasion": {"type": "string", "description": "Occasion (e.g. wedding, office, date night)."},
                    "gender": {"type": "string", "enum": ["male", "female", "unisex", ""], "description": "Gender filter."},
                    "top_k": {"type": "integer", "description": "Max results per category (default 3).", "default": 3},
                },
                "required": [],
            },
        },
    },
]

_TOOL_DEFINITIONS_GEMINI = [
    {
        "name": "search_fashion",
        "description": "Search for fashion products by text query.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING"},
                "top_k": {"type": "INTEGER"},
                "gender": {"type": "STRING"},
                "category": {"type": "STRING"},
                "color": {"type": "STRING"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "recommend_outfit",
        "description": "Generate outfit recommendations based on style or occasion.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "style": {"type": "STRING"},
                "occasion": {"type": "STRING"},
                "gender": {"type": "STRING"},
                "top_k": {"type": "INTEGER"},
            },
            "required": [],
        },
    },
    {
        "name": "ask_user",
        "description": (
            "Ask the user ONE concise follow-up question when the request is too vague "
            "to search productively (e.g. 'I want a shirt' with no color, occasion, fit, "
            "or material, and history does not supply it). Phrase the question in the "
            "same language the user wrote in. Use this instead of search_fashion when "
            "key information is missing."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "question": {
                    "type": "STRING",
                    "description": "The follow-up question to ask the user, in their language.",
                },
            },
            "required": ["question"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executor  (calls the real search/recommendation pipeline)
# ---------------------------------------------------------------------------

def _execute_tool(tool_name: str, args: dict) -> tuple[list[dict], str]:
    """Thực thi một tool call và trả về danh sách sản phẩm cùng text đã format.

    Hàm này ủy quyền xuống pipeline search/recommend hiện có. Nếu lỗi xảy ra,
    hàm trả về danh sách rỗng kèm text lỗi thay vì làm hỏng toàn bộ orchestration.
    """
    from agent.tools import run_search_tool, run_recommend_tool  # lazy import

    start = time.perf_counter()
    try:
        if tool_name == "search_fashion":
            products = run_search_tool(
                query=args.get("query", ""),
                top_k=int(args.get("top_k", 5)),
                gender=args.get("gender", ""),
                category=args.get("category", ""),
                color=args.get("color", ""),
            )
        elif tool_name == "recommend_outfit":
            products = run_recommend_tool(
                style=args.get("style", ""),
                occasion=args.get("occasion", ""),
                gender=args.get("gender", ""),
                top_k=int(args.get("top_k", 3)),
            )
        else:
            return [], f"[Unknown tool: {tool_name}]"

        elapsed_ms = (time.perf_counter() - start) * 1000
        # Format products
        lines = [f"{i+1}. {p.get('label', '')} | Color: {p.get('color', '')} | Caption: {p.get('caption', '')}"
                 for i, p in enumerate(products)]
        formatted = "\n".join(lines) if lines else "(no results)"
        return products, formatted, elapsed_ms  # type: ignore[return-value]

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.warning("Tool execution failed [%s]: %s", tool_name, exc)
        return [], f"[Tool error: {exc}]", elapsed_ms  # type: ignore[return-value]


# Returns (products, text, elapsed_ms) — 3-tuple
def _exec(tool_name: str, args: dict) -> tuple[list[dict], str, float]:
    """Wrapper mỏng để giữ kiểu trả về 3 phần cho các orchestrator."""
    return _execute_tool(tool_name, args)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Mode B: Gemini orchestrator
# ---------------------------------------------------------------------------

def orchestrate_with_gemini(
    query: str,
    history_text: str,
    gender: Optional[str] = None,
    gender_hint: bool = False,
    max_iterations: int = 4,
) -> AgenticOrchestrationResult:
    """Chạy Gemini như một orchestrator agentic bằng native function calling.

    Trả về `AgenticOrchestrationResult` chứa sản phẩm đã gộp và danh sách
    `tool_calls` đã thực thi.
    """
    import google.generativeai as genai  # type: ignore[import]

    result = AgenticOrchestrationResult()

    # Build system instruction
    gender_note = ""
    if gender_hint and gender:
        gender_note = f"\nIMPORTANT: The user's gender is '{gender}'. Use appropriate gender filters in your searches."

    system_instruction = (
        "You are a fashion search orchestrator with three tools: search_fashion, "
        "recommend_outfit, and ask_user.\n\n"
        "Decision rule: if the user's most recent request is too vague to produce "
        "useful results (e.g. 'a shirt', 'something nice', no occasion / color / fit / "
        "material) AND the conversation history does not supply the missing detail, "
        "call ask_user with ONE concise follow-up question targeting the most useful "
        "missing facet. Phrase the question in the same language the user wrote in. "
        "Never call ask_user more than once. Never call ask_user alongside a search; "
        "choose one or the other.\n\n"
        "Otherwise, call search_fashion or recommend_outfit (1-3 times max). When you "
        "have enough results, stop calling tools.{gender_note}"
    ).format(gender_note=gender_note)

    prompt = f"User request: {query}\n\nConversation history:\n{history_text}\n\nPlease search/recommend products for this user."

    try:
        # Define tools using the dict-based approach (works across SDK versions)
        tool_config = {
            "function_declarations": _TOOL_DEFINITIONS_GEMINI
        }

        model = genai.GenerativeModel(  # type: ignore[attr-defined]
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction,
            tools=[tool_config],
        )
        chat = model.start_chat()

        response = chat.send_message(prompt)
        result.orchestrator_input_tokens += getattr(
            getattr(response, "usage_metadata", None), "prompt_token_count", 0
        )
        result.orchestrator_output_tokens += getattr(
            getattr(response, "usage_metadata", None), "candidates_token_count", 0
        )

        all_tool_results: list[str] = []
        iterations = 0

        while iterations < max_iterations:
            # Check if the response contains tool calls
            fn_calls = []
            for part in response.parts:
                if hasattr(part, "function_call") and part.function_call and part.function_call.name:
                    fn_calls.append(part.function_call)

            if not fn_calls:
                break  # Gemini decided it's done

            # If the LLM wants to clarify, take that and stop — do not also run search.
            ask_user_call = next(
                (fc for fc in fn_calls if fc.name == "ask_user"), None
            )
            if ask_user_call is not None:
                question = str(dict(ask_user_call.args).get("question", "")).strip()
                if question:
                    result.tool_calls.append(ToolCall(
                        tool="ask_user",
                        args={"question": question},
                        result_count=0,
                        duration_ms=0.0,
                    ))
                    result.clarification_question = question
                    break

            # Execute each tool call
            tool_responses = []
            for fn_call in fn_calls:
                tool_name = fn_call.name
                args = dict(fn_call.args)
                products, formatted, elapsed_ms = _exec(tool_name, args)

                tc = ToolCall(
                    tool=tool_name,
                    args=args,
                    result_count=len(products),
                    duration_ms=elapsed_ms,
                )
                result.tool_calls.append(tc)
                result.products.extend(products)

                section_header = f"[{tool_name} results]"
                all_tool_results.append(f"{section_header}\n{formatted}")

                # Build function response for Gemini
                tool_responses.append({
                    "function_response": {
                        "name": tool_name,
                        "response": {"result": formatted},
                    }
                })

            # Send tool responses back
            response = chat.send_message(tool_responses)
            result.orchestrator_input_tokens += getattr(
                getattr(response, "usage_metadata", None), "prompt_token_count", 0
            )
            result.orchestrator_output_tokens += getattr(
                getattr(response, "usage_metadata", None), "candidates_token_count", 0
            )
            iterations += 1

        result.tool_results_text = "\n\n".join(all_tool_results) or "(no search results)"

    except Exception as exc:
        logger.error("Gemini orchestration failed: %s", exc)
        result.error = str(exc)
        result.tool_results_text = "(orchestration failed — no results)"

    return result


# ---------------------------------------------------------------------------
# Mode C: GPT-4o orchestrator
# ---------------------------------------------------------------------------

def orchestrate_with_gpt(
    query: str,
    history_text: str,
    gender: Optional[str] = None,
    gender_hint: bool = False,
    max_iterations: int = 4,
) -> AgenticOrchestrationResult:
    """Chạy GPT-4o như một orchestrator agentic bằng native function calling.

    Trả về `AgenticOrchestrationResult` chứa sản phẩm đã gộp và danh sách
    `tool_calls` đã thực thi.
    """
    import openai

    result = AgenticOrchestrationResult()

    gender_note = ""
    if gender_hint and gender:
        gender_note = f"\nIMPORTANT: The user's gender is '{gender}'. Apply appropriate gender filters."

    system_msg = (
        "You are a fashion search orchestrator. Call the available tools to find "
        "the best products for the user. Call search_fashion or recommend_outfit "
        "1-3 times as needed. When done, provide a brief summary.{gender_note}"
    ).format(gender_note=gender_note)

    import os
    client = openai.Client(api_key=os.getenv("OPENAI_API_KEY", ""))
    messages: list[dict] = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"User request: {query}\n\nHistory:\n{history_text}"},
    ]

    all_tool_results: list[str] = []
    iterations = 0

    try:
        while iterations < max_iterations:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=_TOOL_DEFINITIONS_OPENAI,
                tool_choice="auto",
            )

            usage = response.usage
            if usage:
                result.orchestrator_input_tokens += getattr(usage, "prompt_tokens", 0)
                result.orchestrator_output_tokens += getattr(usage, "completion_tokens", 0)

            choice = response.choices[0]
            msg = choice.message

            # Add assistant turn
            messages.append(msg.model_dump())  # type: ignore[arg-type]

            if choice.finish_reason == "stop" or not msg.tool_calls:
                break  # GPT is done

            # Execute tool calls
            for tc_call in (msg.tool_calls or []):
                tool_name = tc_call.function.name
                try:
                    args = json.loads(tc_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                products, formatted, elapsed_ms = _exec(tool_name, args)

                tc = ToolCall(
                    tool=tool_name,
                    args=args,
                    result_count=len(products),
                    duration_ms=elapsed_ms,
                )
                result.tool_calls.append(tc)
                result.products.extend(products)

                section_header = f"[{tool_name} results]"
                all_tool_results.append(f"{section_header}\n{formatted}")

                # Append tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_call.id,
                    "content": formatted,
                })

            iterations += 1

        result.tool_results_text = "\n\n".join(all_tool_results) or "(no search results)"

    except Exception as exc:
        logger.error("GPT orchestration failed: %s", exc)
        result.error = str(exc)
        result.tool_results_text = "(orchestration failed — no results)"

    return result
