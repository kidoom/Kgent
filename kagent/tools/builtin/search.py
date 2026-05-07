"""SearchTool: single-backend web search (SerpApi or Tavily)"""

import os

from ..base import Tool, ToolResult, ToolParameter


class SearchTool(Tool):
    """Web search using a single backend configured via environment."""

    def __init__(self):
        super().__init__(
            name="search",
            description="搜索互联网获取实时信息",
        )
        self._backend = os.getenv("SEARCH_BACKEND", "serpapi").lower()

    def run(self, parameters: dict) -> ToolResult:
        query = parameters.get("query", "").strip()
        if not query:
            return ToolResult(
                content="搜索关键词不能为空",
                success=False,
                error="empty_query",
            )

        api_key = self._get_api_key()
        if not api_key:
            return ToolResult(
                content=f"[ERROR] 搜索 API Key 未配置，请在 .env 中设置 {self._env_key()}",
                success=False,
                error="missing_api_key",
            )

        try:
            if self._backend == "tavily":
                return self._search_tavily(api_key, query)
            else:
                return self._search_serpapi(api_key, query)
        except Exception as e:
            return ToolResult(
                content=f"[ERROR] 搜索失败: {e}",
                success=False,
                error=str(e),
            )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词",
                required=True,
            ),
        ]

    def _env_key(self) -> str:
        return "TAVILY_API_KEY" if self._backend == "tavily" else "SERPAPI_API_KEY"

    def _get_api_key(self) -> str | None:
        key = os.getenv(self._env_key())
        return key if key else None

    def _search_serpapi(self, api_key: str, query: str) -> ToolResult:
        try:
            import urllib.parse
            import urllib.request
            import json

            params = urllib.parse.urlencode({
                "q": query,
                "api_key": api_key,
                "engine": "google",
            })
            url = f"https://serpapi.com/search?{params}"

            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())

            results = data.get("organic_results", [])[:5]
            if not results:
                return ToolResult(
                    content="未找到相关结果",
                    success=True,
                    metadata={"count": 0},
                )

            lines = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "N/A")
                snippet = r.get("snippet", "N/A")
                link = r.get("link", "")
                lines.append(f"{i}. {title}\n   {snippet}\n   {link}")

            return ToolResult(
                content="\n\n".join(lines),
                success=True,
                metadata={"count": len(results)},
            )
        except Exception as e:
            return ToolResult(
                content=f"[ERROR] SerpApi 搜索失败: {e}",
                success=False,
                error=str(e),
            )

    def _search_tavily(self, api_key: str, query: str) -> ToolResult:
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=api_key)
            response = client.search(query=query, max_results=5)

            results = response.get("results", [])
            if not results:
                return ToolResult(
                    content="未找到相关结果",
                    success=True,
                    metadata={"count": 0},
                )

            lines = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "N/A")
                content = r.get("content", "N/A")
                url = r.get("url", "")
                lines.append(f"{i}. {title}\n   {content}\n   {url}")

            return ToolResult(
                content="\n\n".join(lines),
                success=True,
                metadata={"count": len(results)},
            )
        except ImportError:
            return ToolResult(
                content="[ERROR] 需要安装 tavily-python: pip install tavily-python",
                success=False,
                error="tavily_not_installed",
            )
        except Exception as e:
            return ToolResult(
                content=f"[ERROR] Tavily 搜索失败: {e}",
                success=False,
                error=str(e),
            )
