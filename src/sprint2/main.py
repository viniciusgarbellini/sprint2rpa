"""Entrypoint da Sprint 2.

Modos:
  python -m sprint2.main init             → aplica as migrations (idempotente)
  python -m sprint2.main seed             → popula dados de demonstração
  python -m sprint2.main run              → inicia o orquestrador (loop principal)
  python -m sprint2.main once nameplate   → roda a RPA de placa uma vez
  python -m sprint2.main once associate   → roda a RPA de associação uma vez
"""

import sys

from sprint2.association.bot import AssociationBot
from sprint2.db import apply_migrations
from sprint2.logger import get_logger
from sprint2.nameplate.bot import NameplateBot
from sprint2.orchestrator import run_forever

log = get_logger("main")


def cmd_init() -> None:
    log.info("Aplicando migrations da Sprint 2…")
    apply_migrations()
    log.info("Schema pronto.")


def cmd_seed() -> None:
    from sprint2.tools.seed_demo import seed

    apply_migrations()
    seed()


def cmd_run() -> None:
    apply_migrations()
    run_forever()


def cmd_once(name: str) -> None:
    bots = {"nameplate": NameplateBot, "associate": AssociationBot}
    cls = bots.get(name)
    if cls is None:
        log.error(f"Bot desconhecido: {name}. Disponíveis: {list(bots)}")
        sys.exit(2)
    apply_migrations()
    result = cls().run()
    log.info(f"Resultado: {result}")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    cmd, *rest = args
    if cmd == "init":
        cmd_init()
    elif cmd == "seed":
        cmd_seed()
    elif cmd == "run":
        cmd_run()
    elif cmd == "once" and rest:
        cmd_once(rest[0])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
