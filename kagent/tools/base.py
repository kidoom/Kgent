"""Tool abstraction: base class and data models"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Result from a tool execution"""

    content: str
    success: bool = True
    error: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class ToolParameter(BaseModel):
    """Parameter definition for a tool"""

    name: str
    type: str  # "string" | "number" | "boolean" | "array"
    description: str
    required: bool = True
    default: Any = None


class Tool(ABC):
    """Abstract base class for all tools"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, parameters: dict) -> ToolResult:
        """Execute the tool with given parameters."""
        ...

    @abstractmethod
    def get_parameters(self) -> list[ToolParameter]:
        """Return the list of parameters this tool accepts."""
        ...

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function definition format."""
        params = self.get_parameters()
        properties = {}
        required = []

        for p in params:
            properties[p.name] = {
                "type": p.type,
                "description": p.description,
            }
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
