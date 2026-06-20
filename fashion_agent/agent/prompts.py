"""Kho prompt tập trung cho Fashion Agent.

Tất cả chỉ dẫn gửi cho LLM và template message cho người dùng đều nằm ở đây.
Các prompt nội dung vẫn giữ tiếng Anh để không đổi hành vi của mô hình, còn
docstring và comment được viết bằng tiếng Việt để dễ tra cứu trong source.

Cảnh báo: không khai báo prompt mới trực tiếp ở module khác.
Hãy thêm vào đây để mọi template đều có thể review ở một chỗ.
"""

import re

def detect_language(text: str) -> str:
    """Nhận diện ngôn ngữ của tin nhắn người dùng và trả về `vi`, `es` hoặc `en`.

    Thứ tự nhận diện:
    1. Tiếng Việt — các dấu đặc trưng không xuất hiện trong tiếng Tây Ban Nha
    2. Tiếng Tây Ban Nha — ñ, ¿, ¡ hoặc các từ khóa không mơ hồ
    3. Tiếng Anh — fallback mặc định

    Lưu ý: các từ ngắn phổ biến như `el`, `la`, `un`, `una`, `es`, `son`
    được cố ý loại trừ để giảm false positive khi văn bản là tiếng Anh.
    """
    if not text or not text.strip():
        return "en"
    # Vietnamese: tonal diacritics + ă ơ ư đ (characters absent in Spanish)
    vi_pattern = re.compile(
        r'[àảãạăắặẵặâấầẩẫậèẻẽẹêếềểễệìỉĩịòỏõọôốồổỗộơớờởỡợùủũụưứừửữựỳýỷỹỵđ]',
        re.IGNORECASE
    )
    if vi_pattern.search(text):
        return "vi"
    # Spanish: unambiguous tokens ONLY
    # - Special chars: ñ, ¿, ¡
    # - Unambiguously Spanish words not shared with English
    es_pattern = re.compile(
        r'[ñ¿¡]|\b(quiero|necesito|busco|muéstrame|vestido|ropa|camisa|pantalón|falda|'
        r'también|cómo|gracias|hola|tengo|dónde|cuánto|quieres|tiene|tienes|'
        r'qué|está|estás|estoy|ser|del|una que|unos|unas)\b',
        re.IGNORECASE
    )
    if es_pattern.search(text):
        return "es"
    return "en"

def get_template(template_store: dict, key: any, lang: str) -> str:
    """Lấy an toàn một template song ngữ từ kho template."""
    item = template_store.get(key)
    if not item:
        return ""
    return item.get(lang, item.get("en", ""))

# ---------------------------------------------------------------------------
# Out-of-Scope Response  (used by agent/fashion_agent.py)
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


# ---------------------------------------------------------------------------
# Unsupported Category Response  (used by agent/fashion_agent.py)
# ---------------------------------------------------------------------------

UNSUPPORTED_CATEGORY_RESPONSE = {
    "en": "Sorry, we don't carry {category} in our catalog. You might enjoy: {suggestions}.",
    "vi": "Xin lỗi, chúng tôi không có {category} trong danh mục. Bạn có thể thích: {suggestions}.",
    "es": "Lo siento, no tenemos {category} en nuestro catálogo. Podrías disfrutar: {suggestions}.",
}

UNSUPPORTED_CATEGORY_NO_SUGGESTIONS = {
    "en": "Sorry, we don't carry {category} in our catalog. Please browse our available categories!",
    "vi": "Xin lỗi, chúng tôi không có {category} trong danh mục. Vui lòng xem các danh mục hiện có!",
    "es": "Lo siento, no tenemos {category} en nuestro catálogo. ¡Por favor explora nuestras categorías disponibles!",
}


def build_unsupported_category_message(category: str, suggestions: list[str], lang: str) -> str:
    """Tạo thông báo từ chối đa ngôn ngữ cho category không được hỗ trợ.

    Tham số:
        category: Tên category mà người dùng đã yêu cầu.
        suggestions: Danh sách lựa chọn thay thế gợi ý (có thể rỗng).
        lang: Mã ngôn ngữ (`en`, `vi`, `es`).

    Trả về:
        Chuỗi thông báo đã được định dạng.
    """
    if suggestions:
        template = UNSUPPORTED_CATEGORY_RESPONSE.get(lang, UNSUPPORTED_CATEGORY_RESPONSE["en"])
        suggestions_text = ", ".join(suggestions[:-1]) + f", or {suggestions[-1]}" if len(suggestions) > 1 else suggestions[0]
        return template.format(category=category.title(), suggestions=suggestions_text)
    else:
        template = UNSUPPORTED_CATEGORY_NO_SUGGESTIONS.get(lang, UNSUPPORTED_CATEGORY_NO_SUGGESTIONS["en"])
        return template.format(category=category.title())


# ---------------------------------------------------------------------------
# Intent Classification  (used by agent/intent_classifier.py)
# ---------------------------------------------------------------------------

INTENT_PROMPT = """You are operating within a multilingual fashion recommendation research system designed to study LLM recommendation quality and user purchase intent. You serve Vietnamese, Spanish, and English users. All your responses MUST be in the same language as the user's message.

You are a fashion shopping assistant. Classify the user's message into one of these intents:

1. "text_search" — User wants to find specific fashion items (e.g., "find a white shirt", "show me blue dresses")
2. "outfit_request" — User wants fashion recommendations, outfit suggestions, or styling advice (e.g., "suggest an outfit for a party", "what goes with a black blazer?")
3. "follow_up" — User is following up on a previous search/recommendation (e.g., "any other colors?", "anything cheaper?", "the second one")
4. "product_select" — User wants to SELECT/CHOOSE specific products from the most recently shown search results. Signals: numbers (1-6, "#2"), ordinals ("first", "third", "đầu tiên"), selection verbs ("I want", "lấy", "chọn", "pick", "I'll take"), or description references ("the quilted one", "cái áo navy"). ONLY classify as product_select if the conversation history shows recent search results were displayed.
5. "view_selections" — User wants to view their saved/selected products (e.g., "show my selections", "what did I pick?", "my picks", "xem các sản phẩm đã chọn", "ver mis selecciones")
6. "out_of_scope" — User is asking about non-fashion topics (e.g., "today's weather", "how to cook pasta")
7. "unclear" — User's request is too vague to search or classify (e.g., "find something nice", "something cool")

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

AND if intent is "product_select", extract:
- selected_numbers: a list of integers representing which product numbers the user selected. Map ordinals to numbers (first=1, second=2, third=3, etc.). Map descriptions to the matching product number from the conversation history. Return [] if the specific product cannot be determined.

Set each slot to "" if the user did NOT mention that information.

And provide a refined search query in English that would work well for semantic search.
Provide a confidence score from 0.0 to 1.0 indicating how certain you are about the classification.

## Few-shot examples:

User: "find a white cotton slim fit minimalist shirt"
→ {{"intent": "text_search", "confidence": 0.95, "filters": {{"category": "Shirt", "color": "white", "style": "minimalist", "occasion": ""}}, "refined_query": "white cotton slim fit minimalist shirt", "slot_category": "Shirt", "slot_color": "white", "slot_fabric": "cotton", "slot_fit": "slim fit", "slot_construction": "", "slot_aesthetic": "minimalist", "selected_numbers": []}}

User: "find a white men's shirt"
→ {{"intent": "text_search", "confidence": 0.95, "filters": {{"category": "Shirt", "color": "white", "style": "", "occasion": ""}}, "refined_query": "white men shirt", "slot_category": "Shirt", "slot_color": "white", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": "", "selected_numbers": []}}

User: "suggest an outfit for a weekend party"
→ {{"intent": "outfit_request", "confidence": 0.9, "filters": {{"category": "", "color": "", "style": "party", "occasion": "weekend party"}}, "refined_query": "party outfit weekend", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": "party", "selected_numbers": []}}

User: "what about blue?"
→ {{"intent": "follow_up", "confidence": 0.85, "filters": {{"category": "", "color": "blue", "style": "", "occasion": ""}}, "refined_query": "blue variant", "slot_category": "", "slot_color": "blue", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": "", "selected_numbers": []}}

User: "2" (after search results were shown)
→ {{"intent": "product_select", "confidence": 0.9, "filters": {{}}, "refined_query": "", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": "", "selected_numbers": [2]}}

User: "I want the first and third one" (after search results were shown)
→ {{"intent": "product_select", "confidence": 0.9, "filters": {{}}, "refined_query": "", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": "", "selected_numbers": [1, 3]}}

User: "lấy cái áo quilted navy" (after results show a quilted navy item at #2)
→ {{"intent": "product_select", "confidence": 0.85, "filters": {{}}, "refined_query": "", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": "", "selected_numbers": [2]}}

User: "show my selections"
→ {{"intent": "view_selections", "confidence": 0.95, "filters": {{}}, "refined_query": "", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": "", "selected_numbers": []}}

User: "what's the weather like today?"
→ {{"intent": "out_of_scope", "confidence": 0.95, "filters": {{}}, "refined_query": "", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": "", "selected_numbers": []}}

User: "find something nice"
→ {{"intent": "unclear", "confidence": 0.4, "filters": {{}}, "refined_query": "", "slot_category": "", "slot_color": "", "slot_fabric": "", "slot_fit": "", "slot_construction": "", "slot_aesthetic": "", "selected_numbers": []}}

## Conversation history (last 4 messages):
{history_text}

Respond ONLY with valid JSON in this exact format:
{{
    "intent": "text_search|outfit_request|follow_up|product_select|view_selections|out_of_scope|unclear",
    "confidence": 0.0,
    "filters": {{"category": "", "color": "", "style": "", "occasion": ""}},
    "refined_query": "",
    "slot_category": "",
    "slot_color": "",
    "slot_fabric": "",
    "slot_fit": "",
    "slot_construction": "",
    "slot_aesthetic": "",
    "selected_numbers": []
}}

User message: """


# ---------------------------------------------------------------------------
# Clarification Gate  (used by agent/clarification_gate.py)
# ---------------------------------------------------------------------------

CLARIFICATION_PROMPT = """You are a fashion shopping assistant. The user's query is unclear or too vague.
Based on the query and conversation history, generate a helpful clarification question
to understand what the user is looking for.

Your question should:
1. Be in the same language as the user's query (Vietnamese , English or Spanish)
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

FALLBACK_QUESTION = {
    "en": (
        "Could you describe more specifically what you're looking for? For example:\n"
        "- Clothing type: shirt, dress, jeans...\n"
        "- Color: white, black, navy blue...\n"
        "- Occasion: work, casual, party..."
    ),
    "vi": (
        "Bạn có thể mô tả chi tiết hơn bạn đang tìm kiếm gì không? Ví dụ:\n"
        "- Loại trang phục: áo thun, váy, quần jeans...\n"
        "- Màu sắc: trắng, đen, xanh biển...\n"
        "- Dịp sử dụng: công sở, đi chơi, dự tiệc..."
    ),
    "es": (
        "¿Podrías describir con más detalle lo que estás buscando? Por ejemplo:\n"
        "- Tipo de ropa: camisa, vestido, jeans...\n"
        "- Color: blanco, negro, azul marino...\n"
        "- Ocasión: trabajo, casual, fiesta..."
    ),
}


# ---------------------------------------------------------------------------
# Slot Completeness Templates  (used by agent/slot_completeness.py)
# ---------------------------------------------------------------------------

SLOT_TEMPLATES: dict[str, dict[str, str]] = {
    "category": {
        "en": "clothing type (shirt, dress, jeans, jacket...)",
        "vi": "loại trang phục (áo, đầm, quần jeans, áo khoác...)",
        "es": "tipo de ropa (camisa, vestido, jeans, chaqueta...)",
    },
    "color": {
        "en": "color (white, black, navy blue, pastel pink...)",
        "vi": "màu sắc (trắng, đen, xanh navy, hồng pastel...)",
        "es": "color (blanco, negro, azul marino, rosa pastel...)",
    },
    "fabric": {
        "en": "material (cotton, linen, silk, denim, chiffon...)",
        "vi": "chất liệu (cotton, linen, lụa, denim, chiffon...)",
        "es": "material (algodón, lino, seda, denim, gasa...)",
    },
    "fit": {
        "en": "fit/silhouette (slim fit, oversized, A-line, regular...)",
        "vi": "kiểu dáng (slim fit, oversized, chữ A, regular...)",
        "es": "ajuste/silueta (slim fit, holgado, línea A, regular...)",
    },
}

COMBO_TEMPLATES: dict[frozenset[str], dict[str, str]] = {
    frozenset({"category", "color"}): {
        "en": (
            "I need a bit more detail to find the right items! 🛍️\n"
            "• What **clothing type** are you looking for? (shirt, dress, pants...)\n"
            "• Any **color** preference? (white, black, navy blue...)"
        ),
        "vi": (
            "Tôi cần thêm chi tiết để tìm sản phẩm phù hợp! 🛍️\n"
            "• Bạn đang tìm **loại trang phục** nào? (áo, đầm, quần...)\n"
            "• Bạn có thích **màu sắc** nào không? (trắng, đen, xanh biển...)"
        ),
        "es": (
            "¡Necesito un poco más de detalle para encontrar lo que buscas! 🛍️\n"
            "• ¿Qué **tipo de ropa** buscas? (camisa, vestido, pantalón...)\n"
            "• ¿Tienes alguna preferencia de **color**? (blanco, negro, azul marino...)"
        ),
    },
    frozenset({"category", "color", "fabric", "fit"}): {
        "en": (
            "Could you share a few more details? ✨\n"
            "• **Clothing type**: shirt, dress, jeans, jacket...\n"
            "• **Color**: white, black, navy blue, pastel pink...\n"
            "• **Material / fit**: cotton slim fit, linen oversized..."
        ),
        "vi": (
            "Bạn có thể chia sẻ thêm vài chi tiết không? ✨\n"
            "• **Loại trang phục**: áo, đầm, quần jeans, áo khoác...\n"
            "• **Màu sắc**: trắng, đen, xanh navy, hồng pastel...\n"
            "• **Chất liệu / kiểu dáng**: cotton ôm, đũi phom rộng..."
        ),
        "es": (
            "¿Podrías compartir algunos detalles más? ✨\n"
            "• **Tipo de ropa**: camisa, vestido, jeans, chaqueta...\n"
            "• **Color**: blanco, negro, azul marino, rosa pastel...\n"
            "• **Material / ajuste**: algodón slim fit, lino holgado..."
        ),
    },
    frozenset({"color", "fabric", "fit"}): {
        "en": (
            "Great, I know you're looking for {category}! 👍\n"
            "A few more details would help:\n"
            "• **Color**? (white, black, navy blue...)\n"
            "• **Material / fit**? (cotton slim fit, silk A-line...)"
        ),
        "vi": (
            "Tuyệt, tôi biết bạn đang tìm {category}! 👍\n"
            "Thêm vài chi tiết sẽ giúp tôi tìm chính xác hơn:\n"
            "• **Màu sắc**? (trắng, đen, xanh dương...)\n"
            "• **Chất liệu / kiểu dáng**? (cotton dáng ôm, lụa dáng chữ A...)"
        ),
        "es": (
            "¡Genial, sé que buscas {category}! 👍\n"
            "Algunos detalles más me ayudarían:\n"
            "• ¿**Color**? (blanco, negro, azul marino...)\n"
            "• ¿**Material / ajuste**? (algodón slim fit, seda línea A...)"
        ),
    },
    frozenset({"fabric", "fit"}): {
        "en": (
            "Perfect, I'll search for {category} in {color}! 🎨\n"
            "Any preference for **material** or **fit**?\n"
            "e.g. cotton slim fit, linen oversized, denim regular..."
        ),
        "vi": (
            "Tuyệt vời, tôi sẽ tìm {category} màu {color}! 🎨\n"
            "Bạn thích **chất liệu** hay **kiểu dáng** nào không?\n"
            "ví dụ: cotton ôm, vải lanh rộng rãi, denim dáng cơ bản..."
        ),
        "es": (
            "¡Perfecto, buscaré {category} en {color}! 🎨\n"
            "¿Tienes alguna preferencia de **material** o **ajuste**?\n"
            "ej. algodón slim fit, lino holgado, denim regular..."
        ),
    },
    frozenset({"color"}): {
        "en": (
            "I need to know your preferred **color**! 🎨\n"
            "e.g. white, black, navy blue, pastel pink, beige..."
        ),
        "vi": (
            "Tôi cần biết **màu sắc** bạn thích! 🎨\n"
            "ví dụ: trắng, đen, xanh dương, hồng pastel, ghi..."
        ),
        "es": (
            "¡Necesito saber tu **color** preferido! 🎨\n"
            "ej. blanco, negro, azul marino, rosa pastel, beige..."
        ),
    },
    frozenset({"category"}): {
        "en": (
            "What **clothing type** are you looking for? 🛍️\n"
            "e.g. shirt, dress, jeans, jacket, coat..."
        ),
        "vi": (
            "Bạn đang tìm **loại trang phục** nào? 🛍️\n"
            "ví dụ: áo sơ mi, váy đầm, quần jeans, áo khoác..."
        ),
        "es": (
            "¿Qué **tipo de ropa** buscas? 🛍️\n"
            "ej. camisa, vestido, jeans, chaqueta, abrigo..."
        ),
    },
}


# ---------------------------------------------------------------------------
# Synthesis  (used by agent/fashion_agent.py)
# ---------------------------------------------------------------------------

_LANG_NAMES = {"en": "English", "vi": "Vietnamese", "es": "Spanish"}

_BASE_SYNTHESIS_PROMPT = """You are operating within a multilingual fashion recommendation research system designed to study LLM recommendation quality and user purchase intent. You serve Vietnamese, Spanish, and English users. User selections are academic data points (not real purchases), and you should encourage users to select products they genuinely prefer without mentioning real transaction language.

YOU MUST respond exclusively in {language}. Do not use any other language, even if the conversation history contains other languages.

You are a helpful fashion shopping assistant. Based on the search results and user query, provide a natural, helpful response.
{gender_context}
User query: {query}

Search results (top products):
{products_text}

User preferences: {preferences_text}

Conversation history:
{history_text}

Instructions:
1. Respond EXCLUSIVELY in {language}. This is mandatory — do not switch languages.
2. Briefly describe the top recommendations and why they match.
3. If this is a "recommend" intent, include styling suggestions.
4. Keep the response concise (2-4 sentences for search, 3-5 for recommendations).
5. Reference specific products by their NUMBER (1, 2, 3...) matching the order provided above. Do NOT reorder or renumber products.
6. If user preferences are available, personalize recommendations based on their preferred colors and categories.
7. If the user hasn't specified construction details or aesthetic style, briefly suggest options.
8. NEVER mention cart, purchase, checkout, ordering, or "added to cart". You are a search assistant that PRESENTS results only. Do NOT claim any action was performed.
9. End your response with exactly this call-to-action: "{cta_example}"
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

After presenting the products, if items were found, add 1–2 sentences proactively suggesting
what might pair well or what the user might want to explore next (e.g. matching trousers for a
shirt, or a bag to complete the look). Keep it concise, natural, and specific to the items shown.
Label it naturally as a suggestion — do NOT add this section if no products were found.
"""

# Agentic synthesis prompts (Mode B and C) — tool_results replaces products_text
_BASE_SYNTHESIS_PROMPT_AGENTIC = """You are operating within a multilingual fashion recommendation research system designed to study LLM recommendation quality and user purchase intent. You serve Vietnamese, Spanish, and English users. User selections are academic data points (not real purchases).

YOU MUST respond exclusively in {language}. Do not use any other language, even if the conversation history contains other languages.

You are a helpful fashion shopping assistant. An AI orchestrator has already searched for products on your behalf. Use the tool results below to compose a natural, helpful response.
{gender_context}
User query: {query}

Tool Results:
{tool_results}

User preferences: {preferences_text}

Conversation history:
{history_text}

Instructions:
1. Respond EXCLUSIVELY in {language}. This is mandatory — do not switch languages.
2. Briefly describe the top recommendations and why they match the user's request.
3. If this is a styling/outfit request, include styling suggestions.
4. Keep the response concise (2-4 sentences for search, 3-5 for recommendations).
5. Reference specific products by their NUMBER (1, 2, 3...) as shown in Tool Results.
6. If user preferences are available, personalize recommendations accordingly.
7. NEVER mention cart, purchase, checkout, or "added to cart". Present results only.
8. End your response with exactly this call-to-action: "{cta_example}"
"""

SYNTHESIS_PROMPT_AGENTIC = _BASE_SYNTHESIS_PROMPT_AGENTIC + """
Respond with ONLY a JSON object:
{{
    "answer": "<your natural language response>",
    "styling_suggestion": "<optional styling tips, empty string if not applicable>"
}}
"""

STREAM_SYNTHESIS_PROMPT_AGENTIC = _BASE_SYNTHESIS_PROMPT_AGENTIC + """
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
