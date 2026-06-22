"""Logging estruturado (Loguru) — mesmo padrão da Sprint 1.

Saída em JSON quando LOG_FORMAT=json, facilitando auditoria com `jq`.
Cada bot recebe um logger ligado (`bind`) ao seu nome e ao run_id da execução.
"""

import sys

from loguru import logger

from sprint2.config import settings

_configured = False


def setup_logger() -> None:
    """Configura sinks do Loguru (idempotente)."""
    global _configured
    if _configured:
        return

    logger.remove()
    serialize = settings.log_format.lower() == "json"

    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        serialize=serialize,
        backtrace=False,
        diagnose=False,
    )

    settings.log_folder.mkdir(parents=True, exist_ok=True)
    logger.add(
        settings.log_folder / "sprint2.log",
        level=settings.log_level.upper(),
        serialize=True,
        rotation="10 MB",
        retention="14 days",
        enqueue=True,
    )
    _configured = True


def get_logger(bot: str, run_id: str = "-"):
    """Retorna um logger ligado ao bot e ao run_id da execução."""
    setup_logger()
    return logger.bind(bot=bot, run_id=run_id)


setup_logger()
