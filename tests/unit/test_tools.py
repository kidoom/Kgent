"""Tests for Tool base class and ToolRegistry"""

import pytest

from kagent.tools.base import Tool, ToolResult, ToolParameter
from kagent.tools.registry import ToolRegistry


class MockTool(Tool):
    """A concrete tool for testing"""

    def __init__(self):
        super().__init__(
            name="mock_tool",
            description="A mock tool for testing",
        )

    def run(self, parameters: dict) -> ToolResult:
        return ToolResult(
            content=f"executed with {parameters}",
            success=True,
        )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="input",
                type="string",
                description="Input text",
                required=True,
            ),
            ToolParameter(
                name="count",
                type="number",
                description="Repeat count",
                required=False,
                default=1,
            ),
        ]


class FailingTool(Tool):
    """A tool that always fails"""

    def __init__(self):
        super().__init__(name="fail_tool", description="Always fails")

    def run(self, parameters: dict) -> ToolResult:
        raise ValueError("simulated failure")

    def get_parameters(self) -> list[ToolParameter]:
        return []


class TestToolResult:
    """Test ToolResult model"""

    def test_success_result(self):
        result = ToolResult(content="done", success=True)
        assert result.content == "done"
        assert result.success is True
        assert result.error is None

    def test_failure_result(self):
        result = ToolResult(
            content="failed",
            success=False,
            error="something went wrong",
        )
        assert result.success is False
        assert result.error == "something went wrong"

    def test_result_with_metadata(self):
        result = ToolResult(content="ok", metadata={"key": "value"})
        assert result.metadata["key"] == "value"


class TestToolParameter:
    """Test ToolParameter model"""

    def test_required_parameter(self):
        p = ToolParameter(name="query", type="string", description="Search query")
        assert p.name == "query"
        assert p.required is True

    def test_optional_parameter(self):
        p = ToolParameter(
            name="limit",
            type="number",
            description="Max results",
            required=False,
            default=10,
        )
        assert p.required is False
        assert p.default == 10


class TestToolIsAbstract:
    """Test Tool cannot be instantiated"""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError, match="abstract method"):
            Tool(name="test", description="desc")

    def test_subclass_must_implement_run(self):
        class IncompleteTool(Tool):
            def run(self, parameters):
                pass

        with pytest.raises(TypeError, match="abstract method"):
            IncompleteTool(name="test", description="desc")

    def test_concrete_subclass_works(self):
        tool = MockTool()
        assert isinstance(tool, Tool)
        assert tool.name == "mock_tool"


class TestToolOpenAISchema:
    """Test Tool.to_openai_schema()"""

    def test_generates_valid_schema(self):
        tool = MockTool()
        schema = tool.to_openai_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "mock_tool"
        assert "parameters" in schema["function"]
        assert "input" in schema["function"]["parameters"]["properties"]
        assert "input" in schema["function"]["parameters"]["required"]


class TestToolRegistry:
    """Test ToolRegistry"""

    def test_register_and_execute_tool(self):
        registry = ToolRegistry()
        registry.register_tool(MockTool())
        result = registry.execute_tool("mock_tool", {"input": "hello"})
        assert result.success is True
        assert "hello" in result.content

    def test_register_and_execute_function(self):
        registry = ToolRegistry()
        registry.register_function(
            "echo",
            "Echo input",
            lambda args: args.get("text", ""),
        )
        result = registry.execute_tool("echo", {"text": "hi"})
        assert result.success is True
        assert result.content == "hi"

    def test_execute_unknown_tool(self):
        registry = ToolRegistry()
        result = registry.execute_tool("nonexistent", {})
        assert result.success is False
        assert "未注册" in result.content

    def test_unregister_tool(self):
        registry = ToolRegistry()
        registry.register_tool(MockTool())
        assert registry.unregister("mock_tool") is True
        result = registry.execute_tool("mock_tool", {"input": "test"})
        assert result.success is False
        assert "未注册" in result.content

    def test_unregister_function(self):
        registry = ToolRegistry()
        registry.register_function("echo", "...", lambda args: args)
        assert registry.unregister("echo") is True
        result = registry.execute_tool("echo", {"text": "x"})
        assert result.success is False

    def test_unregister_nonexistent(self):
        registry = ToolRegistry()
        assert registry.unregister("nonexistent") is False

    def test_register_non_tool_raises(self):
        registry = ToolRegistry()
        with pytest.raises(TypeError, match="Expected Tool"):
            registry.register_tool("not a tool")

    def test_tool_error_returns_failure_not_exception(self):
        registry = ToolRegistry()
        registry.register_tool(FailingTool())
        result = registry.execute_tool("fail_tool", {})
        assert result.success is False
        assert "执行失败" in result.content

    def test_get_tools_description(self):
        registry = ToolRegistry()
        registry.register_tool(MockTool())
        registry.register_function("greet", "Greet user", lambda args: "hello")
        desc = registry.get_tools_description()
        assert "mock_tool" in desc
        assert "greet" in desc
        assert "echo" not in desc

    def test_get_tools_description_empty(self):
        registry = ToolRegistry()
        desc = registry.get_tools_description()
        assert "无可用工具" in desc
