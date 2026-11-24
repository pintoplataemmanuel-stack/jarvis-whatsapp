"""Chat de terminal que usa el mismo manejador que el webhook.

Ejecutar:
    python -m app.simulator
"""

import asyncio
import os

from dotenv import load_dotenv

from app.agent import handle_message
from app.config import get_settings
from app.security import is_allowed, normalize_phone


def main() -> None:
    load_dotenv()
    settings = get_settings()
    phone = os.getenv("SIM_PHONE", "").strip()
    if not phone:
        phone = settings.allowed_numbers_raw.split(",")[0] if settings.allowed_numbers_raw else ""

    if not is_allowed(phone):
        print("SIM_PHONE no está en ALLOWED_NUMBERS. Revisa tu .env.")
        return

    print("Simulador Jarvis listo. Escribe /salir para terminar.")
    contador = 0
    while True:
        try:
            linea = input("Tú: ").strip()
        except EOFError:
            break

        if not linea:
            continue
        if linea.lower() == "/salir":
            break
        if linea.startswith("/id "):
            contador = int(linea[4:].strip() or contador)
            continue
        if linea.startswith("/audio "):
            print("Jarvis: las notas de voz se activan en la Fase 4.")
            continue

        contador += 1
        resultado = asyncio.run(handle_message(phone, linea, f"SIM-{contador}"))
        if resultado.respuesta:
            print(f"Jarvis: {resultado.respuesta}")
        else:
            print(f"Jarvis: [{resultado.estado}]")

    print("Hasta luego.")


if __name__ == "__main__":
    main()
