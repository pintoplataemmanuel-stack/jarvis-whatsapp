"""Compatibilidad del historial: delegado a SQLite.

Mantiene la interfaz `obtener(phone)` / `limpiar(phone)` que usaban las fases
anteriores, pero ahora cada `append` se persiste en la base de datos.
"""

from app.memory import repository
from app.security import normalize_phone


class HistorialDB:
    def __init__(self, phone: str) -> None:
        self.phone = normalize_phone(phone)

    def append(self, mensaje: dict) -> None:
        repository.agregar_historial(self.phone, mensaje)

    def __iter__(self):
        return iter(repository.cargar_historial(self.phone))

    def __len__(self) -> int:
        return repository.contar_historial(self.phone)


def obtener(phone: str) -> HistorialDB:
    return HistorialDB(phone)


def limpiar(phone: str) -> None:
    repository.limpiar_historial(normalize_phone(phone))
