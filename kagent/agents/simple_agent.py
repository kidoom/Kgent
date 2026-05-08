"""SimpleAgent: basic conversational agent with optional prompt-based tool calling"""

import json
import re
from typing import Iterator, Optional

from ..core.agent import Agent
from ..core.config import Config
from ..core.llm import AgentLLM, LLMChunk
from ..core.message import Message
from ..tools.base import ToolResult
from ..tools.registry import ToolRegistry


# Parameter wrapping convention per tool name
_PARAM_WRAPPERS: dict[str, str] = {
    "calculator": "expression",
    "search": "query",
}


class SimpleAgent(Agent):
    """Basic conversational agent with optional tool calling via prompt constraints.

    Tool call format: [TOOL_CALL:name:params]
    params is a string, wrapped per tool convention:
      - calculator → {"expression": params}
      - search / default → {"query": params}
    """

    def __init__(
        self,
        name: str,
        llm: AgentLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        super().__init__(name=name, llm=llm, system_prompt=system_prompt, config=config)
        self.tool_registry = tool_registry

    # ── Public API ──────────────────────────────────────────────

    def run(self, input_text: str, max_steps: Optional[int] = None, **kwargs) -> str:
        """Run the agent on input_text and return the final response.

        Args:
            input_text: User input text.
            max_steps: Maximum LLM call steps. Defaults to config.max_steps.

        Returns:
            Final assistant response text.
        """
        max_steps = max_steps if max_steps is not None else self.config.max_steps

        self.add_message(Message(content=input_text, role="user"))
        messages = self._build_messages(input_text)

        if self.tool_registry:
            return self._run_with_tools(messages, max_steps)

        response = self.llm.invoke(messages)
        answer = response.content or ""
        self.add_message(Message(content=answer, role="assistant"))
        return answer

    def add_tool(self, tool) -> None:
        """Register a tool with the agent's tool registry.

        Creates a ToolRegistry if none exists.
        """
        if self.tool_registry is None:
            self.tool_registry = ToolRegistry()
        self.tool_registry.register_tool(tool)

    def remove_tool(self, name: str) -> bool:
        """Unregister a tool from the agent's tool registry."""
        if self.tool_registry is None:
            return False
        return self.tool_registry.unregister(name)

    def stream_run(self, input_text: str, **kwargs) -> Iterator[LLMChunk]:
        """Stream the agent response (no tool calling support in stream mode)."""
        self.add_message(Message(content=input_text, role="user"))
        messages = self._build_messages(input_text)
        full_content = []
        for chunk in self.llm.stream(messages):
            if chunk.delta:
                full_content.append(chunk.delta)
            yield chunk
        answer = "".join(full_content)
        if answer:
            self.add_message(Message(content=answer, role="assistant"))

    # ── Internal ────────────────────────────────────────────────

    def _run_with_tools(self, messages: list[dict], max_steps: int) -> str:
        """Loop: LLM call → parse tool calls → execute → inject observation → repeat."""
        best_answer = ""

        for _ in range(max_steps):
            response = self.llm.invoke(messages)
            content = response.content or ""

            tool_calls = self._parse_tool_calls(content)

            if not tool_calls:
                # No tool calls — this is the final answer
                best_answer = content
                break

            # Execute each tool call and collect observations
            observations = []
            for call in tool_calls:
                tool_name = call["name"]
                params_str = call["params"]
                result = self._execute_tool_call(tool_name, params_str)
                observations.append(
                    f"Observation[{tool_name}]: {result.content}"
                )

            # Inject the LLM output + observations into messages for next round
            messages.append({"role": "assistant", "content": content})
            obs_text = "\n".join(observations)
            messages.append({"role": "user", "content": obs_text})
            best_answer = content

        self.add_message(Message(content=best_answer, role="assistant"))
        return best_answer

    def _build_messages(self, input_text: str) -> list[dict]:
        """Build the message list for LLM invocation."""
        messages = []

        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        for msg in self.get_history():
            messages.append(msg.to_dict())

        # Inject tool description if registry is available
        if self.tool_registry:
            tools_desc = self.tool_registry.get_tools_description()
            tool_instruction = (
                f"\n\n可用工具:\n{tools_desc}\n\n"
                "如需调用工具，请使用格式: [TOOL_CALL:工具名:参数]\n"
                "例如: [TOOL_CALL:calculator:2+3*4] 或 [TOOL_CALL:search:Python教程]\n"
                "如不需要工具，直接回答即可。"
            )
            if messages and messages[-1]["role"] == "user":
                messages[-1]["content"] += tool_instruction
            else:
                messages.append({"role": "user", "content": tool_instruction})

        return messages

    def _parse_tool_calls(self, text: str) -> list[dict]:
        """Parse [TOOL_CALL:name:params] patterns from LLM output.

        Returns:
            List of {"name": str, "params": str}. Empty list if none found.
        """
        pattern = r"\[TOOL_CALL:([^:]+):([^\]]+)\]"
        matches = re.findall(pattern, text)
        return [{"name": m[0].strip(), "params": m[1].strip()} for m in matches]

    def _execute_tool_call(self, tool_name: str, parameters_str: str) -> ToolResult:
        """Execute a single tool call via ToolRegistry.

        Wraps parameters_str into a dict per tool convention.
        """
        param_key = _PARAM_WRAPPERS.get(tool_name, "query")
        arguments = {param_key: parameters_str}

        return self.tool_registry.execute_tool(tool_name, arguments)
