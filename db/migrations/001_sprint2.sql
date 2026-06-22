-- =============================================================================
-- Migration 001 — Sprint 2: Visualização Operacional e Representação do Ativo
-- =============================================================================
-- Esta migration ESTENDE o schema da Sprint 1 (rpa-cs). Ela NÃO recria as
-- tabelas da Sprint 1 (assets, readings_clean, execution_logs, etc.) — apenas
-- adiciona o que é novo nesta sprint:
--
--   1. Hierarquia de navegação da planta: plants → areas → assets
--   2. Vínculo Ativo ↔ Localização (plant_id / area_id em assets)
--   3. Rastreio da extração da placa do motor (asset_nameplates)
--   4. Controle de acesso / auditoria de consultas (access_logs)
--   5. Views de apoio à navegação e à associação Ativo-TAG-Localização
--
-- Toda a migration é IDEMPOTENTE (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS),
-- então pode ser aplicada várias vezes sem efeito colateral.
--
-- Compatibilidade: se as tabelas-base da Sprint 1 ainda não existirem (ex.:
-- avaliar a Sprint 2 isoladamente), os CREATE TABLE IF NOT EXISTS de plants/
-- areas/access_logs funcionam mesmo assim. As referências a assets/readings_clean
-- são resolvidas pelo seed (tools/seed_demo.py) ou pela stack da Sprint 1.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. Garantia mínima das tabelas-base que a Sprint 2 referencia.
--    (No-op quando a Sprint 1 já criou. Mantém a Sprint 2 executável sozinha.)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assets (
    id              SERIAL          PRIMARY KEY,
    tag             VARCHAR(50)     UNIQUE NOT NULL,
    name            VARCHAR(200)    NOT NULL,
    manufacturer    VARCHAR(100),
    model           VARCHAR(100),
    rated_power_kw  NUMERIC(10,2),
    rated_voltage_v NUMERIC(10,2),
    rated_current_a NUMERIC(10,2),
    rated_rpm       INTEGER,
    location        VARCHAR(200),
    installation_date DATE,
    status          VARCHAR(20)     NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE','INACTIVE','MAINTENANCE')),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- readings_raw / readings_clean: camadas bronze/silver da Sprint 1. A interface
-- da Sprint 2 LÊ readings_clean para os dashboards. Recriadas aqui só por
-- garantia (no-op quando a Sprint 1 já criou).
CREATE TABLE IF NOT EXISTS readings_raw (
    id              BIGSERIAL       PRIMARY KEY,
    asset_tag       VARCHAR(50)     NOT NULL,
    source          VARCHAR(50)     NOT NULL,
    source_id       VARCHAR(200)    NOT NULL,
    payload         JSONB           NOT NULL,
    received_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    run_id          UUID            NOT NULL,
    UNIQUE (source, source_id)
);

CREATE TABLE IF NOT EXISTS readings_clean (
    id              BIGSERIAL       PRIMARY KEY,
    raw_id          BIGINT          NOT NULL REFERENCES readings_raw(id) ON DELETE CASCADE,
    asset_id        INTEGER         REFERENCES assets(id),
    asset_tag       VARCHAR(50)     NOT NULL,
    measured_at     TIMESTAMPTZ     NOT NULL,
    temperature_c   NUMERIC(8,2),
    vibration_mm_s  NUMERIC(8,2),
    current_a       NUMERIC(8,2),
    voltage_v       NUMERIC(8,2),
    rpm             INTEGER,
    power_kw        NUMERIC(10,2),
    quality_score   NUMERIC(3,2)    CHECK (quality_score BETWEEN 0 AND 1),
    flags           JSONB           DEFAULT '{}'::jsonb,
    processed_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (raw_id)
);

CREATE INDEX IF NOT EXISTS idx_clean_tag_time ON readings_clean(asset_tag, measured_at DESC);

-- execution_logs: auditoria das automações RPA, COMPARTILHADA entre Sprint 1 e 2.
-- Manter uma única tabela de auditoria mantém a rastreabilidade consistente.
CREATE TABLE IF NOT EXISTS execution_logs (
    id              BIGSERIAL       PRIMARY KEY,
    run_id          UUID            UNIQUE NOT NULL,
    bot_name        VARCHAR(50)     NOT NULL,
    started_at      TIMESTAMPTZ     NOT NULL,
    finished_at     TIMESTAMPTZ,
    status          VARCHAR(20)     NOT NULL
                    CHECK (status IN ('RUNNING','SUCCESS','FAILED','PARTIAL')),
    records_in      INTEGER         NOT NULL DEFAULT 0,
    records_ok      INTEGER         NOT NULL DEFAULT 0,
    records_failed  INTEGER         NOT NULL DEFAULT 0,
    duration_ms     INTEGER,
    error_message   TEXT,
    metadata        JSONB           DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_exec_logs_bot_time ON execution_logs(bot_name, started_at DESC);

-- -----------------------------------------------------------------------------
-- 1. plants — Plantas industriais (topo da hierarquia de navegação)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plants (
    id          SERIAL          PRIMARY KEY,
    code        VARCHAR(30)     UNIQUE NOT NULL,   -- ex.: 'PLT-SP'
    name        VARCHAR(200)    NOT NULL,          -- ex.: 'Planta São Paulo'
    city        VARCHAR(120),
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 2. areas — Áreas/setores dentro de uma planta (nível intermediário)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS areas (
    id          SERIAL          PRIMARY KEY,
    plant_id    INTEGER         NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
    code        VARCHAR(30)     NOT NULL,          -- ex.: 'A-BOMBAS'
    name        VARCHAR(200)    NOT NULL,          -- ex.: 'Bombeamento'
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (plant_id, code)
);

CREATE INDEX IF NOT EXISTS idx_areas_plant ON areas(plant_id);

-- -----------------------------------------------------------------------------
-- 3. assets — vínculo com a localização hierárquica
--    Mantém a coluna legada `location` (texto livre da Sprint 1) e adiciona
--    o vínculo estruturado plant_id / area_id usado na navegação.
-- -----------------------------------------------------------------------------
ALTER TABLE assets ADD COLUMN IF NOT EXISTS plant_id INTEGER REFERENCES plants(id);
ALTER TABLE assets ADD COLUMN IF NOT EXISTS area_id  INTEGER REFERENCES areas(id);

CREATE INDEX IF NOT EXISTS idx_assets_plant ON assets(plant_id);
CREATE INDEX IF NOT EXISTS idx_assets_area  ON assets(area_id);

-- -----------------------------------------------------------------------------
-- 4. asset_nameplates — Rastreio da extração da placa do motor (provenance)
--    Cada execução da RPA de placa registra aqui de onde vieram os dados que
--    preencheram o cadastro (imagem de origem, texto "OCR", campos extraídos,
--    confiança e quem/o quê executou). Atende rastreabilidade + Digital Twin.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS asset_nameplates (
    id              BIGSERIAL       PRIMARY KEY,
    asset_id        INTEGER         REFERENCES assets(id) ON DELETE CASCADE,
    tag             VARCHAR(50)     NOT NULL,
    source_image    VARCHAR(300)    NOT NULL,      -- caminho/nome da imagem da placa
    ocr_text        TEXT,                          -- texto lido da imagem (OCR)
    extracted       JSONB           NOT NULL,      -- campos estruturados extraídos
    ocr_confidence  NUMERIC(3,2)    CHECK (ocr_confidence BETWEEN 0 AND 1),
    extracted_by    VARCHAR(100)    NOT NULL DEFAULT 'nameplate_bot',
    extracted_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nameplates_tag ON asset_nameplates(tag, extracted_at DESC);

-- -----------------------------------------------------------------------------
-- 5. access_logs — Auditoria de acesso/consulta (controle de acesso)
--    Registra login e consultas operacionais na interface. Atende o requisito
--    não-funcional "rastreabilidade e controle no acesso às informações".
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS access_logs (
    id          BIGSERIAL       PRIMARY KEY,
    username    VARCHAR(100)    NOT NULL,
    role        VARCHAR(30)     NOT NULL,
    action      VARCHAR(60)     NOT NULL,          -- LOGIN | LOGIN_FAIL | VIEW_ASSET | SEARCH_TAG | RUN_RPA
    target      VARCHAR(200),                      -- ex.: TAG consultada
    at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_access_logs_at ON access_logs(at DESC);

-- -----------------------------------------------------------------------------
-- 6. View: v_asset_location — Mapeamento Ativo ↔ TAG ↔ Localização
--    Núcleo da consistência exigida na avaliação: uma linha por ativo com sua
--    TAG e sua localização hierárquica resolvida (planta + área).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_asset_location AS
SELECT
    a.id                AS asset_id,
    a.tag,
    a.name,
    a.status,
    p.id                AS plant_id,
    p.code              AS plant_code,
    p.name              AS plant_name,
    ar.id               AS area_id,
    ar.code             AS area_code,
    ar.name             AS area_name,
    a.location          AS location_legacy
FROM assets a
LEFT JOIN plants p ON p.id = a.plant_id
LEFT JOIN areas  ar ON ar.id = a.area_id;

-- -----------------------------------------------------------------------------
-- 7. View: v_navigation — Contagem de ativos por planta/área (árvore de navegação)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_navigation AS
SELECT
    p.id    AS plant_id,
    p.code  AS plant_code,
    p.name  AS plant_name,
    ar.id   AS area_id,
    ar.code AS area_code,
    ar.name AS area_name,
    COUNT(a.id) AS asset_count
FROM plants p
LEFT JOIN areas  ar ON ar.plant_id = p.id
LEFT JOIN assets a  ON a.area_id = ar.id
GROUP BY p.id, p.code, p.name, ar.id, ar.code, ar.name
ORDER BY p.name, ar.name;
