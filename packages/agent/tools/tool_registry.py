from packages.agent.tools.base_tool import BaseTool, ToolResult
from packages.agent.tools.feishu_doc_search_tool import FeishuDocSearchTool
from packages.agent.tools.image_search_http_tool import ImageSearchHttpTool
from packages.agent.tools.web_search_http_tool import WebSearchHttpTool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self.register(WebSearchHttpTool())
        self.register(FeishuDocSearchTool())
        self.register(ImageSearchHttpTool())

    def register(self, tool: BaseTool) -> None:
        if not tool.name:
            raise ValueError("Tool name is required")
        self._tools[tool.name] = tool

    async def run(self, tool_name: str, **kwargs) -> ToolResult:
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"Tool not found: {tool_name}",
            )

        return await tool.run(**kwargs)
