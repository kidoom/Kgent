"""FunctionCallAgent: native OpenAI function-calling agent"""

import json
import time
from typing import Optional

from ..core.agent import Agent
from ..core.config import Config
from ..core.exceptions import LLMError
from ..core.llm import AgentLLM, LLMResponse
from ..core.message import Message
from ..tools.registry import ToolRegistry


_DEFAULT_FC_PROMPT = """You are a helpful assistant with access to tools.
Use tools when needed to answer the user's question. If you can answer directly, do so without using tools.
"""


class FunctionCallAgent(Agent):
    """Agent that uses OpenAI-native function/tool calling protocol.

    Unlike SimpleAgent (prompt-constrained) or ReActAgent (Thought/Action),
    this agent uses the model's native tool_calls response format.
    The LLM decides when and which tools to call.
    """

    def __init__(
        self,
        name: str,
        llm: AgentLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional[ToolRegistry] = None,
        custom_prompt: Optional[str] = None,
    ):
        super().__init__(
            name=name, llm=llm, system_prompt=system_prompt,
            config=config, custom_prompt=custom_prompt,
        )
        self.tool_registry = tool_registry

    def run(
        self,
        input_text: str,
        max_steps: Optional[int] = None,
        tool_choice: str | dict = "auto",
        **kwargs,
    ) -> str:
        """Run the function-calling loop on input_text.

        Args:
            input_text: User input.
            max_steps: Maximum tool-calling rounds. Defaults to config.max_steps.
            tool_choice: OpenAI tool_choice parameter ("auto", "none", "required", etc.).

        Returns:
            Final text response from the LLM.
        """
        max_steps = max_steps if max_steps is not None else self.config.max_steps
        self._new_run_id()
        self.add_message(Message(content=input_text, role="user"))

        # Build tool schemas for OpenAI
        tools_schema = self._build_tool_schemas() if self.tool_registry else None

        # Build messages
        messages = self._build_messages(input_text)

        for _ in range(max_steps):
            response = self._invoke_with_tools(messages, tools_schema, tool_choice)
            content = self._extract_message_content(response)
            tool_calls = response.tool_calls or []

            # No tool calls — LLM answered directly
            if not tool_calls:
                self.add_message(Message(content=content, role="assistant"))
                return content

            # Add assistant message with tool_calls
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls,
            })

            # Execute each tool call and add results
            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                arguments = self._parse_function_call_arguments(tc["function"]["arguments"])

                if self.tool_registry and self.tool_registry.is_registered(tool_name):
                    result = self.tool_registry.execute_tool(tool_name, arguments)
                    tool_content = result.content
                else:
                    tool_content = f"[ERROR] Tool '{tool_name}' not found"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": tool_content,
                })

        # Max steps reached — return last content
        self.add_message(Message(content=content, role="assistant"))
        return content

    def _build_tool_schemas(self) -> list[dict]:
        """Build OpenAI-format tool schemas from ToolRegistry."""
        schemas = []
        for name, info in self.tool_registry.list_tools().items():
            if not info["enabled"]:
                continue
            # Try to get schema from Tool object
            if name in self.tool_registry._tools:
                schemas.append(self.tool_registry._tools[name].to_openai_schema())
            else:
                # Bare function — build minimal schema
                func_info = self.tool_registry._functions.get(name, {})
                params = func_info.get("parameters", [])
                properties = {}
                required = []
                for p in params:
                    properties[p.name] = {
                        "type": p.type,
                        "description": p.description,
                    }
                    if p.required:
                        required.append(p.name)
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": info.get("description", ""),
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required,
                        },
                    },
                })
        return schemas

    def _invoke_with_tools(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
        tool_choice: str | dict,
    ) -> LLMResponse:
        """Call LLM with tool schemas. Retries on timeout/429 with exponential backoff (L3)."""
        max_retries = 3
        backoff = 1.0

        for attempt in range(max_retries + 1):
            try:
                return self.llm.invoke(
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice if tools else None,
                )
            except LLMError as e:
                # Only retry on the last attempt; otherwise backoff and retry
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise

    def _extract_message_content(self, response: LLMResponse) -> str:
        """Extract text content from LLM response."""
        return response.content or ""

    def _parse_function_call_arguments(self, arguments: str) -> dict:
        """Parse JSON arguments from a function call."""
        try:
            return json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return {}

    def _build_messages(self, input_text: str) -> list[dict]:
        """Build initial message list with system prompt."""
        messages = []
        system = self.system_prompt or _DEFAULT_FC_PROMPT
        messages.append({"role": "system", "content": system})
        # Add history
        for msg in self.get_history():
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})
        return messages
