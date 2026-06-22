"""Repository da Sprint 2 — encapsula o SQL das entidades novas.

Cobre: plantas, áreas, vínculo de localização, rastreio de placa, auditoria de
acesso e as consultas de navegação/visualização. Também grava a auditoria das
RPAs em `execution_logs` (a mesma tabela da Sprint 1, mantendo rastreabilidade
unificada). Não reimplementa a coleta de leituras — apenas LÊ readings_clean.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from sprint2.db import get_connection
from sprint2.models import (
    AccessEvent,
    Area,
    AssetAssociation,
    NameplateData,
    Plant,
)


def _rows_as_dicts(cur) -> list[dict[str, Any]]:
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


class Repository:
    """Acesso a dados das entidades novas da Sprint 2."""

    # ------------------------- HIERARQUIA / LOCALIZAÇÃO --------------------

    def upsert_plant(self, plant: Plant) -> int:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO plants (code, name, city)
                VALUES (%s, %s, %s)
                ON CONFLICT (code) DO UPDATE
                    SET name = EXCLUDED.name, city = EXCLUDED.city
                RETURNING id
                """,
                (plant.code, plant.name, plant.city),
            )
            plant_id = cur.fetchone()[0]
            conn.commit()
            return plant_id

    def upsert_area(self, area: Area) -> int:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM plants WHERE code = %s", (area.plant_code,))
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"Planta inexistente para área: {area.plant_code!r}")
            plant_id = row[0]
            cur.execute(
                """
                INSERT INTO areas (plant_id, code, name)
                VALUES (%s, %s, %s)
                ON CONFLICT (plant_id, code) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                (plant_id, area.code, area.name),
            )
            area_id = cur.fetchone()[0]
            conn.commit()
            return area_id

    def associate_location(self, assoc: AssetAssociation) -> str:
        """Vincula uma TAG à sua planta/área. Idempotente.

        Retorna: 'LINKED' (mudou), 'UNCHANGED' (já estava) ou 'NO_ASSET'
        (TAG ainda sem cadastro — vínculo fica pendente).
        """
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM plants WHERE code = %s", (assoc.plant_code,))
            prow = cur.fetchone()
            cur.execute(
                "SELECT a.id FROM areas a JOIN plants p ON p.id = a.plant_id "
                "WHERE p.code = %s AND a.code = %s",
                (assoc.plant_code, assoc.area_code),
            )
            arow = cur.fetchone()
            if prow is None or arow is None:
                raise ValueError(
                    f"Planta/área inexistente: {assoc.plant_code}/{assoc.area_code}"
                )
            plant_id, area_id = prow[0], arow[0]

            cur.execute(
                "SELECT id, plant_id, area_id FROM assets WHERE tag = %s",
                (assoc.tag,),
            )
            asset = cur.fetchone()
            if asset is None:
                conn.commit()
                return "NO_ASSET"

            asset_id, cur_plant, cur_area = asset
            if cur_plant == plant_id and cur_area == area_id:
                return "UNCHANGED"

            cur.execute(
                "UPDATE assets SET plant_id = %s, area_id = %s WHERE id = %s",
                (plant_id, area_id, asset_id),
            )
            conn.commit()
            return "LINKED"

    # ------------------------- CADASTRO VIA PLACA --------------------------

    def upsert_asset_from_nameplate(self, np: NameplateData) -> tuple[int, bool]:
        """Cria/atualiza o cadastro do ativo com os dados extraídos da placa.

        Preenche apenas campos técnicos da placa; NÃO toca em localização
        (isso é função da RPA de associação). Idempotente por TAG.

        Retorna (asset_id, created) — created=True se foi um INSERT.
        """
        default_name = np.name or f"Motor {np.tag}"
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM assets WHERE tag = %s", (np.tag,))
            existing = cur.fetchone()

            if existing is None:
                cur.execute(
                    """
                    INSERT INTO assets (
                        tag, name, manufacturer, model,
                        rated_power_kw, rated_voltage_v, rated_current_a, rated_rpm
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (
                        np.tag, default_name, np.manufacturer, np.model,
                        np.rated_power_kw, np.rated_voltage_v,
                        np.rated_current_a, np.rated_rpm,
                    ),
                )
                asset_id = cur.fetchone()[0]
                conn.commit()
                return asset_id, True

            asset_id = existing[0]
            # COALESCE: dados da placa preenchem lacunas / atualizam o cadastro,
            # mas um nome já definido não é sobrescrito por um genérico.
            cur.execute(
                """
                UPDATE assets SET
                    manufacturer    = COALESCE(%s, manufacturer),
                    model           = COALESCE(%s, model),
                    rated_power_kw  = COALESCE(%s, rated_power_kw),
                    rated_voltage_v = COALESCE(%s, rated_voltage_v),
                    rated_current_a = COALESCE(%s, rated_current_a),
                    rated_rpm       = COALESCE(%s, rated_rpm)
                WHERE id = %s
                """,
                (
                    np.manufacturer, np.model, np.rated_power_kw,
                    np.rated_voltage_v, np.rated_current_a, np.rated_rpm,
                    asset_id,
                ),
            )
            conn.commit()
            return asset_id, False

    def insert_nameplate_record(
        self,
        asset_id: int,
        np: NameplateData,
        source_image: str,
        ocr_text: str,
        extracted_by: str = "nameplate_bot",
    ) -> int:
        """Registra a proveniência da extração da placa (rastreabilidade)."""
        extracted = np.model_dump(mode="json")
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO asset_nameplates
                    (asset_id, tag, source_image, ocr_text, extracted,
                     ocr_confidence, extracted_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    asset_id, np.tag, source_image, ocr_text,
                    Jsonb(extracted), np.ocr_confidence, extracted_by,
                ),
            )
            rec_id = cur.fetchone()[0]
            conn.commit()
            return rec_id

    # ------------------------- AUDITORIA RPA (execution_logs) --------------

    def log_execution(
        self,
        run_id: UUID,
        bot_name: str,
        started_at: datetime,
        status: str,
        records_in: int,
        records_ok: int,
        records_failed: int,
        duration_ms: int,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO execution_logs
                    (run_id, bot_name, started_at, finished_at, status,
                     records_in, records_ok, records_failed, duration_ms,
                     error_message, metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(run_id), bot_name, started_at,
                    datetime.now(timezone.utc), status,
                    records_in, records_ok, records_failed, duration_ms,
                    error_message, Jsonb(metadata or {}),
                ),
            )
            conn.commit()

    # ------------------------- AUDITORIA DE ACESSO -------------------------

    def log_access(self, event: AccessEvent) -> None:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO access_logs (username, role, action, target) "
                "VALUES (%s, %s, %s, %s)",
                (event.username, event.role, event.action, event.target),
            )
            conn.commit()

    def recent_access_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT username, role, action, target, at "
                "FROM access_logs ORDER BY at DESC LIMIT %s",
                (limit,),
            )
            return _rows_as_dicts(cur)

    # ------------------------- NAVEGAÇÃO / CONSULTA ------------------------

    def navigation_tree(self) -> list[dict[str, Any]]:
        """Plantas → áreas com contagem de ativos (árvore de navegação)."""
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM v_navigation")
            return _rows_as_dicts(cur)

    def list_plants(self) -> list[dict[str, Any]]:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT id, code, name, city FROM plants ORDER BY name")
            return _rows_as_dicts(cur)

    def list_areas(self, plant_id: int) -> list[dict[str, Any]]:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, code, name FROM areas WHERE plant_id = %s ORDER BY name",
                (plant_id,),
            )
            return _rows_as_dicts(cur)

    def assets_in_area(self, area_id: int) -> list[dict[str, Any]]:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, tag, name, status FROM assets "
                "WHERE area_id = %s ORDER BY tag",
                (area_id,),
            )
            return _rows_as_dicts(cur)

    def search_by_tag(self, query: str) -> list[dict[str, Any]]:
        """Localiza ativos cuja TAG contém o termo (case-insensitive)."""
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM v_asset_location "
                "WHERE tag ILIKE %s ORDER BY tag LIMIT 50",
                (f"%{query}%",),
            )
            return _rows_as_dicts(cur)

    def asset_location(self, tag: str) -> dict[str, Any] | None:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM v_asset_location WHERE tag = %s", (tag,))
            rows = _rows_as_dicts(cur)
            return rows[0] if rows else None

    def asset_full(self, tag: str) -> dict[str, Any] | None:
        """Cadastro completo do ativo (placa) + localização para a tela de detalhe."""
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.id AS asset_id, a.tag, a.name, a.status,
                       a.manufacturer, a.model,
                       a.rated_power_kw, a.rated_voltage_v,
                       a.rated_current_a, a.rated_rpm,
                       p.name AS plant_name, ar.name AS area_name,
                       a.location AS location_legacy
                FROM assets a
                LEFT JOIN plants p ON p.id = a.plant_id
                LEFT JOIN areas  ar ON ar.id = a.area_id
                WHERE a.tag = %s
                """,
                (tag,),
            )
            rows = _rows_as_dicts(cur)
            return rows[0] if rows else None

    def latest_reading(self, tag: str) -> dict[str, Any] | None:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT measured_at, temperature_c, vibration_mm_s, current_a,
                       voltage_v, rpm, power_kw, quality_score
                FROM readings_clean
                WHERE asset_tag = %s
                ORDER BY measured_at DESC
                LIMIT 1
                """,
                (tag,),
            )
            rows = _rows_as_dicts(cur)
            return rows[0] if rows else None

    def readings_history(self, tag: str, hours: int = 24) -> list[dict[str, Any]]:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT measured_at, temperature_c, vibration_mm_s, current_a,
                       voltage_v, rpm, power_kw, quality_score
                FROM readings_clean
                WHERE asset_tag = %s
                  AND measured_at >= NOW() - (%s || ' hours')::interval
                ORDER BY measured_at ASC
                """,
                (tag, str(hours)),
            )
            return _rows_as_dicts(cur)

    def nameplate_history(self, tag: str) -> list[dict[str, Any]]:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT source_image, ocr_confidence, extracted_by, extracted_at "
                "FROM asset_nameplates WHERE tag = %s ORDER BY extracted_at DESC",
                (tag,),
            )
            return _rows_as_dicts(cur)

    def recent_executions(self, limit: int = 30) -> list[dict[str, Any]]:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT bot_name, started_at, finished_at, status, records_in, "
                "records_ok, records_failed, duration_ms "
                "FROM execution_logs ORDER BY started_at DESC LIMIT %s",
                (limit,),
            )
            return _rows_as_dicts(cur)
