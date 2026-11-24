import os

os.environ.setdefault("ALLOWED_NUMBERS", "573000000000")
os.environ.setdefault("SIM_PHONE", "573000000000")

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.evolution import EvolutionClient
from app.main import app
from app.simulator import main as simulador

client = TestClient(app)


@pytest.fixture(autouse=True)
def _settings(monkeypatch, tmp_path):
    monkeypatch.setenv("ALLOWED_NUMBERS", "573000000000")
    monkeypatch.setenv("SIM_PHONE", "573000000000")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "jarvis.db"))
    monkeypatch.setenv("WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _agente(monkeypatch):
    async def falso_agente(phone, historial):
        return f"Eco: {list(historial)[-1]['content']}"

    monkeypatch.setattr("app.agent.runner.ejecutar_agente", falso_agente)


@pytest.fixture
def enviados(monkeypatch):
    registro = []

    def falso_enviar(self, number, text):
        registro.append((number, text))
        return {"status": "PENDING"}

    monkeypatch.setattr(EvolutionClient, "send_text", falso_enviar)
    return registro


def mensaje(remote_jid, texto, message_id="M1"):
    return {
        "event": "messages.upsert",
        "instance": "jarvis",
        "data": {
            "key": {"remoteJid": remote_jid, "fromMe": False, "id": message_id},
            "pushName": "Ana",
            "message": {"conversation": texto},
            "messageType": "conversation",
            "messageTimestamp": "1700000000",
        },
    }


def test_mensaje_de_texto_se_repite(enviados):
    respuesta = client.post(
        "/webhook/evolution",
        json=mensaje("573000000000@s.whatsapp.net", "Hola Jarvis"),
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True}
    assert enviados == [("573000000000", "Eco: Hola Jarvis")]


def test_numero_no_permitido_no_recibe_respuesta(enviados):
    respuesta = client.post(
        "/webhook/evolution",
        json=mensaje("574999999999@s.whatsapp.net", "Hola"),
    )
    assert respuesta.status_code == 200
    assert enviados == []


def test_payload_mal_formado_no_envia(enviados):
    respuesta = client.post(
        "/webhook/evolution",
        content=b"{esto no es json",
        headers={"content-type": "application/json"},
    )
    assert respuesta.status_code == 400
    assert enviados == []


def test_payload_sin_evento_no_envia(enviados):
    respuesta = client.post("/webhook/evolution", json={"data": {}})
    assert respuesta.status_code == 422
    assert enviados == []


def test_mensaje_propio_no_envia(enviados):
    payload = mensaje("573000000000@s.whatsapp.net", "Hola")
    payload["data"]["key"]["fromMe"] = True
    respuesta = client.post("/webhook/evolution", json=payload)
    assert respuesta.status_code == 200
    assert enviados == []


def test_simulador_usa_el_mismo_manejador(monkeypatch, enviados):
    entradas = iter(["Hola desde terminal", "/salir"])
    monkeypatch.setattr("builtins.input", lambda _="": next(entradas))
    simulador()
    assert enviados == [("573000000000", "Eco: Hola desde terminal")]
