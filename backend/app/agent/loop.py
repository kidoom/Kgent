"""The minimal model-tool-model loop controller."""

from pathlib import Path

from app.agent.messages import AgentResult, AgentStep, Message, ToolExecutionResult, ToolResultBlock, ToolUseBlock
from app.agent.model_client import ModelClient
from app.agent.prompts import SYSTEM_PROMPT
from app.tools.base import Tool
from app.tools.registry import build_tool_schemas, find_tool_by_name


async def run_agent(
    user_input: str,
    model_client: ModelClient,
    tools: list[Tool],
    max_steps: int = 8,
) -> AgentResult:
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=user_input),
    ]
    steps: list[AgentStep] = []
    tool_schemas = build_tool_schemas(tools)

    for _ in range(max_steps):
        response = await model_client.call_model(messages=messages, tools=tool_schemas)
        messages.append(response.assistant_message)

        if not response.tool_uses:
            return AgentResult(answer=response.text, steps=steps)

        for tool_use in response.tool_uses:
            steps.append(AgentStep(type="tool_use", name=tool_use.name, input=tool_use.input))
            result = await execute_tool_use(tool_use, tools)
            steps.append(
                AgentStep(
                    type="tool_result",
                    name=tool_use.name,
                    content=result.content,
                    is_error=result.is_error,
                )
            )
            messages.append(
                Message(
                    role="user",
                    content=[
                        ToolResultBlock(
                            tool_use_id=tool_use.id,
                            content=result.content,
                            is_error=result.is_error,
                        )
                    ],
                )
            )

    raise RuntimeError("Agent stopped: max steps reached")


async def execute_tool_use(tool_use: ToolUseBlock, tools: list[Tool]) -> ToolExecutionResult:
    tool = find_tool_by_name(tools, tool_use.name)
    if tool is None:
        return ToolExecutionResult(content=f"Unknown tool: {tool_use.name}", is_error=True)

    try:
        content = await tool.call(tool_use.input)
        return ToolExecutionResult(content=content)
    except Exception as exc:  # noqa: BLE001 - errors are returned to the model deliberately.
        return ToolExecutionResult(content=f"Error: {exc}", is_error=True)


def infer_project_root() -> Path:
    return Path.cwd().resolve()
