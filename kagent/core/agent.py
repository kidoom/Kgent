"""Agent abstract base class"""

import uuid
from abc import ABC, abstractmethod
from typing import Optional

from .config import Config
from .llm import AgentLLM
from .message import Message


class Agent(ABC):
    """Abstract base class for all Agents"""

    def __init__(
        self,
        name: str,
        llm: AgentLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        custom_prompt: Optional[str] = None,
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self.custom_prompt = custom_prompt
        self.run_id: str = ""
        self._history: list[Message] = []

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """Execute the agent with given input and return response text."""
        ...

    def _new_run_id(self) -> str:
        """Generate a new run_id. Call at the start of each run()."""
        self.run_id = uuid.uuid4().hex[:8]
        return self.run_id

    def _format_prompt(self, template: str, **extra_vars: str) -> str:
        """Replace template variables in a prompt string.

        Built-in variables: {tools}, {history}, {input}, {max_steps}
        Subclasses can pass additional variables via extra_vars.
        """
        tools_desc = ""
        if hasattr(self, "tool_registry") and self.tool_registry:
            tools_desc = self.tool_registry.get_tools_description()

        history_lines = []
        for msg in self.get_history():
            role = msg.role.capitalize()
            history_lines.append(f"{role}: {msg.content}")
        history_str = "\n".join(history_lines)

        variables = {
            "tools": tools_desc,
            "history": history_str,
            "max_steps": str(self.config.max_steps),
            **extra_vars,
        }
        return template.format(**variables)

    def add_message(self, message: Message) -> None:
        """Add a message to conversation history, trimming if over limit."""
        self._history.append(message)
        max_len = self.config.max_history_length
        if len(self._history) > max_len:
            self._history = self._history[-max_len:]

    def clear_history(self) -> None:
        """Clear all conversation history."""
        self._history.clear()

    def get_history(self) -> list[Message]:
        """Return a copy of conversation history."""
        return list(self._history)
