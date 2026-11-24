from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict], str]
    requires_confirmation: bool = False
    args_model: type[BaseModel] | None = None

    def ejecutar(self, args: dict) -> str:
        if self.args_model is not None:
            args = self.args_model.model_validate(args).model_dump()
        return self.handler(args)


TOOL_REGISTRY: dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    TOOL_REGISTRY[tool.name] = tool
    return tool


def get(name: str) -> Tool | None:
    return TOOL_REGISTRY.get(name)


def definitions() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in TOOL_REGISTRY.values()
    ]
