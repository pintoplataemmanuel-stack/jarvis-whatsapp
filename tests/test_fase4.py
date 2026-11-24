import asyncio
import base64

import pytest
from fastapi.testclient import TestClient

from app.agent import runner as modulo_runner
from app.agent.conversation import obtener
from app.agent.llm import ChatResult
from app.config import get_settings
from app.evolution import EvolutionClient
from app.main import app
from app.memory import db, repository
from app.voice import handler as modulo_voz

TELEFONO = "573000000000"
JID = f"{TELEFONO}@s.whatsapp.net"


@pytest.fixture(autouse=True)
def _config(monkeypatch, tmp_path):
    monkeypatch.setenv("ALLOWED_NUMBERS", TELEFONO)
    monkeypatch.setenv("DB_PATH", str(tmp_path / "jarvis.db"))
    monkeypatch.setenv("SUMMARY_MESSAGE_THRESHOLD", "5")
    monkeypatch.setenv("SUMMARY_TOKEN_THRESHOLD", "999999")
    monkeypatch.setenv("KEEP_RECENT_MESSAGES", "2")
    monkeypatch.setenv("REPLY_WITH_AUDIO", "false")
    monkeypatch.setenv("VOICE_ENABLED", "true")
    monkeypatch.setenv("WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class RespuestaFalsa:
    def __init__(self, status_code=200, datos=None, contenido=b"datos"):
        self.status_code = status_code
        self._datos = datos if datos is not None else {}
        self.content = contenido

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._datos


def test_esquema_sqlite_y_wal():
    db.inicializar()
    with db.conexion() as conex:
        tablas = {fila[0] for fila in conex.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        modo = conex.execute("PRAGMA journal_mode").fetchone()[0]

    assert {"messages", "conversation", "facts", "summaries", "scheduled_jobs"} <= tablas
    assert modo.lower() == "wal"


def test_idempotencia_de_mensajes():
    assert repository.guardar_mensaje("M1", TELEFONO, "in", "hola") is True
    assert repository.guardar_mensaje("M1", TELEFONO, "in", "hola") is False
    assert repository.guardar_mensaje(None, TELEFONO, "in", "hola") is False


def test_historial_persiste_y_conserva_metadatos_de_herramientas():
    historial = obtener(JID)
    historial.append({"role": "user", "content": "suma 2 y 3"})
    historial.append(
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "t1", "type": "function", "function": {"name": "sumar_numeros"}}],
        }
    )

    recargado = list(obtener(TELEFONO))
    assert len(recargado) == 2
    assert recargado[0]["content"] == "suma 2 y 3"
    assert recargado[1]["tool_calls"][0]["id"] == "t1"


def test_resumen_automatico_conserva_ultimos_mensajes():
    class ProveedorResumen:
        def __init__(self):
            self.llamadas = 0

        def chat(self, messages, tools=None):
            self.llamadas += 1
            return ChatResult(
                content="Resumen: Ana quiere recordar la reunión del lunes.",
                tool_calls=[],
            )

    for indice in range(6):
        repository.agregar_historial(TELEFONO, {"role": "user", "content": f"mensaje {indice}"})

    proveedor = ProveedorResumen()
    assert asyncio.run(repository.resumir_si_necesario(TELEFONO, proveedor)) is True
    assert proveedor.llamadas == 1
    assert repository.obtener_resumen(TELEFONO).startswith("Resumen: Ana")
    assert repository.contar_historial(TELEFONO) == 2

    historial = repository.cargar_historial(TELEFONO)
    assert historial[0]["role"] == "system"
    assert "Resumen de conversaciones anteriores" in historial[0]["content"]

    otro = ProveedorResumen()
    assert asyncio.run(repository.resumir_si_necesario(TELEFONO, otro)) is False
    assert otro.llamadas == 0


def test_descarga_de_audio_usa_endpoint_oficial(monkeypatch):
    llamadas = []

    def falso_post(url, headers, json, timeout):
        llamadas.append((url, headers, json))
        return RespuestaFalsa(
            datos={"base64": "data:audio/ogg;base64," + base64.b64encode(b"audio-ogg").decode()}
        )

    monkeypatch.setattr("app.evolution.client.httpx.post", falso_post)

    cliente = EvolutionClient(base_url="http://evo:8080/", api_key="CLAVE_LOCAL", instance="jarvis")
    datos = cliente.download_media("ABC123")

    assert datos == b"audio-ogg"
    assert llamadas[0][0] == "http://evo:8080/chat/getBase64FromMediaMessage/jarvis"
    assert llamadas[0][1]["apikey"] == "CLAVE_LOCAL"
    assert llamadas[0][2] == {"message": {"key": {"id": "ABC123"}}, "convertToMp4": False}


def test_envio_de_audio_v2_y_fallback_v1(monkeypatch):
    cuerpos = []
    respuestas = [RespuestaFalsa(400), RespuestaFalsa(200)]

    def falso_post(url, headers, json, timeout):
        cuerpos.append(json)
        return respuestas.pop(0)

    monkeypatch.setattr("app.evolution.client.httpx.post", falso_post)

    EvolutionClient(base_url="http://evo:8080", api_key="k", instance="jarvis").send_audio(
        TELEFONO, "YXVkaW8="
    )

    assert cuerpos[0] == {"number": TELEFONO, "audio": "YXVkaW8=", "encoding": True}
    assert cuerpos[1]["audioMessage"]["audio"] == "YXVkaW8="
    assert cuerpos[1]["options"]["presence"] == "recording"


def test_nota_de_voz_se_transcribe_y_va_al_manejador_comun(monkeypatch):
    recibido = []
    enviados = []

    monkeypatch.setattr(EvolutionClient, "download_media", lambda self, message_id: b"audio-ogg")
    monkeypatch.setattr(modulo_voz, "transcribir", lambda ruta: "Necesito la hora en Bogotá")
    monkeypatch.setattr(EvolutionClient, "send_text", lambda self, number, text: enviados.append(text))

    async def falso_handle(phone, text, message_id=None):
        recibido.append((phone, text, message_id))

    monkeypatch.setattr(modulo_voz, "handle_message", falso_handle)

    asyncio.run(modulo_voz.procesar_nota_de_voz(JID, "VOZ1"))

    assert recibido == [(JID, "Necesito la hora en Bogotá", "VOZ1")]
    assert enviados == []
    assert modulo_voz.ruta_audio("VOZ1").exists() is False


def test_nota_de_voz_vacia_pide_repetir(monkeypatch):
    enviados = []
    llamados = []

    monkeypatch.setattr(EvolutionClient, "download_media", lambda self, message_id: b"audio-ogg")
    monkeypatch.setattr(modulo_voz, "transcribir", lambda ruta: "   ")
    monkeypatch.setattr(EvolutionClient, "send_text", lambda self, number, text: enviados.append(text))

    async def falso_handle(phone, text, message_id=None):
        llamados.append(text)

    monkeypatch.setattr(modulo_voz, "handle_message", falso_handle)

    asyncio.run(modulo_voz.procesar_nota_de_voz(JID, "VOZ2"))

    assert enviados == ["No te escuché bien. Repite el mensaje más cerca del micrófono."]
    assert llamados == []


def test_webhook_enruta_notas_de_voz(monkeypatch):
    voces = []
    textos = []

    monkeypatch.setattr(
        "app.main.procesar_nota_de_voz",
        lambda phone, message_id: voces.append((phone, message_id)),
    )
    monkeypatch.setattr(
        "app.main.handle_message",
        lambda phone, text, message_id: textos.append(text),
    )

    payload = {
        "event": "messages.upsert",
        "instance": "jarvis",
        "data": {
            "key": {"remoteJid": JID, "fromMe": False, "id": "VOZ3"},
            "message": {"audioMessage": {"mimetype": "audio/ogg"}},
            "messageType": "audioMessage",
        },
    }

    respuesta = TestClient(app).post("/webhook/evolution", json=payload)

    assert respuesta.status_code == 200
    assert voces == [(JID, "VOZ3")]
    assert textos == []


def test_respuesta_por_audio_opcional_y_retroceso_a_texto(monkeypatch):
    monkeypatch.setenv("REPLY_WITH_AUDIO", "true")
    get_settings.cache_clear()
    audios = []

    async def falso_agente(phone, historial):
        return "Son las tres de la tarde."

    monkeypatch.setattr(modulo_runner, "ejecutar_agente", falso_agente)
    monkeypatch.setattr(modulo_runner, "sintetizar", lambda texto: "YXVkaW8=")
    monkeypatch.setattr(
        EvolutionClient,
        "send_audio",
        lambda self, number, audio: audios.append((number, audio)),
    )
    monkeypatch.setattr(EvolutionClient, "send_text", lambda self, number, text: pytest.fail("debió usar audio"))

    resultado = asyncio.run(modulo_runner.handle_message(JID, "dame la hora"))

    assert resultado.estado == "enviado_audio"
    assert audios == [(TELEFONO, "YXVkaW8=")]

    monkeypatch.setattr(modulo_runner, "sintetizar", lambda texto: (_ for _ in ()).throw(ImportError("sin pyttsx3")))
    texto_enviado = []
    monkeypatch.setattr(
        EvolutionClient,
        "send_text",
        lambda self, number, text: texto_enviado.append(text),
    )

    resultado = asyncio.run(modulo_runner.handle_message(JID, "dame la hora"))

    assert resultado.estado == "enviado"
    assert texto_enviado == ["Son las tres de la tarde."]
