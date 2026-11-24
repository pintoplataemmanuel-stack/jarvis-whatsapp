import asyncio
import re

import pytest

from app.agent import runner as modulo_runner
from app.agent.conversation import limpiar
from app.agent.llm import ChatResult, LLMError, ToolCall
from app.config import get_settings
from app.evolution import EvolutionClient
from app.memory import repository


@pytest.fixture(autouse=True)
def _limpio(monkeypatch, tmp_path):
    monkeypatch.setenv("ALLOWED_NUMBERS", "573000000000")
    monkeypatch.setenv("MAX_TOOL_ITERATIONS", "3")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "jarvis.db"))
    monkeypatch.setenv("WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    limpiar("573000000000")
    modulo_runner.PENDIENTES.clear()
    yield
    get_settings.cache_clear()
    limpiar("573000000000")
    modulo_runner.PENDIENTES.clear()


@pytest.fixture
def enviados(monkeypatch):
    registro = []

    def falso_enviar(self, number, text):
        registro.append((number, text))
        return {"status": "PENDING"}

    monkeypatch.setattr(EvolutionClient, "send_text", falso_enviar)
    return registro


def herramienta_llamada(identificador, nombre, argumentos):
    cruda = {
        "id": identificador,
        "type": "function",
        "function": {"name": nombre, "arguments": __import__("json").dumps(argumentos)},
    }
    return ToolCall(id=identificador, name=nombre, arguments=argumentos, raw=cruda)


def test_tool_calling_suma(enviados, monkeypatch):
    estados = {"n": 0}

    class ProveedorFalso:
        def chat(self, messages, tools=None):
            estados["n"] += 1
            if estados["n"] == 1:
                llamada = herramienta_llamada("t1", "sumar_numeros", {"a": 2, "b": 3})
                return ChatResult(content=None, tool_calls=[llamada], raw_tool_calls=[llamada.raw])
            assert any(m.get("role") == "tool" and "Resultado: 5" in m.get("content", "") for m in messages)
            return ChatResult(content="La suma es 5.", tool_calls=[], raw_tool_calls=[])

    monkeypatch.setattr(modulo_runner, "LLMProvider", ProveedorFalso)

    resultado = asyncio.run(modulo_runner.handle_message("573000000000@s.whatsapp.net", "suma 2 y 3"))

    assert resultado.estado == "enviado"
    assert enviados == [("573000000000", "La suma es 5.")]
    assert estados["n"] == 2


def test_accion_destructiva_pide_confirmacion(enviados, monkeypatch):
    class ProveedorFalso:
        def chat(self, messages, tools=None):
            llamada = herramienta_llamada("t2", "borrar_historial", {"motivo": "prueba"})
            return ChatResult(content=None, tool_calls=[llamada], raw_tool_calls=[llamada.raw])

    monkeypatch.setattr(modulo_runner, "LLMProvider", ProveedorFalso)

    primera = asyncio.run(modulo_runner.handle_message("573000000000", "borra mi historial"))
    assert "CONFIRMAR" in (primera.respuesta or "")
    codigo = re.search(r"CONFIRMAR ([a-f0-9]{8})", primera.respuesta).group(1)
    assert repository.contar_historial("573000000000") > 0
    assert not any("borrado" in texto for _, texto in enviados)

    segunda = asyncio.run(modulo_runner.handle_message("573000000000", f"CONFIRMAR {codigo}"))

    assert segunda.respuesta == "Historial de conversación borrado."
    assert repository.contar_historial("573000000000") == 0
    assert codigo not in modulo_runner.PENDIENTES
    assert enviados[-1][1] == "Historial de conversación borrado."


def test_error_del_modelo_es_amigable(enviados, monkeypatch):
    class ProveedorFallo:
        def chat(self, messages, tools=None):
            raise LLMError("detalle interno")

    monkeypatch.setattr(modulo_runner, "LLMProvider", ProveedorFallo)

    resultado = asyncio.run(modulo_runner.handle_message("573000000000", "hola"))

    assert resultado.respuesta == "No pude conectar con el modelo en este momento."
    assert enviados == [("573000000000", "No pude conectar con el modelo en este momento.")]


def test_definiciones_de_herramientas_incluyen_esquemas():
    definiciones = modulo_runner.definitions()
    nombres = {item["function"]["name"] for item in definiciones}
    assert {"obtener_hora_local", "sumar_numeros", "borrar_historial"} <= nombres
    assert all(item["type"] == "function" for item in definiciones)
    assert "confirmación" in modulo_runner.SYSTEM_PROMPT
