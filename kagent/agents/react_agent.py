"""ReActAgent: Thought → Action → Observation loop"""

import re
from typing import Optional

from ..core.agent import Agent
from ..core.config import Config
from ..core.llm import AgentLLM
from ..core.message import Message
from ..tools.base import ToolResult
from ..tools.registry import ToolRegistry


# Parameter wrapping convention: tool name → parameter key
_PARAM_WRAPPERS: dict[str, str] = {
    "calculator": "expression",
    "search": "query",
}

_DEFAULT_REACT_PROMPT = """You are a helpful assistant that follows the Thought/Action/Observation pattern.

Available tools:
{tools}

When you need to use a tool, respond in this exact format:
Thought: <your reasoning>
Action: <ToolName>[<parameters>]

When you have the final answer, respond:
Thought: <your reasoning>
Action: Finish[<your final answer>]

Examples:
Thought: I need to search for the weather.
Action: Search[北京天气]

Thought: I need to calculate 2+3.
Action: Calculator[2+3]

Thought: I now have enough information to answer.
Action: Finish[北京今天晴，25°C]

{history}

User input: {input}
"""


class ReActAgent(Agent):
    """Agent that follows the Thought → Action → Observation reasoning loop.

    Action format: Action: ToolName[parameters]
      - Calculator → {"expression": params}
      - Search / default → {"query": params}
      - Finish[answer] → terminates loop, returns answer
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
        super().__init__(name=name, llm=llm, system_prompt=system_prompt, config=config, custom_prompt=custom_prompt)
        self.tool_registry = tool_registry

    # ── Public API ──────────────────────────────────────────────

    def run(self, input_text: str, max_steps: Optional[int] = None, **kwargs) -> str:
        """Run the ReAct loop on input_text.

        Args:
            input_text: User input text.
            max_steps: Maximum reasoning steps. Defaults to config.max_steps.

        Returns:
            Final answer string.
        """
        max_steps = max_steps if max_steps is not None else self.config.max_steps
        self._new_run_id()

        self.add_message(Message(content=input_text, role="user"))

        best_answer = ""

        for step in range(max_steps):
            prompt = self._format_prompt(input_text)
            messages = [{"role": "user", "content": prompt}]

            response = self.llm.invoke(messages)
            content = response.content or ""

            thought, action = self._parse_output(content)

            # No action found — inject error observation and continue
            if action is None:
                self.add_message(Message(content=content, role="assistant"))
                self.add_message(
                    Message(
                        content="Observation: 格式错误，请严格遵循 Thought/Action 格式",
                        role="user",
                    )
                )
                best_answer = content
                continue

            # Parse the action
            tool_name, tool_input = self._parse_action(action)

            # Check for Finish action
            if tool_name.lower() == "finish":
                best_answer = tool_input
                break

            # Execute tool
            if self.tool_registry:
                result = self._execute_tool(tool_name, tool_input)
                observation = result.content
            else:
                observation = f"[ERROR] 工具 '{tool_name}' 不可用（未配置 ToolRegistry）"

            # Inject into history for next iteration
            self.add_message(Message(content=content, role="assistant"))
            self.add_message(
                Message(content=f"Observation: {observation}", role="user")
            )
            best_answer = content

        self.add_message(Message(content=best_answer, role="assistant"))
        return best_answer

    # ── Internal ────────────────────────────────────────────────

    def _format_prompt(self, input_text: str) -> str:
        """Build the ReAct prompt with tools, history, and input injected."""
        tools_desc = "(无可用工具)"
        if self.tool_registry:
            tools_desc = self.tool_registry.get_tools_description()

        # Build history string from messages
        history_lines = []
        for msg in self.get_history():
            role = msg.role.capitalize()
            history_lines.append(f"{role}: {msg.content}")
        history_str = "\n".join(history_lines) if history_lines else ""

        template = self.system_prompt or _DEFAULT_REACT_PROMPT
        return template.format(
            tools=tools_desc,
            history=history_str,
            input=input_text,
        )

    def _parse_output(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """Parse Thought and Action from LLM output.

        Returns:
            (thought, action) tuple. Either may be None if not found.
        """
        thought = None
        action = None

        thought_match = re.search(r"Thought:\s*(.+?)(?=\nAction:|\Z)", text, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()

        action_match = re.search(r"Action:\s*(.+?)(?=\n|$)", text, re.DOTALL)
        if action_match:
            action = action_match.group(1).strip()

        return thought, action

    def _parse_action(self, action_text: str) -> tuple[str, str]:
        """Parse 'ToolName[params]' into (tool_name, tool_input).

        Handles Action: Finish[answer] by returning ("Finish", "answer").
        """
        match = re.match(r"(\w+)\[(.+)\]", action_text, re.DOTALL)
        if match:
            return match.group(1).strip(), match.group(2).strip()

        # Fallback: treat entire text as tool name with empty params
        return action_text.strip(), ""

    def _execute_tool(self, tool_name: str, tool_input: str) -> ToolResult:
        """Execute a tool via ToolRegistry with parameter wrapping."""
        param_key = _PARAM_WRAPPERS.get(tool_name.lower(), "query")
        arguments = {param_key: tool_input}
        return self.tool_registry.execute_tool(tool_name.lower(), arguments)
