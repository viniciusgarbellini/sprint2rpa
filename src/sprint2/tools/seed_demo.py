"""Popula dados de demonstração para rodar a Sprint 2 isolada (vídeo/avaliação).

Faz, em ordem:
  1. gera as imagens de placa na pasta de drop;
  2. escreve o CSV de layout (associação TAG → planta/área);
  3. roda a RPA de placa  → cria os cadastros a partir das placas;
  4. roda a RPA de associação → cria plantas/áreas e vincula a localização;
  5. injeta uma série temporal sintética em readings_clean (últimas 24h) para
     que os dashboards tenham o que mostrar.

Idempotente: pode ser executado várias vezes (as RPAs e os INSERTs usam chaves
naturais / ON CONFLICT).
"""

import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from psycopg.types.json import Jsonb

from sprint2.association.bot import AssociationBot
from sprint2.config import settings
from sprint2.db import get_connection
from sprint2.logger import get_logger
from sprint2.nameplate.bot import NameplateBot
from sprint2.tools.gen_nameplates import DEMO_MOTORS, generate_all

log = get_logger("seed")

# Layout da planta (associação Ativo-TAG-Localização) — duas plantas.
LAYOUT_ROWS = [
    {"tag": "MTR-001", "plant_code": "PLT-SP", "plant_name": "Planta Sao Paulo",
     "area_code": "A-BOMBAS", "area_name": "Bombeamento"},
    {"tag": "MTR-002", "plant_code": "PLT-SP", "plant_name": "Planta Sao Paulo",
     "area_code": "A-COMPRESSORES", "area_name": "Casa de Compressores"},
    {"tag": "MTR-003", "plant_code": "PLT-SP", "plant_name": "Planta Sao Paulo",
     "area_code": "A-ESTEIRAS", "area_name": "Linha 2 - Conveyor"},
    {"tag": "MTR-004", "plant_code": "PLT-SP", "plant_name": "Planta Sao Paulo",
     "area_code": "A-EXAUSTAO", "area_name": "Casa de Maquinas - Exaustao"},
    {"tag": "MTR-005", "plant_code": "PLT-CP", "plant_name": "Planta Campinas",
     "area_code": "A-UTILIDADES", "area_name": "Utilidades"},
]


def _write_layout_csv() -> Path:
    path = Path(settings.association_source)
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["tag", "plant_code", "plant_name", "area_code", "area_name"]
    lines = [",".join(headers)]
    for row in LAYOUT_ROWS:
        lines.append(",".join(row[h] for h in headers))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info(f"Layout escrito: {path} ({len(LAYOUT_ROWS)} linhas)")
    return path


def _seed_readings(points: int = 48, hours: int = 24) -> int:
    """Injeta uma série temporal sintética por ativo (camadas raw + clean)."""
    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    inserted = 0

    with get_connection() as conn:
        for spec in DEMO_MOTORS:
            tag = spec["tag"]
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM assets WHERE tag = %s", (tag,))
                row = cur.fetchone()
            if row is None:
                continue
            asset_id = row[0]

            for i in range(points):
                measured_at = now - timedelta(hours=hours * (points - 1 - i) / points)
                phase = 2 * math.pi * i / points
                temp = round(60 + 8 * math.sin(phase) + rng.uniform(-2, 2), 2)
                vib = round(2.5 + 1.2 * math.sin(phase / 2) + rng.uniform(-0.4, 0.4), 2)
                current = round(spec["current_a"] * rng.uniform(0.70, 0.90), 2)
                voltage = round(spec["voltage_v"] * rng.uniform(0.98, 1.02), 2)
                rpm = int(spec["rpm"] * rng.uniform(0.99, 1.01))
                power = round(spec["power_kw"] * rng.uniform(0.60, 0.85), 2)
                quality = round(rng.uniform(0.90, 1.00), 2)
                source_id = f"seed:{tag}:{i}"
                payload = {"tag": tag, "seed": True, "i": i}

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO readings_raw
                            (asset_tag, source, source_id, payload, received_at, run_id)
                        VALUES (%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (source, source_id) DO NOTHING
                        RETURNING id
                        """,
                        (tag, "manual", source_id, Jsonb(payload),
                         measured_at, str(uuid4())),
                    )
                    raw = cur.fetchone()
                    if raw is None:
                        continue  # já semeado
                    raw_id = raw[0]
                    cur.execute(
                        """
                        INSERT INTO readings_clean
                            (raw_id, asset_id, asset_tag, measured_at,
                             temperature_c, vibration_mm_s, current_a, voltage_v,
                             rpm, power_kw, quality_score, flags)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (raw_id) DO NOTHING
                        """,
                        (raw_id, asset_id, tag, measured_at, temp, vib, current,
                         voltage, rpm, power, quality, Jsonb({})),
                    )
                    inserted += 1
        conn.commit()
    log.info(f"{inserted} leitura(s) sintética(s) inserida(s).")
    return inserted


def seed() -> None:
    log.info("== Seed de demonstração da Sprint 2 ==")
    generate_all(Path(settings.nameplate_drop_folder))
    _write_layout_csv()

    log.info("Rodando RPA de placa (cria cadastros a partir das placas)…")
    NameplateBot().run()

    log.info("Rodando RPA de associação (cria plantas/áreas e vincula)…")
    AssociationBot().run()

    _seed_readings()
    log.info("== Seed concluído. Abra o dashboard para visualizar. ==")


if __name__ == "__main__":
    from sprint2.db import apply_migrations

    apply_migrations()
    seed()
