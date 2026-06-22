"""RPA de associação — vincula automaticamente Ativo ↔ TAG ↔ Localização.

Fonte: um CSV de layout da planta (exportado da engenharia), com as colunas:

    tag, plant_code, plant_name, area_code, area_name

A cada execução o bot:
  1. Garante (upsert) as plantas e áreas declaradas no layout;
  2. Vincula cada TAG à sua planta/área (idempotente — só grava se mudou);
  3. Registra TAGs ainda sem cadastro como pendências (NO_ASSET).

Atende: "automatizar a atualização de registros e a vinculação entre o ativo,
sua TAG e sua localização" — sem input manual repetitivo.
"""

import csv
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sprint2.config import settings
from sprint2.logger import get_logger
from sprint2.models import Area, AssetAssociation, Plant
from sprint2.repository import Repository


class AssociationBot:
    """Bot RPA que mantém a associação Ativo-TAG-Localização em dia."""

    name = "association_bot"

    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()
        self.source = Path(settings.association_source)

    def _rows(self) -> list[dict[str, str]]:
        if not self.source.exists():
            return []
        with self.source.open(encoding="utf-8-sig", newline="") as fh:
            return [
                {(k or "").strip(): (v or "").strip() for k, v in row.items()}
                for row in csv.DictReader(fh)
            ]

    def run(self) -> dict:
        run_id = uuid4()
        log = get_logger(self.name, str(run_id))
        started = datetime.now(timezone.utc)
        t0 = time.perf_counter()

        rows = self._rows()
        records_in = len(rows)
        ok = failed = linked = unchanged = pending = 0
        last_error: str | None = None

        log.info(f"[{self.name}] Início — {records_in} vínculo(s) no layout")

        for row in rows:
            try:
                assoc = AssetAssociation(
                    tag=row["tag"],
                    plant_code=row["plant_code"],
                    area_code=row["area_code"],
                    plant_name=row.get("plant_name"),
                    area_name=row.get("area_name"),
                )
                # 1) garante planta e área (idempotente)
                self.repo.upsert_plant(
                    Plant(code=assoc.plant_code, name=assoc.plant_name or assoc.plant_code)
                )
                self.repo.upsert_area(
                    Area(
                        plant_code=assoc.plant_code,
                        code=assoc.area_code,
                        name=assoc.area_name or assoc.area_code,
                    )
                )
                # 2) vincula a TAG à localização
                result = self.repo.associate_location(assoc)
                if result == "LINKED":
                    linked += 1
                elif result == "UNCHANGED":
                    unchanged += 1
                else:  # NO_ASSET
                    pending += 1
                    log.warning(f"TAG sem cadastro (vínculo pendente): {assoc.tag}")
                ok += 1
            except Exception as e:
                failed += 1
                last_error = f"{type(e).__name__}: {e}"
                log.warning(f"Linha de layout descartada {row!r}: {last_error}")

        duration_ms = int((time.perf_counter() - t0) * 1000)
        status = "SUCCESS" if failed == 0 else ("PARTIAL" if ok > 0 else "FAILED")

        self.repo.log_execution(
            run_id=run_id,
            bot_name=self.name,
            started_at=started,
            status=status,
            records_in=records_in,
            records_ok=ok,
            records_failed=failed,
            duration_ms=duration_ms,
            error_message=last_error if status != "SUCCESS" else None,
            metadata={"linked": linked, "unchanged": unchanged, "pending": pending},
        )
        log.info(
            f"[{self.name}] Fim: status={status} in={records_in} ok={ok} "
            f"fail={failed} vinculados={linked} inalterados={unchanged} "
            f"pendentes={pending} dur={duration_ms}ms"
        )
        return {
            "status": status, "records_in": records_in, "ok": ok, "failed": failed,
            "linked": linked, "unchanged": unchanged, "pending": pending,
        }
