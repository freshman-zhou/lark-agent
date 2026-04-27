from dataclasses import dataclass
from typing import Any


@dataclass
class SkillResult:
    success: bool
    data: dict[str, Any] | None = None
    message: str | None = None
    error: str | None = None


class BaseSkill:
    name: str = ""
    description: str = ""

    async def run(self, params: dict[str, Any], context: Any) -> SkillResult:
        raise NotImplementedError