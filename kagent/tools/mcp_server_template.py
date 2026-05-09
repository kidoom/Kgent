"""MCP Server template — example server for RAG project integration.

Run directly: python -m kagent.tools.mcp_server_template
Exposes two tools: search_docs + list_sources

This is a minimal MCP server using stdio transport and JSON-RPC 2.0.
"""

import json
import sys


# Simulated document store
_DOCUMENTS = [
    {"id": 1, "title": "Kagent 框架介绍", "content": "Kagent 是一个可插拔 AI Agent 框架"},
    {"id": 2, "title": "MCP 协议", "content": "Model Context Protocol 用于 Agent 与外部工具通信"},
    {"id": 3, "title": "ReAct 推理", "content": "Thought-Action-Observation 循环推理模式"},
]

TOOL_DEFINITIONS = [
    {
        "name": "search_docs",
        "description": "搜索文档库中的相关内容",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_sources",
        "description": "列出所有可用的文档来源",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def handle_request(request: dict) -> dict:
    """Handle a single JSON-RPC request."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    # Notifications have no id — no response needed
    if req_id is None:
        return {}

    if method == "initialize":
        return _response(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "kagent-mcp-template", "version": "0.1.0"},
        })

    if method == "tools/list":
        return _response(req_id, {"tools": TOOL_DEFINITIONS})

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = _handle_tool_call(tool_name, arguments)
        return _response(req_id, result)

    return _error_response(req_id, -32601, f"Method not found: {method}")


def _handle_tool_call(name: str, arguments: dict) -> dict:
    """Dispatch to the appropriate tool handler."""
    if name == "search_docs":
        query = arguments.get("query", "").lower()
        matches = [
            d for d in _DOCUMENTS
            if query in d["title"].lower() or query in d["content"].lower()
        ]
        if not matches:
            return {"content": [{"type": "text", "text": "未找到匹配文档"}], "isError": False}
        text = "\n".join(f"- {m['title']}: {m['content']}" for m in matches)
        return {"content": [{"type": "text", "text": text}], "isError": False}

    if name == "list_sources":
        sources = [f"- [{d['id']}] {d['title']}" for d in _DOCUMENTS]
        text = "可用文档来源:\n" + "\n".join(sources)
        return {"content": [{"type": "text", "text": text}], "isError": False}

    return {"content": [{"type": "text", "text": f"未知工具: {name}"}], "isError": True}


def _response(req_id: int, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error_response(req_id: int, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def main():
    """Run the MCP server on stdin/stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            err = _error_response(None, -32700, "Parse error")
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
