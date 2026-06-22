# Sprint 2 — Visualização Operacional e Representação do Ativo

**Vídeo de demonstração:** https://www.youtube.com/watch?v=y8mZN0_Phh4

> Continuação do projeto de Digital Twin de motores elétricos industriais.
> A Sprint 1 (repositório **rpa-cs**) estabeleceu a coleta/normalização/persistência
> dos dados. **Esta Sprint 2 entrega apenas os módulos novos**: a navegação pela
> planta, as RPAs de associação **Ativo-TAG-Localização** e de **extração da placa
> do motor**, e a interface operacional de consulta com controle de acesso.

---

## O que é novo nesta sprint (em uma frase)

Duas **RPAs** (placa do motor → cadastro; layout → associação TAG/localização)
mantêm o cadastro consistente **sem digitação manual repetitiva**, e uma
**interface com login** permite navegar pela planta, localizar o motor pela TAG e
acompanhar seus sensores (tensão, corrente, temperatura, rotação, vibração) em
tempo quase real e em séries temporais.

---

## Como esta sprint se conecta à Sprint 1

A Sprint 2 **não recopia** os bots de coleta nem o normalizador da Sprint 1.
Ela conecta no **mesmo PostgreSQL** e o estende via *migration* (`db/migrations/`):

- **Reusa** as tabelas `assets`, `readings_clean` e `execution_logs` da Sprint 1.
- **Adiciona** `plants`, `areas`, `asset_nameplates`, `access_logs` e o vínculo
  `assets.plant_id / area_id`, além das views `v_asset_location` e `v_navigation`.

A migration é **idempotente** e tem uma seção de "garantia mínima" das tabelas-base
(`CREATE TABLE IF NOT EXISTS`), de modo que a Sprint 2 também **roda isolada** —
útil para a avaliação e a gravação do vídeo sem precisar subir toda a Sprint 1.

> **Correção do feedback da Sprint 1** (ambiguidade de versão / módulos antigos):
> aqui a versão do Python é **única e explícita (3.12)** em `pyproject.toml` e no
> `Dockerfile`, com **estrutura de módulos moderna** (src-layout, `collections.abc`,
> tipagem `X | None`, sem `from __future__ import annotations`).

---

## Mapeamento Requisito → Implementação

| Requisito do enunciado | Onde está |
|---|---|
| **Estrutura de navegação** (planta / área / ativo) | `plants`→`areas`→`assets` + view `v_navigation`; sidebar em `app/streamlit_app.py` |
| **Associação automatizada (RPA)** Ativo-TAG-Localização | `src/sprint2/association/bot.py` (lê layout, upsert planta/área, vincula TAG) |
| **Integração de dados da placa** (imagem → cadastro) | `src/sprint2/nameplate/` (`extractor.py` + `bot.py`); doc em `docs/pipeline-placa-cadastro.md` |
| **Localizar equipamento pela TAG** | busca `search_by_tag` (view `v_asset_location`) na interface |
| **Métricas de sensores em dashboards** (tensão, corrente, temperatura, rotação, vibração) | `render_asset` — `st.metric` + gráficos Plotly de séries temporais |
| **Visualização de dados atuais + histórico** | `latest_reading` + `readings_history` sobre `readings_clean` |
| **Atualização sem input manual repetitivo** | RPAs idempotentes agendadas por cron (`src/sprint2/orchestrator.py`) |
| **Controle de acesso + rastreabilidade** | login com papéis (`app/auth.py`) + `access_logs` + `execution_logs` |
| **Estrutura preparada para ML** | ver [§ Preparado para ML](#preparado-para-ml-futuro) |
| Repositório GitHub privado | (configurar no GitHub — ver § Entrega) |

---

## Stack

| Camada | Tecnologia | Por quê |
|---|---|---|
| Linguagem | **Python 3.12** | versão única, alinhada ao Docker |
| Validação | Pydantic 2 | contratos na fronteira (placa, layout) |
| Imagem/“OCR” | Pillow (PIL) | gera a placa e lê o texto da imagem |
| Persistência | PostgreSQL 16 | mesma base da Sprint 1 (consistência) |
| Driver | psycopg 3 | tipado, retry com Tenacity |
| Agendamento | APScheduler | cron Pythonic para as RPAs |
| Interface | Streamlit + Plotly | navegação + dashboards rápidos |
| Logging | Loguru | JSON estruturado, auditável |
| Containers | Docker + Compose | reprodutibilidade |
| Testes | pytest | parser da placa, modelos, auth |

---

## Estrutura do repositório

```
SPRINT 2/
├── pyproject.toml              ← packaging moderno (src-layout) + config pytest
├── requirements.txt            ← versões fixas (lock) para Docker
├── docker-compose.yml          ← postgres + app (RPA) + dashboard
├── Dockerfile                  ← imagem Python 3.12
├── .env.example
├── db/migrations/001_sprint2.sql   ← estende o schema da Sprint 1
├── src/sprint2/
│   ├── config.py · logger.py · db.py · models.py · repository.py
│   ├── orchestrator.py · main.py
│   ├── nameplate/   extractor.py (pipeline placa→texto→campos) · bot.py
│   ├── association/ bot.py (Ativo ↔ TAG ↔ Localização)
│   ├── app/         streamlit_app.py (navegação/consulta) · auth.py (login+papéis)
│   └── tools/       gen_nameplates.py (gera placas) · seed_demo.py
├── data/
│   ├── nameplates_drop/      ← a RPA de placa vigia esta pasta
│   ├── nameplates_archive/   ← placas já processadas
│   └── associations/         ← layout.csv (TAG → planta/área)
├── tests/          test_extractor.py · test_models.py · test_auth.py
└── docs/
    ├── arquitetura-sprint2.md
    ├── mapeamento-ativo-tag-localizacao.md
    └── pipeline-placa-cadastro.md
```

---

## Como rodar

### Pré-requisitos
- **Docker Desktop** (ou Docker + Compose v2).
- Portas livres: **5432** (Postgres) e **8501** (interface).

### 1. Configurar
```bash
cp .env.example .env
```

### 2. Subir a stack
```bash
docker compose up --build
```
Sobem três serviços: `sprint2_postgres`, `sprint2_app` (orquestrador das RPAs,
que aplica as migrations e roda um warm-up dos dois bots) e `sprint2_dashboard`.

### 3. Popular os dados de demonstração (gera placas, layout, roda as RPAs e cria histórico)
Em outro terminal:
```bash
docker compose run --rm app python -m sprint2.main seed
```

### 4. Abrir a interface
http://localhost:8501 — entre com **operador / operador123** ou **admin / admin123**.

> Sem Docker? Veja `docs/arquitetura-sprint2.md` (§ execução local com venv).

---

## Demonstrar as RPAs ao vivo (sem o seed)

**RPA de placa** — copie uma imagem de placa para a pasta vigiada e rode o bot:
```bash
docker compose run --rm app python -m sprint2.tools.gen_nameplates   # gera placas em data/nameplates_drop
docker compose run --rm app python -m sprint2.main once nameplate    # extrai → cadastro
```

**RPA de associação** — com o `data/associations/layout.csv` presente:
```bash
docker compose run --rm app python -m sprint2.main once associate    # vincula TAG → planta/área
```

No modo `run` (default do serviço `app`), ambas executam sozinhas por cron
(`*/2` e `*/3` min) — basta soltar arquivos nas pastas.

---

## Testes
```bash
docker compose run --rm app pytest
```
Cobrem: parsing da placa (com ruído de OCR, conversão cv→kW, roundtrip
imagem→extração), validação dos modelos e autenticação.

---

## Preparado para ML (futuro)

- `readings_clean` (com `quality_score` e `flags`) já é uma base limpa,
  rotulável, pronta para alimentar detecção de anomalia/manutenção preditiva.
- `asset_nameplates` guarda a **proveniência** da extração (imagem, texto, confiança),
  permitindo treinar/avaliar um OCR real depois sem perder rastreabilidade.
- O ponto de troca para **OCR de produção** é uma única função
  (`extractor._ocr_image`) — ver `docs/pipeline-placa-cadastro.md`.

---
## Entrega (requisitos não-funcionais)

- **Repositório GitHub**: https://github.com/viniciusgarbellini/sprint2rpa
- **Vídeo de demonstração**: https://www.youtube.com/watch?v=y8mZN0_Phh4

---

## Licença
Projeto acadêmico — uso livre para fins educacionais.
