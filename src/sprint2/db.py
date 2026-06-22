"""Camada fina de conexão com o PostgreSQL (psycopg 3).

Não duplica o Repository da Sprint 1: aqui há apenas o boilerplate de conexão
com retry exponencial (o app sobe junto do banco no compose) e o aplicador de
migrations da Sprint 2.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from sprint2.config import settings
from sprint2.logger import get_logger

log = get_logger("db")

# Diretório raiz do projeto (…/SPRINT 2), para localizar db/migrations.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS_DIR = _PROJECT_ROOT / "db" / "migrations"


@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=1, min=1, max=15),
    retry=retry_if_exception_type(psycopg.OperationalError),
    reraise=True,
)
def _connect() -> psycopg.Connection:
    return psycopg.connect(settings.db_dsn)


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Context manager de conexão com auto-close."""
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def apply_migrations() -> None:
    """Aplica todas as migrations *.sql de db/migrations em ordem (idempotente)."""
    if not _MIGRATIONS_DIR.exists():
        log.warning(f"Diretório de migrations não encontrado: {_MIGRATIONS_DIR}")
        return

    files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
    with get_connection() as conn:
        for sql_file in files:
            sql = sql_file.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            log.info(f"Migration aplicada: {sql_file.name}")
