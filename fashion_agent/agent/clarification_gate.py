"""Cổng clarification: tạo câu hỏi làm rõ cho query mơ hồ hoặc không rõ ý định.

Mục đích tổng thể:
- File này quyết định câu hỏi cần hỏi lại khi bước phân loại intent trước đó
  cho biết query chưa rõ hoặc confidence thấp.
- File này không nên chịu trách nhiệm parse JSON intent chính từ intent_classifier.py.
- Input của file này nên là dữ liệu đã được chuẩn hóa bởi các bước trước trong pipeline.
- Khi được gọi, file này giả định rằng hệ thống đã cần clarification và chỉ tập trung
  tạo câu hỏi follow-up hữu ích cho người dùng.

Các object và method chính:
- ClarificationResult: object kết quả nhỏ được pipeline chat sử dụng. Nó cho biết
  có cần clarification hay không và câu hỏi nào sẽ được hiển thị cho người dùng.
- check_clarification(): function public chính. Nó phát hiện ngôn ngữ của query,
  chuẩn bị câu hỏi fallback, gọi Gemini để tạo câu hỏi clarification động,
  parse JSON clarification, và trả về ClarificationResult. Nếu Gemini không khả dụng
  hoặc parse lỗi, nó trả về câu hỏi fallback theo ngôn ngữ.

Quan hệ trong pipeline:
- intent_classifier.py xử lý JSON thô từ Gemini cho intent và slot extraction.
- clarification_gate.py chỉ xử lý câu hỏi clarification sau khi hệ thống đã xác định
  query mơ hồ, confidence thấp, hoặc unclear.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.utils import parse_llm_json, format_history_text
from agent.prompts import CLARIFICATION_PROMPT, FALLBACK_QUESTION, detect_language
from shared.llm import get_model


@dataclass
class ClarificationResult:
    """Kết quả của bước hỏi lại khi query còn mơ hồ."""

    needs_clarification: bool
    question: str = ""


def check_clarification(
    query: str,
    history: list | None = None,
) -> ClarificationResult:
    """Tạo câu hỏi làm rõ bằng LLM cho những intent chưa rõ.

    Hàm này dùng Gemini để sinh câu hỏi follow-up ngắn gọn khi query quá mơ hồ.
    Nếu LLM không sẵn sàng hoặc JSON trả về lỗi, hàm sẽ dùng câu hỏi dự phòng
    theo ngôn ngữ của người dùng.
    """
    lang = detect_language(query)
    fallback_q = FALLBACK_QUESTION.get(lang, FALLBACK_QUESTION["en"])

    try:
        model = get_model()
    except RuntimeError:
        return ClarificationResult(
            needs_clarification=True,
            question=fallback_q,
        )

    history_text = format_history_text(history, limit=4)

    prompt = CLARIFICATION_PROMPT.format(
        query=query,
        history_text=history_text,
    )

    try:
        response = model.generate_content(prompt)
        data = parse_llm_json(response.text)
        question = data.get("question", "")
        if question:
            return ClarificationResult(
                needs_clarification=True,
                question=question,
            )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Clarification LLM failed: %s", exc)

    # Fallback
    return ClarificationResult(
        needs_clarification=True,
        question=fallback_q,
    )
