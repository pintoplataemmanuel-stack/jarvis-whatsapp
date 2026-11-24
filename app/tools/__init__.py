"""Registro de herramientas del agente."""

from app.tools import builtin  # noqa: F401  (registra las herramientas al importar)
from app.tools.registry import TOOL_REGISTRY, Tool, definitions, get, register

__all__ = ["Tool", "TOOL_REGISTRY", "definitions", "get", "register"]
