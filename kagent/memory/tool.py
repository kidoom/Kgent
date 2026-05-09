"""MemoryTool — wraps MemoryManager as a Tool for Agent use."""

from ..tools.base import Tool, ToolResult, ToolParameter
from .base import MemoryItem
from .manager import MemoryManager


class MemoryTool(Tool):
    """Tool for storing and recalling memories via MemoryManager.

    Actions:
      - remember: Store content in memory
      - recall: Search for relevant memories

    Usage in Agent prompt:
      [TOOL_CALL:memory:action=recall,query=用户的名字]
      [TOOL_CALL:memory:action=remember,content=用户叫张三]
    """

    def __init__(self, manager: MemoryManager):
        super().__init__(
            name="memory",
            description="记忆系统 — 存储和检索对话记忆",
        )
        self._manager = manager

    def run(self, parameters: dict) -> ToolResult:
        action = parameters.get("action", "").strip().lower()

        if action == "remember":
            return self._do_remember(parameters)
        elif action == "recall":
            return self._do_recall(parameters)
        else:
            return ToolResult(
                content=f"[ERROR] 未知的记忆操作: '{action}'，支持: remember, recall",
                success=False,
                error="invalid_action",
            )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="操作类型: remember (存储) 或 recall (检索)",
                required=True,
            ),
            ToolParameter(
                name="content",
                type="string",
                description="要存储的内容 (action=remember 时必填)",
                required=False,
            ),
            ToolParameter(
                name="query",
                type="string",
                description="检索关键词 (action=recall 时必填)",
                required=False,
            ),
        ]

    def _do_remember(self, params: dict) -> ToolResult:
        content = params.get("content", "").strip()
        if not content:
            return ToolResult(
                content="[ERROR] remember 操作需要 content 参数",
                success=False,
                error="missing_content",
            )
        item = MemoryItem(content=content)
        self._manager.store(item)
        return ToolResult(
            content=f"已记住: {content}",
            success=True,
            metadata={"action": "remember"},
        )

    def _do_recall(self, params: dict) -> ToolResult:
        query = params.get("query", "").strip()
        if not query:
            return ToolResult(
                content="[ERROR] recall 操作需要 query 参数",
                success=False,
                error="missing_query",
            )
        results = self._manager.search(query, top_k=5)
        if not results:
            return ToolResult(
                content=f"未找到与 '{query}' 相关的记忆",
                success=True,
                metadata={"action": "recall", "count": 0},
            )
        lines = []
        for i, item in enumerate(results, 1):
            lines.append(f"{i}. {item.content}")
        return ToolResult(
            content="\n".join(lines),
            success=True,
            metadata={"action": "recall", "count": len(results)},
        )
