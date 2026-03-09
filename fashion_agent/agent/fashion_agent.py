"""
Fashion Agent — main orchestrator.

Ties together intent classification, slot-based clarification, memory, search, and
Gemini synthesis into a single `chat()` function.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

from agent.intent_classifier import classify_intent, ClassifiedIntent, ExtractedSlots
from agent.slot_completeness import (
    check_slot_completeness,
    generate_targeted_question,
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

User preferences: {preferences_text}

Conversation history:
{history_text}

Instructions:
1. Respond naturally in the same language as the user's query (Vietnamese or English).
2. Briefly describe the top recommendations and why they match.
3. If this is a "recommend" intent, include styling suggestions.
4. Keep the response concise (2-4 sentences for search, 3-5 for recommendations).
5. Reference specific products by their attributes (category, color, style).
6. If user preferences are available, personalize recommendations based on their preferred colors and categories.

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
    preferences: Optional[dict] = None,
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

    # Format preferences
    prefs = preferences or {}
    prefs_parts = []
    if prefs.get("preferred_colors"):
        prefs_parts.append(f"Preferred colors: {', '.join(prefs['preferred_colors'])}")
    if prefs.get("preferred_categories"):
        prefs_parts.append(f"Preferred categories: {', '.join(prefs['preferred_categories'])}")
    preferences_text = "; ".join(prefs_parts) if prefs_parts else "No preferences yet."

    prompt = SYNTHESIS_PROMPT.format(
        query=query,
        products_text=products_text,
        preferences_text=preferences_text,
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
# ReAct Tool Registry & Orchestrator
# ---------------------------------------------------------------------------

TOOLS = {
    "search": {
        "description": "Search for fashion products using hybrid search (vector + BM25 + rerank).",
        "params": ["query", "top_k"],
    },
    "memory_enrich": {
        "description": "Enrich the query with user preferences from memory.",
        "params": ["query", "preferences"],
    },
    "outfit_hints": {
        "description": "Generate outfit/styling suggestions for an occasion.",
        "params": ["occasion", "style"],
    },
}

PLAN_PROMPT = """You are a fashion agent planner. Given the user query and context, decide which tools to call.

Available tools:
- search(query, top_k): Search for fashion products
- memory_enrich(query, preferences): Enrich query with user preferences
- outfit_hints(occasion, style): Get outfit styling suggestions

Context:
- User query: {query}
- Intent: {intent}
- User preferences: {preferences_text}
- Previous observations: {observations_text}
- Iteration: {iteration}/{max_iter}

Respond with a JSON array of tool calls (1-2 tools max):
[{{"tool": "search", "args": {{"query": "...", "top_k": 6}}}}]

If observations are sufficient, respond with: []
"""


def _plan(
    query: str,
    intent: str,
    preferences: dict,
    observations: list[str],
    iteration: int,
    max_iter: int,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
) -> list[dict]:
    """Use Gemini to plan which tools to call next."""
    try:
        import google.generativeai as genai
    except ImportError:
        return [{"tool": "search", "args": {"query": query, "top_k": 6}}]

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return [{"tool": "search", "args": {"query": query, "top_k": 6}}]

    genai.configure(api_key=key)
    model = genai.GenerativeModel(model_name)

    prefs_text = json.dumps(preferences) if preferences else "No preferences yet."
    obs_text = "\n".join(observations[-3:]) if observations else "No observations yet."

    prompt = PLAN_PROMPT.format(
        query=query,
        intent=intent,
        preferences_text=prefs_text,
        observations_text=obs_text,
        iteration=iteration,
        max_iter=max_iter,
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        plan = json.loads(text)
        if isinstance(plan, list):
            return plan
    except Exception:
        pass

    return [{"tool": "search", "args": {"query": query, "top_k": 6}}]


def _execute_tool(
    tool_name: str,
    args: dict,
    preferences: dict,
    api_key: Optional[str] = None,
    filters: Optional[dict] = None,
) -> tuple[str, list[NodeWithScore]]:
    """Execute a single tool call and return (observation, products)."""
    if tool_name == "search":
        search_q = args.get("query", "")
        top_k = args.get("top_k", 6)
        products = hybrid_search(search_q, top_k=top_k, filters=filters)
        if products:
            summaries = [f"{p.label}({p.color}, score={p.score:.3f})" for p in products[:3]]
            obs = f"Search '{search_q}' → {len(products)} results: {', '.join(summaries)}"
        else:
            obs = f"Search '{search_q}' → 0 results"
        return obs, products

    elif tool_name == "memory_enrich":
        q = args.get("query", "")
        enriched_parts = [q]
        if preferences.get("preferred_colors"):
            enriched_parts.append(f"preferred colors: {', '.join(preferences['preferred_colors'])}")
        if preferences.get("preferred_categories"):
            enriched_parts.append(f"preferred categories: {', '.join(preferences['preferred_categories'])}")
        enriched = " ".join(enriched_parts)
        return f"Enriched query: '{enriched}'", []

    elif tool_name == "outfit_hints":
        occasion = args.get("occasion", "casual")
        style = args.get("style", "")
        try:
            import google.generativeai as genai
            key = api_key or os.getenv("GEMINI_API_KEY")
            if key:
                genai.configure(api_key=key)
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = f"Give a brief outfit suggestion for {occasion} occasion, {style} style. 2-3 items max. Respond as plain text."
                response = model.generate_content(prompt)
                return f"Outfit hints: {response.text.strip()[:200]}", []
        except Exception:
            pass
        return f"Outfit hints: Consider a smart casual outfit for {occasion}.", []

    return f"Unknown tool: {tool_name}", []


MAX_REACT_ITERATIONS = 8
LOW_CONFIDENCE_THRESHOLD = 0.5
MAX_CLARIFICATION_TURNS = 3

# In-memory storage for accumulated slots per session
# Key: session_id, Value: ExtractedSlots
_session_accumulated_slots: dict[str, ExtractedSlots] = {}


def chat(
    query: str,
    session_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> AgentResponse:
    """
    Main agent entry point — ReAct orchestrator.

    Orchestrates: intent → slot check → clarify if needed → memory →
    ReAct(plan→execute→observe) → synthesize.
    """
    # Get or create session
    if session_id and session_exists(session_id):
        pass
    else:
        session_id = create_session()

    # Save user message
    add_message(session_id, "user", query)

    # Load history
    history = get_history(session_id, limit=20)

    # Step 1: Intent classification + slot extraction (single LLM call)
    intent_result = classify_intent(query, history=history, api_key=api_key)

    # Step 2: Handle out_of_scope intent
    if intent_result.intent == "out_of_scope":
        answer = "Xin lỗi, tôi chỉ hỗ trợ tìm kiếm và tư vấn thời trang. Bạn muốn tìm trang phục gì không?"
        add_message(session_id, "assistant", answer)
        return AgentResponse(
            answer=answer,
            session_id=session_id,
            intent="out_of_scope",
        )

    # Step 3: Slot-based completeness check (text_search only)
    if intent_result.intent == "text_search":
        new_slots = intent_result.extracted_slots
        accumulated = _session_accumulated_slots.get(session_id, ExtractedSlots())

        # Check for topic reset (new category = new search)
        if should_reset_slots(accumulated, new_slots):
            accumulated = ExtractedSlots()

        # Merge new slots into accumulated
        accumulated = merge_slots(accumulated, new_slots)
        _session_accumulated_slots[session_id] = accumulated

        # Check completeness
        is_complete, missing = check_slot_completeness(accumulated)

        if not is_complete:
            # Count clarification turns in this conversation flow
            clarify_count = _count_clarification_turns(history)

            if clarify_count < MAX_CLARIFICATION_TURNS:
                # Ask targeted question about missing slots
                question = generate_targeted_question(
                    slots=accumulated,
                    missing_slots=missing,
                    history=history,
                    api_key=api_key,
                )
                add_message(session_id, "assistant", question)
                return AgentResponse(
                    answer=question,
                    session_id=session_id,
                    intent="clarification",
                    reasoning=f"Slot completeness insufficient. Missing: {', '.join(missing)}. "
                              f"Clarification turn {clarify_count + 1}/{MAX_CLARIFICATION_TURNS}.",
                )
            # Max clarification reached — proceed with what we have

        # Use slot-composed query for better search alignment
        search_query = compose_refined_query_from_slots(accumulated)
        if not search_query.strip():
            search_query = intent_result.refined_query or query

    elif intent_result.intent == "follow_up":
        # Follow-up: merge with accumulated slots from previous turns
        new_slots = intent_result.extracted_slots
        accumulated = _session_accumulated_slots.get(session_id, ExtractedSlots())
        accumulated = merge_slots(accumulated, new_slots)
        _session_accumulated_slots[session_id] = accumulated

        # Compose query from merged slots if available
        slot_query = compose_refined_query_from_slots(accumulated)
        search_query = slot_query if slot_query.strip() else (intent_result.refined_query or query)

    else:
        # outfit_request, unclear: use existing flow
        if intent_result.confidence < 0.6 or intent_result.intent == "unclear":
            clarification = check_clarification(query, history=history, api_key=api_key)
            if clarification.needs_clarification:
                add_message(session_id, "assistant", clarification.question)
                return AgentResponse(
                    answer=clarification.question,
                    session_id=session_id,
                    intent="unclear",
                    reasoning=f"Low confidence ({intent_result.confidence:.2f}). Asking for clarification.",
                )
        search_query = intent_result.refined_query or query

    # Step 3.5: Log query to memory & load preferences
    log_query(session_id, query, intent_result.intent, intent_result.filters)
    preferences = get_preferences(session_id)

    # Step 4: ReAct loop — plan → execute → observe
    all_products: list[NodeWithScore] = []
    reasoning_steps: list[str] = []
    observations: list[str] = []
    threshold = LOW_CONFIDENCE_THRESHOLD

    for iteration in range(1, MAX_REACT_ITERATIONS + 1):
        reasoning_steps.append(f"Thought (iter {iteration}): Planning next action for '{search_query}'")

        plan = _plan(
            query=search_query,
            intent=intent_result.intent,
            preferences=preferences,
            observations=observations,
            iteration=iteration,
            max_iter=MAX_REACT_ITERATIONS,
            api_key=api_key,
        )

        if not plan:
            reasoning_steps.append(f"Thought (iter {iteration}): Planner decided sufficient results. Stopping.")
            break

        for tool_call in plan[:2]:
            tool_name = tool_call.get("tool", "search")
            tool_args = tool_call.get("args", {})

            reasoning_steps.append(f"Action: {tool_name}({json.dumps(tool_args, ensure_ascii=False)[:100]})")

            obs, products = _execute_tool(tool_name, tool_args, preferences, api_key, filters=intent_result.filters)
            observations.append(obs)
            reasoning_steps.append(f"Observation: {obs[:150]}")

            if products:
                all_products = products

        if all_products and all_products[0].score > threshold:
            reasoning_steps.append(
                f"Thought: High confidence (score={all_products[0].score:.3f} > {threshold:.1f}). Proceeding to synthesis."
            )
            break

        if iteration == 4:
            threshold -= 0.2
            reasoning_steps.append(f"Thought: Lowering threshold to {threshold:.1f} after 4 iterations.")

        if iteration < MAX_REACT_ITERATIONS:
            category = intent_result.filters.get("category", "")
            search_query = f"{query} {category} fashion".strip()
            reasoning_steps.append(f"Thought: Refining query to '{search_query}'")

    # Step 5: Synthesize response (with preferences)
    answer, styling = _synthesize_response(
        query=query,
        products=all_products,
        history=history,
        intent=intent_result.intent,
        preferences=preferences,
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
        for p in all_products
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


def _count_clarification_turns(history: list[Message]) -> int:
    """Count consecutive clarification turns (assistant messages that are questions).

    Looks backward from the most recent messages to count how many times
    the agent asked for clarification vs gave search results.
    """
    count = 0
    # Walk backward through history, counting assistant messages that look like questions
    for msg in reversed(history):
        if msg.role == "assistant":
            # Check if this message was a clarification (contains question marks)
            if "?" in msg.content or "không?" in msg.content:
                count += 1
            else:
                break  # Found a non-question assistant message — stop counting
        elif msg.role == "user":
            # User message between clarifications — continue counting
            continue
    return count
