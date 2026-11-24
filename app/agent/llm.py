import json
import logging
import time
from dataclasses import dataclass, field

import openai
from openai import OpenAI

from app.config import get_settings

log = logging.getLogger("jarvis.llm")


class LLMError(Exception):
    """Error amigable del proveedor de modelo. Nunca contiene claves."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    raw: dict = field(default_factory=dict)


@dataclass
class ChatResult:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_tool_calls: list[dict] = field(default_factory=list)


class LLMProvider:
    """Único punto de contacto con un proveedor compatible con la API de OpenAI."""

    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.llm_model
        self.client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
        self.max_reintentos = 3

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResult:
        ultimo_error: Exception | None = None

        for intento in range(1, self.max_reintentos + 1):
            try:
                kwargs: dict = {"model": self.model, "messages": messages}
                if tools:
                    kwargs["tools"] = tools
                respuesta = self.client.chat.completions.create(**kwargs)
                mensaje = respuesta.choices[0].message

                herramientas: list[ToolCall] = []
                crudas: list[dict] = []
                for llamada in mensaje.tool_calls or []:
                    cruda = llamada.model_dump()
                    crudas.append(cruda)
                    try:
                        argumentos = json.loads(llamada.function.arguments or "{}")
                    except json.JSONDecodeError:
                        argumentos = {}
                    herramientas.append(
                        ToolCall(
                            id=llamada.id,
                            name=llamada.function.name,
                            arguments=argumentos,
                            raw=cruda,
                        )
                    )

                return ChatResult(content=mensaje.content, tool_calls=herramientas, raw_tool_calls=crudas)

            except (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError) as exc:
                ultimo_error = exc
                log.warning("llm_reintento intento=%s tipo=%s", intento, type(exc).__name__)
            except openai.APIStatusError as exc:
                if exc.status_code >= 500:
                    ultimo_error = exc
                    log.warning("llm_reintento intento=%s status=%s", intento, exc.status_code)
                else:
                    raise LLMError(f"Error del proveedor ({exc.status_code})") from None
            except Exception as exc:
                raise LLMError(f"Error inesperado del proveedor ({type(exc).__name__})") from None

            if intento < self.max_reintentos:
                time.sleep(2 ** (intento - 1))

        raise LLMError(f"El proveedor no respondió ({type(ultimo_error).__name__ if ultimo_error else 'desconocido'})")
