"""Agent abstract base class"""

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
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self._history: list[Message] = []

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """Execute the agent with given input and return response text."""
        ...

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
