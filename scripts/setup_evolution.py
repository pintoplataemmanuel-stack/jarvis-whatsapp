"""Crea la instancia, configura el webhook y guarda el QR de Evolution API.

Uso desde la máquina anfitriona:
    python scripts/setup_evolution.py --base-url http://localhost:8080

Uso desde el contenedor del backend:
    docker compose exec backend python scripts/setup_evolution.py
"""

import argparse
import base64
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

EVENTOS = ["MESSAGES_UPSERT", "QRCODE_UPDATED", "CONNECTION_UPDATE"]
WEBHOOK_PATH = Path("data/qr.png")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default=os.getenv("EVOLUTION_BASE_URL", "http://evolution:8080"),
        help="URL base de Evolution API alcanzable desde donde se ejecuta el script",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    api_key = os.getenv("EVOLUTION_API_KEY", "")
    instance = os.getenv("EVOLUTION_INSTANCE", "jarvis")
    webhook_url = os.getenv("EVOLUTION_WEBHOOK_URL", "http://backend:8000/webhook/evolution")
    number = os.getenv("EVOLUTION_NUMBER", "").strip()
    secreto = os.getenv("WEBHOOK_SECRET", "").strip()
    headers = {"apikey": api_key, "Content-Type": "application/json"}

    def post(path: str, body: dict) -> httpx.Response:
        respuesta = httpx.post(f"{base}{path}", headers=headers, json=body, timeout=30)
        print(f"POST {path} -> {respuesta.status_code}")
        return respuesta

    print(f"Evolution API: {base}")
    print(f"Instancia: {instance}")
    print(f"Webhook: {webhook_url}")

    crear = {
        "instanceName": instance,
        "integration": "WHATSAPP-BAILEYS",
        "qrcode": True,
    }
    if number:
        crear["number"] = number
    respuesta = post("/instance/create", crear)
    if respuesta.status_code >= 400:
        print("Aviso: no se pudo crear (¿ya existe?). Continúo con la instancia existente.")
        print(f"Detalle: {respuesta.text[:300]}")

    # Evolution API v2: /webhook/set espera el body envuelto en "webhook".
    cabeceras_webhook = {"x-jarvis-secret": secreto} if secreto else {}
    v2 = {"webhook": {
        "enabled": True,
        "url": webhook_url,
        "events": EVENTOS,
        "byEvents": False,
        "base64": False,
        "headers": cabeceras_webhook,
    }}
    respuesta = post(f"/webhook/set/{instance}", v2)
    if respuesta.status_code >= 400:
        # Algunas versiones antiguas aceptan los nombres snake_case dentro del envelope.
        v1 = {"webhook": {
            "enabled": True,
            "url": webhook_url,
            "events": EVENTOS,
            "by_events": False,
            "base64": False,
            "headers": cabeceras_webhook,
        }}
        respuesta = post(f"/webhook/set/{instance}", v1)
        if respuesta.status_code >= 400:
            print("ERROR: no se pudo configurar el webhook ni en v2 ni en v1.")
            print(f"Detalle: {respuesta.text[:300]}")
            return

    if secreto:
        print("Cabecera x-jarvis-secret configurada. El secreto nunca se imprime.")

    respuesta = httpx.get(f"{base}/instance/connect/{instance}", headers=headers, timeout=30)
    print(f"GET /instance/connect/{instance} -> {respuesta.status_code}")
    datos = respuesta.json() if respuesta.status_code < 400 else {}

    if isinstance(datos, dict):
        print(f"Campos devueltos: {', '.join(sorted(datos.keys()))}")
        pairing = datos.get("pairingCode")
        if pairing:
            print(f"Código de emparejamiento: {pairing}")

        candidato = None
        for clave in ("base64", "qrcode", "code"):
            valor = datos.get(clave)
            if isinstance(valor, str) and len(valor) > 150:
                candidato = valor
                break

        if candidato:
            crudo = candidato.split(",", 1)[1] if candidato.startswith("data:image") else candidato
            try:
                WEBHOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
                WEBHOOK_PATH.write_bytes(base64.b64decode(crudo))
                print(f"QR guardado en {WEBHOOK_PATH}")
            except Exception:
                print(f"No se pudo decodificar el QR automáticamente. Ábrelo en Swagger: /instance/connect/{instance}")
        else:
            print(f"No encontré un campo de QR claro. Ábrelo en Swagger: /instance/connect/{instance}")

    respuesta = httpx.get(f"{base}/instance/connectionState/{instance}", headers=headers, timeout=30)
    print(f"GET /instance/connectionState/{instance} -> {respuesta.status_code}")
    if respuesta.status_code < 400:
        print("Estado:")
        print(json.dumps(respuesta.json(), ensure_ascii=False, indent=2)[:1000])


if __name__ == "__main__":
    main()
