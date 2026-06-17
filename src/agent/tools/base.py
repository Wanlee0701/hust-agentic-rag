"""
base.py — Interface chuẩn cho tất cả Agent tools.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ToolResult:
    """Kết quả trả về từ một tool execution."""
    success: bool
    data: Any = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Interface chuẩn cho tất cả agent tools."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult: ...

    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"
