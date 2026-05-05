from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExplicitIntentResult:
    intent: str
    confidence: float
    task_type: str = "UNKNOWN"
    normalized_command: str = ""
    title: str = ""
    deliverables: list[str] = field(default_factory=list)
    requires_clarification: bool = False
    clarifying_questions: list[str] = field(default_factory=list)
    reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExplicitIntentResult":
        return cls(
            intent=str(data.get("intent") or "UNKNOWN"),
            confidence=float(data.get("confidence") or 0),
            task_type=str(data.get("task_type") or "UNKNOWN"),
            normalized_command=str(data.get("normalized_command") or ""),
            title=str(data.get("title") or ""),
            deliverables=list(data.get("deliverables") or []),
            requires_clarification=bool(data.get("requires_clarification")),
            clarifying_questions=list(data.get("clarifying_questions") or []),
            reason=str(data.get("reason") or ""),
            raw=data,
        )
