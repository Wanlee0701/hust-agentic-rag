"""
confidence_gate.py — Postprocessing: xử lý câu trả lời dựa trên confidence score.

Logic 3 mức:
  - confidence < low_threshold  → reject (từ chối trả lời)
  - low ≤ confidence < high     → warn (trả lời kèm cảnh báo)
  - confidence ≥ high_threshold → pass (trả lời bình thường)
"""
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class GateResult:
    """Kết quả từ Confidence Gate."""
    action: str        # 'reject' | 'warn' | 'pass'
    answer: str
    confidence: float
    success: bool


class ConfidenceGate:
    """
    Post-processing gate: quyết định cách trả lời dựa trên confidence.
    """

    DEFAULT_HIGH = 0.65
    DEFAULT_LOW = 0.35

    def __init__(self, high_threshold: float = None, low_threshold: float = None):
        self.high = high_threshold if high_threshold is not None else self.DEFAULT_HIGH
        self.low = low_threshold if low_threshold is not None else self.DEFAULT_LOW

    def evaluate(self, confidence: float, raw_answer: str, question: str) -> GateResult:
        """
        Đánh giá và xử lý câu trả lời.

        Args:
            confidence: Điểm confidence (0.0 - 1.0).
            raw_answer: Câu trả lời từ GenerateTool.
            question: Câu hỏi gốc.

        Returns:
            GateResult với action và answer đã xử lý.
        """
        if confidence < self.low:
            logger.warning(
                f"[ConfidenceGate] {confidence:.1%} < {self.low:.0%} → reject"
            )
            return GateResult(
                action="reject",
                answer=self._no_result_answer(question),
                confidence=confidence,
                success=False,
            )
        elif confidence < self.high:
            logger.info(
                f"[ConfidenceGate] {confidence:.1%} in warning zone → warn"
            )
            warning = (
                f"\n\n---\n⚠️ *Lưu ý: Độ tin cậy của câu trả lời này ở mức trung bình "
                f"({confidence:.0%}). Vui lòng kiểm tra lại với tài liệu gốc hoặc liên hệ "
                f"Phòng Đào tạo để xác nhận.*"
            )
            return GateResult(
                action="warn",
                answer=raw_answer + warning,
                confidence=confidence,
                success=True,
            )
        else:
            logger.info(
                f"[ConfidenceGate] {confidence:.1%} >= {self.high:.0%} → pass"
            )
            return GateResult(
                action="pass",
                answer=raw_answer,
                confidence=confidence,
                success=True,
            )

    @staticmethod
    def _no_result_answer(question: str) -> str:
        return (
            f"Xin lỗi, tôi không tìm thấy thông tin liên quan đến câu hỏi: **'{question}'** "
            f"trong cơ sở dữ liệu quy chế hiện tại.\n\n"
            f"Bạn có thể:\n"
            f"• Thử hỏi lại với từ khóa khác (ví dụ: tên Chương, Điều cụ thể)\n"
            f"• Liên hệ Phòng Đào tạo hoặc Phòng Công tác Sinh viên ĐHBK Hà Nội\n"
            f"• Tra cứu trực tiếp: https://hust.edu.vn"
        )

    @staticmethod
    def calculate_confidence(
        results: list, answer: str, iterations: int
    ) -> float:
        """
        Tính confidence score dựa trên 3 yếu tố.

        Args:
            results: List[(Document, score)].
            answer: Câu trả lời đã sinh.
            iterations: Số hop đã thực hiện.

        Returns:
            Confidence score (0.0 - 1.0).
        """
        score = 0.0

        # Yếu tố 1: Số lượng docs (tối đa 0.30)
        doc_count = len(results)
        score += min(doc_count / 5, 1.0) * 0.30

        # Yếu tố 2: Chất lượng câu trả lời (tối đa 0.40)
        if answer:
            answer_lower = answer.lower()
            has_numbers = any(c.isdigit() for c in answer)
            has_legal = any(
                t in answer_lower
                for t in [
                    "điều", "khoản", "chương", "tín chỉ", "gpa", "cpa",
                    "%", "học kỳ", "năm học", "quyết định",
                ]
            )
            is_negative = any(
                t in answer_lower
                for t in ["không biết", "không tìm thấy", "không có thông tin", "xin lỗi"]
            )
            if is_negative:
                score += 0.0
            elif has_numbers and has_legal:
                score += 0.40
            elif has_numbers or has_legal:
                score += 0.25
            elif len(answer) > 100:
                score += 0.15

        # Yếu tố 3: Hiệu quả (tối đa 0.30)
        if iterations <= 2:
            score += 0.30
        elif iterations <= 4:
            score += 0.20
        elif iterations <= 6:
            score += 0.10

        return round(min(max(score, 0.0), 1.0), 2)
