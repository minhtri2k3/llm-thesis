"""Clarification gate: detects vague queries and requests more info."""

from __future__ import annotations

from dataclasses import dataclass

# Vague query patterns (too short or too generic)
VAGUE_KEYWORDS = {
    "đồ", "quần áo", "thứ gì", "cái gì", "something", "anything",
    "tìm đồ", "đẹp", "nice", "good", "cool", "hay", "ổn",
}

MIN_QUERY_LENGTH = 4  # characters


@dataclass
class ClarificationResult:
    needs_clarification: bool
    question: str = ""


def check_clarification(query: str) -> ClarificationResult:
    """
    Check if a query is too vague for meaningful search.

    Returns ClarificationResult with a question if clarification is needed.
    """
    query_stripped = query.strip()

    # Too short
    if len(query_stripped) < MIN_QUERY_LENGTH:
        return ClarificationResult(
            needs_clarification=True,
            question="Bạn muốn tìm loại trang phục nào? (áo, quần, váy, giày...) Màu sắc ưa thích?",
        )

    # Check for vague-only queries
    words = set(query_stripped.lower().split())
    non_vague_words = words - VAGUE_KEYWORDS
    if len(non_vague_words) == 0:
        return ClarificationResult(
            needs_clarification=True,
            question=(
                "Bạn có thể mô tả cụ thể hơn không? Ví dụ:\n"
                "- Loại trang phục: áo sơ mi, váy, quần jeans...\n"
                "- Màu sắc: trắng, đen, xanh navy...\n"
                "- Dịp sử dụng: đi làm, đi chơi, dự tiệc..."
            ),
        )

    return ClarificationResult(needs_clarification=False)
