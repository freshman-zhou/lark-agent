from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class BaseTool:
    name: str = ""
    description: str = ""

    async def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError
