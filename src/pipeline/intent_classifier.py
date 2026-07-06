"""
intent_classifier.py — Hybrid Intent Classification & Routing
Kết hợp: LLM (bóc tách ngữ nghĩa) + Schema (kiểm tra business logic).

Luồng:
  1. LLM đọc câu hỏi + memory context → trả về JSON {intent, entities}
  2. So sánh entities bóc tách được với requires_fields trong Schema
  3. Bổ sung entity từ memory nếu còn thiếu
  4. Nếu vẫn thiếu → needs_clarification = True + sinh câu hỏi làm rõ
  5. Nếu đủ → pass vào RAG

[v5 — Auto-Discovery]
  - Entity list (nganh_hoc, khoa_hoc...) không còn hardcode trong prompt.
  - Được inject động từ university_schema.yaml qua SchemaLoader.
  - Clarification prompts cũng lấy từ schema, không còn dict cứng trong code.
  - Hệ thống có thể tái sử dụng cho bất kỳ trường đại học nào.
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
Bạn là bộ phân loại câu hỏi của hệ thống chatbot tư vấn quy chế đào tạo đại học.

## Danh sách Intent hợp lệ:
{intent_list}

## Các loại thông tin (entity) cần bóc tách:
{entity_list}

## Lịch sử hội thoại gần đây (có thể trống):
{memory_context}

## Câu hỏi hiện tại:
"{question}"

## Nhiệm vụ:
1. Xác định intent phù hợp nhất từ danh sách trên.
2. Bóc tách các entity có trong câu hỏi HOẶC được nhắc tới trong lịch sử hội thoại.
   - Chỉ lấy entity từ danh sách entity ở trên.
   - Entity không có trong câu hỏi lẫn lịch sử → để null.
3. Trả về confidence (0.0-1.0) cho quyết định intent.

Trả về JSON duy nhất (KHÔNG giải thích thêm):
{{"intent": "INTENT_NAME", "entities": {{{entity_json_template}}}, "confidence": 0.0}}"""


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
        domain_entities: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            intent_config: Dict intent schema (từ university_schema.yaml hoặc config.yaml['intents']).
            llm_invoker: Hàm gọi LLM, nhận prompt str → trả về str.
            domain_entities: Dict entity schema từ university_schema.yaml['domain_entities'].
                             Nếu None → fallback về entity list mặc định (nganh_hoc, khoa_hoc, gpa).
        """
        self.intent_config = intent_config
        self._llm = llm_invoker
        self._intent_names = list(intent_config.keys())
        # [v5] Domain entities từ schema — nếu không có thì dùng default
        self._domain_entities: Dict[str, Any] = domain_entities or self._default_entities()
        logger.info(
            f"[IntentClassifier] Loaded {len(self._intent_names)} intents: "
            f"{self._intent_names}"
        )
        logger.info(
            f"[IntentClassifier] Domain entities: {list(self._domain_entities.keys())}"
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

        [v5] Entity list được inject động từ domain_entities schema.
        [v3] Nếu previous_intent tồn tại, thêm hint vào prompt để LLM biết context.
        """
        # Build danh sách intent cho prompt
        intent_list_text = "\n".join(
            f"- {name}: {cfg.get('description', '')}"
            for name, cfg in self.intent_config.items()
        )
        context_text = memory_context.strip() if memory_context else "(Không có lịch sử)"

        # [v5] Build entity list động từ domain_entities schema
        entity_lines = []
        for entity_name, entity_cfg in self._domain_entities.items():
            desc = entity_cfg.get('description', '')
            examples = entity_cfg.get('examples', [])
            ex_str = f" (ví dụ: {', '.join(str(e) for e in examples[:3])})" if examples else ""
            entity_lines.append(f"- {entity_name}: {desc}{ex_str}")
        entity_list_text = "\n".join(entity_lines) if entity_lines else "- (Không có entity đặc thù)"

        # Build JSON template cho entity output
        entity_json_template = ", ".join(
            f'"{name}": null' for name in self._domain_entities.keys()
        )

        # [v3] Thêm hint về previous_intent nếu tồn tại
        previous_intent_hint = ""
        if previous_intent:
            previous_intent_hint = (
                f"\n⚠️ LƯU Ý: Trước đó bot hỏi về '{previous_intent}' và cần bổ sung thông tin."
                f"\nNếu câu hỏi hiện tại là trả lời để làm rõ, hãy giữ intent='{previous_intent}'."
            )

        prompt = _INTENT_EXTRACTION_PROMPT.format(
            intent_list=intent_list_text,
            entity_list=entity_list_text,
            entity_json_template=entity_json_template,
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
        Sinh câu hỏi làm rõ:
          1. Dùng clarification_template từ intent schema nếu có.
          2. Nếu không → tổng hợp từ clarification_prompt của từng entity trong domain_entities.
          3. Fallback cuối: sinh tự động từ tên field.

        [v5] Ưu tiên dùng clarification_prompt từ domain_entities schema
             thay vì dict cứng trong code.
        """
        template = intent_def.get("clarification_template", "").strip()
        if template:
            return template

        # [v5] Lấy clarification_prompt từ domain_entities schema
        missing_texts = []
        for field_name in missing_fields:
            entity_cfg = self._domain_entities.get(field_name, {})
            clarif_prompt = entity_cfg.get("clarification_prompt", "").strip()
            if clarif_prompt:
                missing_texts.append(clarif_prompt)
            else:
                # Fallback: dùng description hoặc tên field
                desc = entity_cfg.get("description", field_name)
                examples = entity_cfg.get("examples", [])
                ex_str = f" (ví dụ: {', '.join(str(e) for e in examples[:3])})" if examples else ""
                missing_texts.append(f"{desc}{ex_str}")

        items = "\n".join(f"- {t}" for t in missing_texts)
        return f"Để trả lời chính xác, bạn vui lòng cho biết thêm:\n{items}"

    @staticmethod
    def _default_entities() -> Dict[str, Any]:
        """
        Trả về entity defaults khi không có university_schema.yaml.
        Dùng làm fallback để không breaking change với hệ thống hiện tại.
        """
        return {
            "nganh_hoc": {
                "description": "Ngành học của sinh viên",
                "examples": ["CNTT", "Cơ điện tử", "Toán - Tin"],
                "clarification_prompt": "Ngành học của bạn là gì? (ví dụ: CNTT, Cơ điện tử...)",
            },
            "khoa_hoc": {
                "description": "Khóa nhập học",
                "examples": ["K65", "K68", "K70"],
                "clarification_prompt": "Bạn thuộc khóa nào? (ví dụ: K65, K68, K70...)",
            },
            "gpa": {
                "description": "Điểm GPA tích lũy",
                "examples": ["3.2", "2.8", "3.5"],
                "clarification_prompt": "Điểm GPA tích lũy hiện tại của bạn là bao nhiêu?",
            },
        }
