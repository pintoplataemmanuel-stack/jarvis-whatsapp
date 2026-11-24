"""Conexión y esquema SQLite.

Las fechas se guardan en UTC ISO 8601. La zona America/Bogota se usa solo para
mostrar o programar. Nunca se guardan claves ni tokens en esta base de datos.
"""

import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator

from app.config import get_settings

ESQUEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    phone TEXT NOT NULL,
    direction TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_phone ON messages(phone, created_at);

CREATE TABLE IF NOT EXISTS conversation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tokens INTEGER NOT NULL DEFAULT 0,
    meta TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversation_phone ON conversation(phone, id);

CREATE TABLE IF NOT EXISTS facts (
    phone TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (phone, key)
);

CREATE TABLE IF NOT EXISTS summaries (
    phone TEXT NOT NULL,
    period TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (phone, period)
);

CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id TEXT PRIMARY KEY,
    phone TEXT NOT NULL,
    payload TEXT NOT NULL,
    due_at TEXT NOT NULL,
    last_sent_at TEXT
);
"""


def ruta_db(db_path: str | None = None) -> Path:
    ruta = Path(db_path or get_settings().db_path)
    if not ruta.is_absolute():
        ruta = Path.cwd() / ruta
    ruta.parent.mkdir(parents=True, exist_ok=True)
    return ruta


def conectar(db_path: str | None = None) -> sqlite3.Connection:
    conexion = sqlite3.connect(ruta_db(db_path), timeout=10)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA journal_mode=WAL")
    conexion.execute("PRAGMA foreign_keys=ON")
    return conexion


@contextmanager
def conexion(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    with closing(conectar(db_path)) as conex:
        try:
            yield conex
            conex.commit()
        except Exception:
            conex.rollback()
            raise


def inicializar(db_path: str | None = None) -> None:
    with conexion(db_path) as conex:
        conex.executescript(ESQUEMA)
