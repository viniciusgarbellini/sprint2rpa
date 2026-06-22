"""Orquestrador das RPAs da Sprint 2 (APScheduler).

Agenda a RPA de placa e a RPA de associação em cron próprio (configurável por
env) e dispara um warm-up de cada uma no start. Isola falhas: erro num job não
derruba os demais. Encerramento gracioso em SIGINT/SIGTERM.
"""

import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from sprint2.association.bot import AssociationBot
from sprint2.config import settings
from sprint2.logger import get_logger
from sprint2.nameplate.bot import NameplateBot

log = get_logger("orchestrator")


def _safe_run(bot_factory, label: str) -> None:
    """Executa um bot capturando exceções (um job nunca derruba o scheduler)."""
    try:
        bot_factory().run()
    except Exception as e:
        log.exception(f"Job {label} falhou: {type(e).__name__}: {e}")


def run_forever() -> None:
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        lambda: _safe_run(NameplateBot, "nameplate_bot"),
        CronTrigger.from_crontab(settings.schedule_nameplate_bot),
        id="nameplate_bot",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        lambda: _safe_run(AssociationBot, "association_bot"),
        CronTrigger.from_crontab(settings.schedule_association_bot),
        id="association_bot",
        max_instances=1,
        coalesce=True,
    )

    def _shutdown(signum, _frame):
        log.info(f"Sinal {signum} recebido — encerrando scheduler…")
        scheduler.shutdown(wait=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    log.info("Warm-up: executando os dois bots uma vez antes de agendar…")
    _safe_run(NameplateBot, "nameplate_bot")      # 1º: placa cria/atualiza cadastro
    _safe_run(AssociationBot, "association_bot")   # 2º: vincula TAG → localização

    log.info(
        f"Scheduler ativo — nameplate='{settings.schedule_nameplate_bot}' "
        f"association='{settings.schedule_association_bot}'"
    )
    scheduler.start()
