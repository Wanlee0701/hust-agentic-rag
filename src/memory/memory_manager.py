"""
memory_manager.py — Quản lý bộ nhớ hội thoại theo phiên (session)
Chiến lược: Sliding Window — giữ K cặp Q&A gần nhất.
Storage: Python in-memory dict (local-first, không cần external DB).

Đặc điểm nổi bật:
- Lưu kèm entities đã bóc tách được ở mỗi turn.
- get_entities_from_memory() gộp entity từ toàn bộ window → dùng để
  bổ sung cho câu hỏi hiện tại mà không cần hỏi lại người dùng.
- reset() xóa cứng session khi người dùng bấm "Phiên chat mới".
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Dataclass                                                                    #
# --------------------------------------------------------------------------- #

@dataclass
class ConversationTurn:
    """Một cặp Q&A trong lịch sử hội thoại."""
    question: str
    answer: str
    entities: Dict[str, Any] = field(default_factory=dict)  # entity bóc tách được
    intent_name: str = ""  # [NEW] Intent được classify
    needs_clarification: bool = False  # [NEW] Có cần hỏi lại không?

    def to_text(self, max_chars: int = 300) -> str:
        """Chuyển thành plain text để inject vào prompt."""
        q = self.question[:max_chars]
        # Rút gọn answer để tránh token bloat
        a = self.answer[:max_chars]
        return f"Người dùng: {q}\nBot: {a}"


# --------------------------------------------------------------------------- #
#  ConversationMemory                                                           #
# --------------------------------------------------------------------------- #

class ConversationMemory:
    """
    Sliding Window Memory Manager.

    Mỗi session được lưu dưới dạng list các ConversationTurn.
    Chỉ giữ `window_size` turn gần nhất.
    """

    def __init__(self, window_size: int = 5, max_context_chars: int = 1500):
        """
        Args:
            window_size: Số cặp Q&A tối đa giữ lại (K).
            max_context_chars: Tổng ký tự tối đa khi inject context vào prompt.
        """
        self.window_size = window_size
        self.max_context_chars = max_context_chars
        # Storage: {session_id: List[ConversationTurn]}
        self._store: Dict[str, List[ConversationTurn]] = {}

    # ----------------------------------------------------------------------- #
    #  Write                                                                    #
    # ----------------------------------------------------------------------- #

    def add_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        entities: Optional[Dict[str, Any]] = None,
        intent_name: str = "",
        needs_clarification: bool = False,
    ) -> None:
        """
        Thêm một cặp Q&A vào memory của session.
        Tự động cắt bớt nếu vượt quá window_size.
        
        [NEW] Lưu kèm intent_name và needs_clarification flag.
        """
        if session_id not in self._store:
            self._store[session_id] = []

        turn = ConversationTurn(
            question=question,
            answer=answer,
            entities=entities or {},
            intent_name=intent_name,
            needs_clarification=needs_clarification,
        )
        self._store[session_id].append(turn)

        # Chỉ giữ K turn gần nhất
        if len(self._store[session_id]) > self.window_size:
            self._store[session_id] = self._store[session_id][-self.window_size:]

        logger.debug(
            f"[Memory] Session '{session_id}': {len(self._store[session_id])} turns in window."
        )

    def reset(self, session_id: str) -> None:
        """Xóa cứng toàn bộ memory của session (khi user bấm 'Phiên chat mới')."""
        if session_id in self._store:
            del self._store[session_id]
            logger.info(f"[Memory] Session '{session_id}' đã được reset.")

    # ----------------------------------------------------------------------- #
    #  Read                                                                     #
    # ----------------------------------------------------------------------- #

    def get_context(self, session_id: str) -> str:
        """
        Trả về ngữ cảnh hội thoại dưới dạng plain text để inject vào prompt.
        Giới hạn tổng ký tự bằng max_context_chars.
        """
        turns = self._store.get(session_id, [])
        if not turns:
            return ""

        parts = []
        total_chars = 0
        # Lấy từ gần nhất đến xa nhất, đảm bảo không vượt budget
        chars_per_turn = max(100, self.max_context_chars // len(turns))

        for turn in turns:
            text = turn.to_text(max_chars=chars_per_turn)
            if total_chars + len(text) > self.max_context_chars:
                break
            parts.append(text)
            total_chars += len(text)

        context = "\n---\n".join(parts)
        return context

    def get_entities_from_memory(self, session_id: str) -> Dict[str, Any]:
        """
        Gộp tất cả entity từ các turn trong window thành một dict.
        Turn gần nhất có độ ưu tiên cao hơn (ghi đè entity cũ hơn).

        Ví dụ:
          Turn 1: {"nganh_hoc": "CNTT"}
          Turn 2: {"khoa_hoc": "K65"}
          → {"nganh_hoc": "CNTT", "khoa_hoc": "K65"}
        """
        turns = self._store.get(session_id, [])
        merged: Dict[str, Any] = {}
        for turn in turns:  # Thứ tự cũ → mới (mới ghi đè cũ)
            for key, value in turn.entities.items():
                if value:  # Bỏ qua None / empty string
                    merged[key] = value
        return merged

    def has_session(self, session_id: str) -> bool:
        """Kiểm tra session có tồn tại không."""
        return session_id in self._store and len(self._store[session_id]) > 0

    def get_last_turn(self, session_id: str) -> Optional[ConversationTurn]:
        """Lấy turn cuối cùng của session (nếu có)."""
        turns = self._store.get(session_id, [])
        return turns[-1] if turns else None

    def get_last_clarification_intent(self, session_id: str) -> Optional[str]:
        """
        [NEW] Lấy intent từ turn cuối cùng nếu turn đó cần clarification.
        Dùng để reuse intent khi user respond với clarification.
        
        Returns:
            intent_name nếu turn cuối cần clarification, else None.
        """
        last_turn = self.get_last_turn(session_id)
        if last_turn and last_turn.needs_clarification:
            return last_turn.intent_name
        return None

    def get_turn_count(self, session_id: str) -> int:
        """Số turn hiện tại trong session."""
        return len(self._store.get(session_id, []))


# --------------------------------------------------------------------------- #
#  Singleton factory — dùng chung một instance toàn app                        #
# --------------------------------------------------------------------------- #

_global_memory: Optional[ConversationMemory] = None


def get_memory(window_size: int = 5, max_context_chars: int = 1500) -> ConversationMemory:
    """
    Trả về instance ConversationMemory dùng chung toàn bộ app.
    Gọi lần đầu sẽ khởi tạo, các lần sau trả về cùng instance.
    """
    global _global_memory
    if _global_memory is None:
        _global_memory = ConversationMemory(
            window_size=window_size,
            max_context_chars=max_context_chars,
        )
        logger.info(
            f"[Memory] Initialized ConversationMemory "
            f"(window={window_size}, max_chars={max_context_chars})"
        )
    return _global_memory
