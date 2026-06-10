"""
intent_classifier.py — Hybrid Intent Classification & Routing
Kết hợp: LLM (bóc tách ngữ nghĩa) + YAML config (kiểm tra business logic).

Luồng:
  1. LLM đọc câu hỏi + memory context → trả về JSON {intent, entities}
  2. So sánh entities bóc tách được với requires_fields trong YAML
  3. Bổ sung entity từ memory nếu còn thiếu
  4. Nếu vẫn thiếu → needs_clarification = True + sinh câu hỏi làm rõ
  5. Nếu đủ → pass vào RAG
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import sys

# Ensure logger handles UTF-8 properly
logger = logging.getLogger(__name__)

# Make sure logger propagates UTF-8 encoded messages
for handler in logger.handlers:
    if hasattr(handler, 'stream') and handler.stream:
        if hasattr(handler.stream, 'reconfigure'):
            try:
                handler.stream.reconfigure(encoding='utf-8', errors='replace')
            except:
                pass


# --------------------------------------------------------------------------- #
#  Result Dataclass                                                             #
# --------------------------------------------------------------------------- #

@dataclass
class IntentResult:
    """Kết quả phân loại intent từ một câu hỏi."""
    intent_name: str = "GENERAL_REGULATION"
    entities: Dict[str, Any] = field(default_factory=dict)
    needs_clarification: bool = False
    clarification_question: str = ""
    missing_fields: List[str] = field(default_factory=list)
    confidence: float = 1.0
    raw_llm_response: str = ""


# --------------------------------------------------------------------------- #
#  Prompt Template                                                              #
# --------------------------------------------------------------------------- #

_INTENT_EXTRACTION_PROMPT = """\
Bạn là bộ phân loại câu hỏi của hệ thống chatbot quy chế đào tạo ĐHBK Hà Nội.

## Danh sách Intent hợp lệ:
{intent_list}

## Lịch sử hội thoại gần đây (có thể trống):
{memory_context}

## Câu hỏi hiện tại của sinh viên:
"{question}"

## Nhiệm vụ:
1. Xác định intent phù hợp nhất từ danh sách trên.
2. Bóc tách các entity có trong câu hỏi HOẶC được nhắc tới trong lịch sử hội thoại:
   - nganh_hoc: tên ngành (ví dụ: "CNTT", "Cơ điện tử", "Toán - Tin", "Điện tử viễn thông")
   - khoa_hoc: khóa học (ví dụ: "K65", "K66", "K68", "K70")
   - gpa: điểm GPA nếu có (ví dụ: 3.2)
3. Nếu entity không có trong câu hỏi lẫn lịch sử → để null.

Trả về JSON duy nhất (KHÔNG giải thích thêm):
{{"intent": "INTENT_NAME", "entities": {{"nganh_hoc": null, "khoa_hoc": null, "gpa": null}}, "confidence": 0.0}}"""


# --------------------------------------------------------------------------- #
#  IntentClassifier                                                             #
# --------------------------------------------------------------------------- #

class IntentClassifier:
    """
    Hybrid Intent Classifier.

    - Đọc YAML config để biết intent definitions, required_fields.
    - Gọi LLM để bóc tách intent + entities từ câu hỏi.
    - Kết hợp với entity từ memory để quyết định clarification.
    """

    def __init__(
        self,
        intent_config: Dict[str, Any],
        llm_invoker: Callable[[str], str],
    ):
        """
        Args:
            intent_config: Dict từ config.yaml['intents']
            llm_invoker: Hàm gọi LLM, nhận prompt str → trả về str
        """
        self.intent_config = intent_config
        self._llm = llm_invoker
        self._intent_names = list(intent_config.keys())
        logger.info(
            f"[IntentClassifier] Loaded {len(self._intent_names)} intents: "
            f"{self._intent_names}"
        )

    # ----------------------------------------------------------------------- #
    #  Public API                                                               #
    # ----------------------------------------------------------------------- #

    def classify(
        self,
        question: str,
        memory_context: str = "",
        memory_entities: Optional[Dict[str, Any]] = None,
        previous_intent: Optional[str] = None,
    ) -> IntentResult:
        """
        Phân loại câu hỏi và kiểm tra entity yêu cầu.

        Args:
            question: Câu hỏi của người dùng.
            memory_context: Lịch sử hội thoại (plain text từ MemoryManager).
            memory_entities: Entity đã biết từ lịch sử (carry-over).
            previous_intent: [NEW] Intent từ turn trước (nếu được clarify). 
                           Dùng như hint để detector response-to-clarification.

        Returns:
            IntentResult với thông tin đầy đủ.
        """
        memory_entities = memory_entities or {}

        # 1. Gọi LLM để bóc tách intent + entities
        llm_result = self._call_llm(question, memory_context, previous_intent)

        # 2. Merge entity từ LLM với entity từ memory
        #    LLM có độ ưu tiên cao hơn (câu hỏi hiện tại cụ thể hơn lịch sử)
        merged_entities = {**memory_entities, **{
            k: v for k, v in llm_result["entities"].items() if v is not None
        }}

        intent_name = llm_result.get("intent", "GENERAL_REGULATION")
        # Fallback nếu LLM trả về intent không hợp lệ
        if intent_name not in self.intent_config:
            logger.warning(
                f"[IntentClassifier] LLM trả về intent không hợp lệ: '{intent_name}'. "
                f"Fallback về GENERAL_REGULATION."
            )
            intent_name = "GENERAL_REGULATION"
        
        # [NEW] Nếu previous_intent tồn tại (đang response to clarification),
        #       LLM có thể trả về intent khác.
        #       Khi đó, heuristic: nếu question không chứa từ khóa mới,
        #       assume user đang trả lời để làm rõ → reuse previous_intent
        if previous_intent and intent_name != previous_intent:
            # Heuristic đơn giản: nếu question rất ngắn hoặc chỉ là entity info
            # → nhiều khả năng đang respond to clarification
            is_clarification_response = len(question.split()) <= 15 or (
                "là" in question.lower() and 
                any(kw in question.lower() for kw in ["ngành", "khóa", "k6", "k7"])
            )
            if is_clarification_response:
                logger.info(
                    f"[IntentClassifier] Detected response to clarification. "
                    f"Reusing previous_intent='{previous_intent}' instead of '{intent_name}'."
                )
                intent_name = previous_intent

        # 3. Kiểm tra required_fields theo YAML
        intent_def = self.intent_config[intent_name]
        needs_clarification, missing_fields = self._check_required_fields(
            intent_def, merged_entities
        )

        # 4. Sinh câu hỏi làm rõ nếu cần
        clarification_question = ""
        if needs_clarification:
            clarification_question = self._build_clarification(intent_def, missing_fields)
            logger.info(
                f"[IntentClassifier] Intent='{intent_name}' | "
                f"Missing fields: {missing_fields} | Clarification triggered."
            )
        else:
            logger.info(
                f"[IntentClassifier] Intent='{intent_name}' | "
                f"Entities: {merged_entities} | Pass to RAG."
            )

        return IntentResult(
            intent_name=intent_name,
            entities=merged_entities,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
            missing_fields=missing_fields,
            confidence=llm_result.get("confidence", 1.0),
            raw_llm_response=llm_result.get("_raw", ""),
        )

    # ----------------------------------------------------------------------- #
    #  Private helpers                                                           #
    # ----------------------------------------------------------------------- #

    def _call_llm(self, question: str, memory_context: str, previous_intent: Optional[str] = None) -> Dict[str, Any]:
        """Gọi LLM và parse JSON kết quả. Trả về dict với keys: intent, entities, confidence.
        
        [NEW] Nếu previous_intent tồn tại, thêm hint vào prompt để LLM biết context.
        """
        # Build danh sách intent cho prompt
        intent_list_text = "\n".join(
            f"- {name}: {cfg.get('description', '')}"
            for name, cfg in self.intent_config.items()
        )
        context_text = memory_context.strip() if memory_context else "(Không có lịch sử)"
        
        # [NEW] Thêm hint về previous_intent nếu tồn tại
        previous_intent_hint = ""
        if previous_intent:
            previous_intent_hint = f"\n⚠️ LƯU Ý: Trước đó bot hỏi về '{previous_intent}' và cần bổ sung thông tin.\nNếu câu hỏi hiện tại là trả lời để làm rõ, hãy giữ intent='{previous_intent}'."

        prompt = _INTENT_EXTRACTION_PROMPT.format(
            intent_list=intent_list_text,
            memory_context=context_text,
            question=question + previous_intent_hint,
        )

        raw = ""
        try:
            raw = self._llm(prompt)
            # Ensure raw is properly decoded UTF-8
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            
            # Extract JSON using greedy matching - find outermost braces
            # Try multiple strategies
            json_str = None
            
            # Strategy 1: Find first { and last } (greedy)
            first_brace = raw.find("{")
            last_brace = raw.rfind("}")
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                potential_json = raw[first_brace:last_brace+1]
                try:
                    data = json.loads(potential_json)
                    data["_raw"] = raw
                    # Đảm bảo entities luôn là dict
                    if "entities" not in data or not isinstance(data["entities"], dict):
                        data["entities"] = {}
                    return data
                except json.JSONDecodeError:
                    pass  # Try next strategy
            
            # Strategy 2: Use regex with cleanup
            match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw, re.DOTALL)
            if match:
                json_str = match.group()
                # Clean up potential UTF-8 encoding issues
                json_str = json_str.encode("utf-8", errors="replace").decode("utf-8")
                data = json.loads(json_str)
                data["_raw"] = raw
                if "entities" not in data or not isinstance(data["entities"], dict):
                    data["entities"] = {}
                return data
        except json.JSONDecodeError as e:
            logger.warning(
                f"[IntentClassifier] JSON decode error: {e}. "
                f"Raw (first 500 chars): {repr(raw[:500])}"
            )
        except Exception as e:
            logger.warning(
                f"[IntentClassifier] LLM parse error: {type(e).__name__}: {e}. "
                f"Raw (first 500 chars): {repr(raw[:500])}"
            )

        # Fallback an toàn
        return {
            "intent": "GENERAL_REGULATION",
            "entities": {},
            "confidence": 0.5,
            "_raw": raw,
        }

    def _check_required_fields(
        self,
        intent_def: Dict[str, Any],
        entities: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Kiểm tra xem entity đã có đủ required_fields hay chưa.
        Returns: (needs_clarification, list_of_missing_fields)
        """
        if not intent_def.get("requires_entities", False):
            return False, []

        required = intent_def.get("required_fields", [])
        missing = [
            field for field in required
            if not entities.get(field)  # None, "", hoặc không có key
        ]
        return bool(missing), missing

    def _build_clarification(
        self,
        intent_def: Dict[str, Any],
        missing_fields: List[str],
    ) -> str:
        """
        Sinh câu hỏi làm rõ từ clarification_template trong YAML.
        Nếu không có template → sinh tự động từ missing_fields.
        """
        template = intent_def.get("clarification_template", "").strip()
        if template:
            return template

        # Auto-generate nếu không có template
        field_labels = {
            "nganh_hoc": "ngành học (ví dụ: CNTT, Cơ điện tử...)",
            "khoa_hoc": "khóa học (ví dụ: K65, K68, K70...)",
            "gpa": "điểm GPA của học kỳ gần nhất",
        }
        missing_texts = [
            field_labels.get(f, f) for f in missing_fields
        ]
        items = "\n".join(f"- {t}" for t in missing_texts)
        return f"Để trả lời chính xác, bạn vui lòng cho biết thêm:\n{items}"
