"""RPA de placa — automatiza: imagem da placa → cadastro do ativo.

Varre a pasta de drop por imagens de placa (.png/.jpg), executa o pipeline de
extração, preenche/atualiza o cadastro do ativo, registra a proveniência e
arquiva a imagem processada. Toda execução vira uma linha em execution_logs.

Atende: "automatizar a atualização de registros sem input manual repetitivo" e
"da extração da imagem da placa até o preenchimento do cadastro".
"""

import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sprint2.config import settings
from sprint2.logger import get_logger
from sprint2.nameplate.extractor import extract_nameplate
from sprint2.repository import Repository

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


class NameplateBot:
    """Bot RPA que transforma imagens de placa em cadastro de ativo."""

    name = "nameplate_bot"

    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()
        self.drop = Path(settings.nameplate_drop_folder)
        self.archive = Path(settings.nameplate_archive_folder)

    def _images(self) -> list[Path]:
        if not self.drop.exists():
            return []
        return sorted(
            p for p in self.drop.iterdir()
            if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES
        )

    def run(self) -> dict:
        run_id = uuid4()
        log = get_logger(self.name, str(run_id))
        started = datetime.now(timezone.utc)
        t0 = time.perf_counter()

        images = self._images()
        records_in = len(images)
        ok = failed = created = updated = 0
        last_error: str | None = None

        log.info(f"[{self.name}] Início — {records_in} placa(s) na fila")

        for image in images:
            try:
                data, ocr_text = extract_nameplate(str(image))
                asset_id, was_created = self.repo.upsert_asset_from_nameplate(data)
                self.repo.insert_nameplate_record(
                    asset_id=asset_id,
                    np=data,
                    source_image=image.name,
                    ocr_text=ocr_text,
                    extracted_by=self.name,
                )
                created += int(was_created)
                updated += int(not was_created)
                ok += 1
                self.archive.mkdir(parents=True, exist_ok=True)
                shutil.move(str(image), str(self.archive / image.name))
                log.info(
                    f"Placa OK: {image.name} → TAG={data.tag} "
                    f"({'novo' if was_created else 'atualizado'}, "
                    f"conf={data.ocr_confidence})"
                )
            except Exception as e:  # falha de 1 placa não derruba o lote
                failed += 1
                last_error = f"{type(e).__name__}: {e}"
                log.warning(f"Placa descartada {image.name}: {last_error}")

        duration_ms = int((time.perf_counter() - t0) * 1000)
        if records_in == 0:
            status = "SUCCESS"
        elif failed == 0:
            status = "SUCCESS"
        elif ok > 0:
            status = "PARTIAL"
        else:
            status = "FAILED"

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
            metadata={"created": created, "updated": updated},
        )
        log.info(
            f"[{self.name}] Fim: status={status} in={records_in} ok={ok} "
            f"fail={failed} novos={created} atualizados={updated} dur={duration_ms}ms"
        )
        return {
            "status": status, "records_in": records_in, "ok": ok,
            "failed": failed, "created": created, "updated": updated,
        }
