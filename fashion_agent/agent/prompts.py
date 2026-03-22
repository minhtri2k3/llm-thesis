"""
Centralized prompt templates for the Fashion Agent.

All LLM prompt instructions and user-facing message templates live here.
Language: English — LLM auto-adapts output to user's language via instructions.

WARNING: Do NOT define new prompts inline in other modules.
         Add them here so every template is reviewable in one place.
"""

# ---------------------------------------------------------------------------
# Intent Classification  (used by agent/intent_classifier.py)
# ---------------------------------------------------------------------------

INTENT_PROMPT = """You are a fashion shopping assistant. Classify the user's message into one of these intents:

1. "text_search" — User wants to find specific fashion items (e.g., "find a white shirt", "show me blue dresses")
2. "outfit_request" — User wants fashion recommendations, outfit suggestions, or styling advice (e.g., "suggest an outfit for a party", "what goes with a black blazer?")
3. "follow_up" — User is following up on a previous search/recommendation (e.g., "any other colors?", "anything cheaper?", "the second one")
4. "out_of_scope" — User is asking about non-fashion topics (e.g., "today's weather", "how to cook pasta")
5. "unclear" — User's request is too vague to search or classify (e.g., "find something nice", "something cool")

Also extract any mentioned filters:
- category: the type of clothing (Shirt, Dress, Pants, etc.)
- color: mentioned colors
- style: mentioned style (formal, casual, street, etc.)
- occasion: mentioned occasion (office, party, date, etc.)

AND extract these 6 detailed slots from the user's query:
- slot_category: specific type of clothing (e.g., "Shirt", "Dress", "Jacket", "Pants")
- slot_color: specific color (e.g., "white", "navy blue", "red with stripes")
- slot_fabric: material/texture (e.g., "cotton", "silk", "denim", "chiffon", "linen")
- slot_fit: silhouette/fit (e.g., "slim fit", "oversized", "A-line", "relaxed fit", "regular")
- slot_construction: construction details (e.g., "point collar", "zip closure", "button-down", "crew neck", "v-neck")
- slot_aesthetic: overall style/aesthetic (e.g., "casual", "formal", "minimalist", "vintage", "streetwear")

Set each slot to "" if the user did NOT mention that information.

And provide a refined search query in English that would work well for semantic search.
Provide a confidence score from 0.0 to 1.0 indicating how certain you are about the classification.

## Few-shot examples:

User: "find a white cotton slim fit minimalist shirt"
→ {{"intent": "text_search", "confidence": 0.95, "filters": {{"category": "Shirt", "color": "white", "style": "minimalist", "occasion": ""}}, "refined_query": "white cotton slim fit minimalist shirt", "slot_category": "Shirt", "slot_color": "white", "slot_fabric": "cotton", "slot_fit": "slim fit", "slot_construction": "", "slot_aesthetic": "minimalist"}}

User: "find a white men's shirt"
→ {{"intent": "text_search", "confidence": 0.95, "filters": {{"category": "Shirt", "color": "white", "style": "", "occasion": ""}}, "refined_query": "white men shirt", "slot_category": "Shirt", "slot_color": "white", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": ""}}

User: "suggest an outfit for a weekend party"
→ {{"intent": "outfit_request", "confidence": 0.9, "filters": {{"category": "", "color": "", "style": "party", "occasion": "weekend party"}}, "refined_query": "party outfit weekend", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": "party"}}

User: "what about blue?"
→ {{"intent": "follow_up", "confidence": 0.85, "filters": {{"category": "", "color": "blue", "style": "", "occasion": ""}}, "refined_query": "blue variant", "slot_category": "", "slot_color": "blue", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": ""}}

User: "what's the weather like today?"
→ {{"intent": "out_of_scope", "confidence": 0.95, "filters": {{}}, "refined_query": "", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": ""}}

User: "find something nice"
→ {{"intent": "unclear", "confidence": 0.4, "filters": {{}}, "refined_query": "", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": ""}}

## Conversation history (last 4 messages):
{history_text}

Respond ONLY with valid JSON in this exact format:
{{
    "intent": "text_search|outfit_request|follow_up|out_of_scope|unclear",
    "confidence": 0.0,
    "filters": {{"category": "", "color": "", "style": "", "occasion": ""}},
    "refined_query": "",
    "slot_category": "",
    "slot_color": "",
    "slot_fabric": "",
    "slot_fit": "",
    "slot_construction": "",
    "slot_aesthetic": ""
}}

User message: """


# ---------------------------------------------------------------------------
# Clarification Gate  (used by agent/clarification_gate.py)
# ---------------------------------------------------------------------------

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

FALLBACK_QUESTION = (
    "Could you describe more specifically what you're looking for? For example:\n"
    "- Clothing type: shirt, dress, jeans...\n"
    "- Color: white, black, navy blue...\n"
    "- Occasion: work, casual, party..."
)


# ---------------------------------------------------------------------------
# Slot Completeness Templates  (used by agent/slot_completeness.py)
# ---------------------------------------------------------------------------

SLOT_TEMPLATES: dict[str, str] = {
    "category": "clothing type (shirt, dress, jeans, jacket...)",
    "color": "color (white, black, navy blue, pastel pink...)",
    "fabric": "material (cotton, linen, silk, denim, chiffon...)",
    "fit": "fit/silhouette (slim fit, oversized, A-line, regular...)",
}

COMBO_TEMPLATES: dict[frozenset[str], str] = {
    frozenset({"category", "color"}): (
        "I need a bit more detail to find the right items! 🛍️\n"
        "• What **clothing type** are you looking for? (shirt, dress, pants...)\n"
        "• Any **color** preference? (white, black, navy blue...)"
    ),
    frozenset({"category", "color", "fabric", "fit"}): (
        "Could you share a few more details? ✨\n"
        "• **Clothing type**: shirt, dress, jeans, jacket...\n"
        "• **Color**: white, black, navy blue, pastel pink...\n"
        "• **Material / fit**: cotton slim fit, linen oversized..."
    ),
    frozenset({"color", "fabric", "fit"}): (
        "Great, I know you're looking for {category}! 👍\n"
        "A few more details would help:\n"
        "• **Color**? (white, black, navy blue...)\n"
        "• **Material / fit**? (cotton slim fit, silk A-line...)"
    ),
    frozenset({"fabric", "fit"}): (
        "Perfect, I'll search for {category} in {color}! 🎨\n"
        "Any preference for **material** or **fit**?\n"
        "e.g. cotton slim fit, linen oversized, denim regular..."
    ),
    frozenset({"color"}): (
        "I need to know your preferred **color**! 🎨\n"
        "e.g. white, black, navy blue, pastel pink, beige..."
    ),
    frozenset({"category"}): (
        "What **clothing type** are you looking for? 🛍️\n"
        "e.g. shirt, dress, jeans, jacket, coat..."
    ),
}


# ---------------------------------------------------------------------------
# Synthesis  (used by agent/fashion_agent.py)
# ---------------------------------------------------------------------------

_BASE_SYNTHESIS_PROMPT = """You are a helpful fashion shopping assistant. Based on the search results and user query, provide a natural, helpful response in the same language as the user's query.

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
7. If the user hasn't specified construction details or aesthetic style, briefly suggest options.
"""

SYNTHESIS_PROMPT = _BASE_SYNTHESIS_PROMPT + """
Respond with ONLY a JSON object:
{{
    "answer": "<your natural language response>",
    "styling_suggestion": "<optional styling tips, empty string if not applicable>"
}}
"""

STREAM_SYNTHESIS_PROMPT = _BASE_SYNTHESIS_PROMPT + """
IMPORTANT: Respond with plain text only (NO JSON format). Just write the response directly.
If you have styling suggestions, add them at the end after "💡 Styling tip: ".
"""


# ---------------------------------------------------------------------------
# Query Expansion  (used by search/query_expansion.py)
# ---------------------------------------------------------------------------

EXPANSION_PROMPT = """Generate {max_expansions} similar search queries for fashion items.
Each query should be a variation with synonyms or related terms.
Return ONLY a JSON array of strings, no explanation.

Original query: "{query}"

Example:
Original: "red dress"
Output: ["red dress", "crimson gown", "scarlet formal dress"]
"""
