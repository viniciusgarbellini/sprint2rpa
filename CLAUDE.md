# CLAUDE.md

Contexto do projeto para assistentes de IA (Claude Code). Leia também `HANDOFF.md`
(guia de entrega para humano) e `README.md` (documentação completa).

## O que é este projeto

**Sprint 2 — Visualização Operacional e Representação do Ativo**: continuação de um
projeto acadêmico de *Digital Twin* de motores elétricos industriais. A Sprint 1
(repositório `rpa-cs`) cuidou da coleta/normalização/persistência de leituras. Esta
Sprint 2 **estende a mesma base** e entrega: duas automações RPA, uma interface
operacional e a documentação técnica.

O projeto está **completo e testado** (16/16 testes). O que falta é **entrega**, não
código: subir num GitHub privado e gravar o vídeo de demonstração (ver `HANDOFF.md`).
Não inventar features além do enunciado.

## Arquitetura (alto nível)

```
Imagens de placa  ─►  NameplateBot  ─►┐
(data/nameplates_drop)                 ├─►  PostgreSQL  ─►  Interface Streamlit
Layout CSV        ─►  AssociationBot ─►┘   (assets, plants,    (login, navegação,
(data/associations)                         areas, readings,    busca por TAG,
                                            logs, views)        dashboards)
```

- **NameplateBot** (`src/sprint2/nameplate/`): varre a pasta de drop, extrai dados da
  placa (imagem → texto → regex → `NameplateData`) e preenche o cadastro do ativo.
  A etapa imagem→texto (`extractor._ocr_image`) é **simulada de propósito** (lê texto
  embutido nos metadados PNG); é o único ponto de troca para OCR real.
- **AssociationBot** (`src/sprint2/association/bot.py`): lê o CSV de layout e vincula
  cada TAG à sua planta/área (idempotente: LINKED / UNCHANGED / NO_ASSET).
- **Orquestrador** (`src/sprint2/orchestrator.py`): agenda as duas RPAs via APScheduler.
- **Interface** (`src/sprint2/app/streamlit_app.py`): login com papéis (`auth.py`),
  navegação planta→área→ativo, busca por TAG, métricas atuais + gráficos Plotly,
  painel admin para disparar RPAs, auditoria.

## Estrutura de pastas

| Caminho | Conteúdo |
|---|---|
| `src/sprint2/` | código-fonte (src-layout; pacote `sprint2`) |
| `src/sprint2/nameplate/`, `association/` | as duas RPAs |
| `src/sprint2/app/` | interface Streamlit + autenticação |
| `src/sprint2/tools/` | geradores de demo (`gen_nameplates.py`, `seed_demo.py`) |
| `db/migrations/001_sprint2.sql` | schema (idempotente, estende a Sprint 1) |
| `tests/` | pytest (parser de placa, modelos, auth — não precisam de banco) |
| `docs/` | documentação técnica (arquitetura, mapeamento, pipeline, roteiro do vídeo) |
| `data/` | pastas vigiadas pelas RPAs (drop/archive/associations) |

## Como rodar (resumo)

- **Com Docker** (preferido): `docker compose up --build`; depois
  `docker compose run --rm app python -m sprint2.main seed`; interface em
  http://localhost:8501 (`operador/operador123` ou `admin/admin123`).
- **Local**: Python 3.12, `pip install -r requirements.txt`, `PYTHONPATH=src`,
  `python -m sprint2.main seed`, `streamlit run src/sprint2/app/streamlit_app.py`.
  É preciso um PostgreSQL acessível (ajustar `.env`).
- **Entrypoint CLI**: `python -m sprint2.main {init|seed|run|once nameplate|once associate}`.

## Testes

```bash
PYTHONPATH=src pytest        # 16 testes, sem dependência de banco
```

## Convenções e decisões (respeitar ao editar)

- **Python 3.12 único** (resolve feedback da Sprint 1 sobre ambiguidade de versão).
  Tipagem moderna: `X | None`, `collections.abc`, **sem** `from __future__ import annotations`.
- **src-layout**: o pacote vive em `src/sprint2`; sempre rodar com `PYTHONPATH=src`.
- **Estender, não duplicar**: a Sprint 2 não reescreve a coleta da Sprint 1; a migration
  é idempotente (`IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` / `ON CONFLICT`).
- **RPAs idempotentes**: rodar de novo não duplica nem corrompe dados.
- **Auditoria unificada**: as RPAs gravam em `execution_logs`; acessos em `access_logs`.
- **Pydantic v2** valida os contratos na fronteira (`src/sprint2/models.py`).
- **Configuração por env** (`src/sprint2/config.py`, lê `.env`). Não commitar `.env`.
- **Não há `.venv` no repo** de propósito (é amarrada à máquina). Criar a própria.

## Dependências principais

psycopg 3, Pydantic 2 + pydantic-settings, Loguru, APScheduler, pandas, Pillow,
Streamlit, Plotly, Tenacity, pytest. Versões fixas em `requirements.txt`.
