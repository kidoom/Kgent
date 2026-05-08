"""Integration test: verify all top-level exports are importable (C8)"""


def test_all_exports():
    """All core symbols importable from top-level kagent package."""
    from kagent import (  # noqa: F401
        SimpleAgent,
        ReActAgent,
        AgentLLM,
        Config,
        Message,
        KagentError,
        LLMError,
        AgentError,
        ToolError,
        ConfigError,
    )


def test_submodule_imports():
    """Submodules importable directly."""
    from kagent.core import Agent, AgentLLM, Config, Message  # noqa: F401
    from kagent.agents import SimpleAgent, ReActAgent  # noqa: F401
    from kagent.tools import Tool, ToolParameter, ToolRegistry, ToolResult  # noqa: F401


def test_placeholder_packages():
    """v0.4 placeholder packages importable."""
    import kagent.memory  # noqa: F401
    import kagent.context  # noqa: F401
