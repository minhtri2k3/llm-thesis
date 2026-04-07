"""Test Task 8.1 — verify fixed language detection.

Tests that common English phrases are NOT mis-detected as Spanish
after the ambiguous token fix (removing 'el', 'la', 'un', 'una', etc.).
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.prompts import detect_language


# ── English phrases that the OLD regex would falsely classify as Spanish ──────

ENGLISH_SHOULD_NOT_BE_SPANISH = [
    # Ambiguous words like 'la', 'el', 'un', 'una', 'en', 'es' appear in English
    "I want a lace dress in unique style",       # 'la' in 'lace'
    "Can you show me elegant outfits?",          # 'un' — none, but 'me'
    "I need a blue shirt for the beach",         # the, a
    "Show me the latest fashion trends",         # the
    "What are some casual shoes for men?",
    "I want something formal for a party",
    "Looking for a red cocktail dress",
    "Can you recommend nice sneakers?",
    "Find me a black leather jacket",
    "I like minimal and clean aesthetics",
]

SPANISH_SHOULD_BE_SPANISH = [
    "quiero una camisa elegante",
    "muéstrame vestidos de noche",
    "busco ropa de sport",
    "hola, necesito ayuda",
    "¿dónde están los vestidos?",
    "gracias, es perfecto",
    "tengo una boda el sábado",
]

VIETNAMESE_SHOULD_BE_VIETNAMESE = [
    "tôi muốn mua áo sơ mi trắng",
    "tìm giúp tôi đầm dự tiệc",
    "cho tôi xem các mẫu giày mới nhất",
]


class TestDetectLanguage:
    def test_english_not_misdetected_as_spanish(self):
        for phrase in ENGLISH_SHOULD_NOT_BE_SPANISH:
            result = detect_language(phrase)
            assert result == "en", (
                f"FAIL: '{phrase}' detected as '{result}', expected 'en'. "
                f"Check for ambiguous Spanish tokens in regex."
            )

    def test_spanish_is_detected(self):
        for phrase in SPANISH_SHOULD_BE_SPANISH:
            result = detect_language(phrase)
            assert result == "es", (
                f"FAIL: '{phrase}' detected as '{result}', expected 'es'."
            )

    def test_vietnamese_is_detected(self):
        for phrase in VIETNAMESE_SHOULD_BE_VIETNAMESE:
            result = detect_language(phrase)
            assert result == "vi", (
                f"FAIL: '{phrase}' detected as '{result}', expected 'vi'."
            )

    def test_empty_string_defaults_to_english(self):
        assert detect_language("") == "en"
        assert detect_language("   ") == "en"

    def test_mixed_case_spanish_detected(self):
        assert detect_language("QUIERO VER VESTIDOS") == "es"

    def test_spanish_special_chars_detected(self):
        assert detect_language("¿Tienes una camisa?") == "es"
        assert detect_language("¡Hola! necesito ayuda") == "es"
        assert detect_language("mañana voy a comprar ropa") == "es"  # ñ
