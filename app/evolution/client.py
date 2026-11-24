import base64

import httpx

from app.config import get_settings

EVENTOS = ["MESSAGES_UPSERT", "QRCODE_UPDATED", "CONNECTION_UPDATE"]


def _limpiar_base64(valor: str) -> str:
    """Quita el prefijo `data:...;base64,` que algunas versiones añaden."""
    texto = valor.strip()
    if texto.startswith("data:"):
        texto = texto.split(",", 1)[-1]
    return "".join(texto.split())


class EvolutionClient:
    """Cliente mínimo basado en la documentación oficial de Evolution API.

    Intenta primero el formato v2 y, si falla, el formato v1.
    La API key nunca se registra en logs.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        instance: str | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.evolution_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.evolution_api_key
        self.instance = instance or settings.evolution_instance

    def _headers(self) -> dict[str, str]:
        return {"apikey": self.api_key, "Content-Type": "application/json"}

    def send_text(self, number: str, text: str) -> dict:
        url = f"{self.base_url}/message/sendText/{self.instance}"

        respuesta = httpx.post(url, headers=self._headers(), json={"number": number, "text": text}, timeout=20)
        if respuesta.status_code < 400:
            return respuesta.json()

        respuesta = httpx.post(
            url,
            headers=self._headers(),
            json={"number": number, "textMessage": {"text": text}},
            timeout=20,
        )
        respuesta.raise_for_status()
        return respuesta.json()

    def download_media(self, message_id: str, convert_to_mp4: bool = False) -> bytes:
        """Descarga multimedia con `POST /chat/getBase64FromMediaMessage/{instance}`.

        El cuerpo es `{"message": {"key": {"id": ...}}, "convertToMp4": bool}`,
        según la documentación oficial. El campo de respuesta puede ser
        `base64`, `media` o `data` según la versión desplegada.
        """
        if not message_id:
            raise ValueError("message_id vacío")

        url = f"{self.base_url}/chat/getBase64FromMediaMessage/{self.instance}"
        cuerpo = {
            "message": {"key": {"id": message_id}},
            "convertToMp4": convert_to_mp4,
        }
        respuesta = httpx.post(url, headers=self._headers(), json=cuerpo, timeout=60)
        respuesta.raise_for_status()
        datos = respuesta.json() if respuesta.content else {}

        if not isinstance(datos, dict):
            raise ValueError("respuesta de multimedia inesperada")

        contenido = None
        for clave in ("base64", "media", "data"):
            valor = datos.get(clave)
            if isinstance(valor, str) and valor.strip():
                contenido = valor
                break
            if isinstance(valor, dict):
                interno = valor.get("base64")
                if isinstance(interno, str) and interno.strip():
                    contenido = interno
                    break
        if contenido is None:
            raise ValueError("la respuesta no incluye base64")

        return base64.b64decode(_limpiar_base64(contenido), validate=False)

    def send_audio(self, number: str, audio_base64: str) -> dict:
        """Envía nota de voz con `POST /message/sendWhatsAppAudio/{instance}`.

        v2: `{number, audio, encoding}`.
        v1: `{number, audioMessage: {audio}, options: {encoding, presence}}`.
        """
        url = f"{self.base_url}/message/sendWhatsAppAudio/{self.instance}"
        audio = _limpiar_base64(audio_base64)

        respuesta = httpx.post(
            url,
            headers=self._headers(),
            json={"number": number, "audio": audio, "encoding": True},
            timeout=60,
        )
        if respuesta.status_code < 400:
            return respuesta.json()

        respuesta = httpx.post(
            url,
            headers=self._headers(),
            json={
                "number": number,
                "audioMessage": {"audio": audio},
                "options": {"encoding": True, "presence": "recording"},
            },
            timeout=60,
        )
        respuesta.raise_for_status()
        return respuesta.json()
