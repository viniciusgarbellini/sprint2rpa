# LEIA-ME PRIMEIRO — Guia de entrega da Sprint 2

> Este arquivo é o ponto de partida. Não precisa do Claude Code para nada aqui:
> todos os passos são comandos que você roda no terminal da sua máquina.

## 1. Em que pé está o projeto

A Sprint 2 está **implementada e testada** (16/16 testes passando). Tudo o que o
professor pede em **código** já está pronto:

- 2 RPAs: extração da placa (imagem → cadastro) e associação Ativo-TAG-Localização;
- interface web (Streamlit) com login/papéis, navegação planta→área→ativo, busca
  por TAG, dashboards de sensores (tensão, corrente, temperatura, rotação, vibração)
  e séries temporais;
- migration idempotente do banco, auditoria (`execution_logs` / `access_logs`);
- documentação técnica completa em `docs/` e no `README.md`.

O repositório **git já está inicializado** com 1 commit na branch `main`.

## 2. O que FALTA fazer (só isto)

1. **Subir para um repositório GitHub PRIVADO** e adicionar o professor como colaborador.
2. **Gravar o vídeo** de demonstração (roteiro pronto em `docs/roteiro-video.md`).
3. (Recomendado) **Rodar uma vez na sua máquina** antes de gravar, para garantir
   que sobe certinho no seu ambiente.

---

## 3. Como rodar na sua máquina

### Caminho A — Docker (recomendado, mais simples)

Pré-requisitos: **Docker Desktop** instalado e aberto. Portas livres: 5432 e 8501.

```bash
# 1. copie o arquivo de ambiente
cp .env.example .env          # Windows PowerShell: copy .env.example .env

# 2. suba a stack (postgres + RPAs + dashboard)
docker compose up --build

# 3. em OUTRO terminal, popule os dados de demonstração
docker compose run --rm app python -m sprint2.main seed
```

Abra **http://localhost:8501** e entre com `operador / operador123` ou
`admin / admin123`.

### Caminho B — Sem Docker (Python local)

Pré-requisitos: **Python 3.12** e um **PostgreSQL** acessível (ajuste o `.env`
com host/usuário/senha do seu Postgres).

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt

# aponte o Python para a pasta src:
# Windows PowerShell:
$env:PYTHONPATH = "src"
# Linux/Mac:
export PYTHONPATH=src

python -m sprint2.main seed                       # cria schema + dados demo
streamlit run src/sprint2/app/streamlit_app.py    # abre a interface
```

> Importante: **NÃO existe `.venv` pronta nesta pasta** (foi removida de propósito,
> porque uma venv é amarrada à máquina de quem a criou). Crie a sua com o passo acima.

### Rodar os testes (opcional, prova que está tudo ok)

```bash
# com a venv ativada e PYTHONPATH=src:
pip install pytest
pytest
# devem passar 16 testes
```

---

## 4. Subir para o GitHub privado (entregável obrigatório)

O commit local já existe. Falta só criar o repo privado e dar push:

```bash
# Opção 1 — com GitHub CLI (gh) autenticado:
gh repo create sprint2-monitor --private --source=. --remote=origin --push

# Opção 2 — manual:
#   a) crie no github.com um repositório PRIVADO vazio (sem README)
#   b) então:
git remote add origin https://github.com/<SEU_USUARIO>/<REPO>.git
git push -u origin main
```

Depois, no GitHub: **Settings → Collaborators → Add people** e adicione o **professor**.

> Se o git reclamar de identidade ao commitar algo novo, configure:
> `git config user.name "Seu Nome"` e `git config user.email "seu@email.com"`.

---

## 5. Gravar o vídeo (entregável obrigatório)

Siga o roteiro pronto em **`docs/roteiro-video.md`** (4 a 6 min, com falas e
comandos). No fim dele há um checklist das evidências que precisam aparecer:
RPAs rodando, login com os 2 papéis, navegação, busca por TAG, dashboards e auditoria.

Coloque o link do vídeo no `README.md` ou na plataforma de entrega.

---

## 6. Mapa rápido do projeto (onde está cada coisa)

| O que | Onde |
|---|---|
| RPA da placa (imagem → cadastro) | `src/sprint2/nameplate/` |
| RPA de associação (TAG → planta/área) | `src/sprint2/association/bot.py` |
| Interface web | `src/sprint2/app/streamlit_app.py` |
| Login/papéis | `src/sprint2/app/auth.py` |
| Banco / migration | `db/migrations/001_sprint2.sql`, `src/sprint2/db.py` |
| Orquestrador (agenda as RPAs) | `src/sprint2/orchestrator.py` |
| Dados de demonstração | `src/sprint2/tools/` |
| Documentação técnica | `README.md` e `docs/` |

## 7. Checklist final de entrega

- [ ] Rodou na sua máquina (Docker ou local) e abriu a interface
- [ ] Repositório **privado** no GitHub com push feito
- [ ] **Professor** adicionado como colaborador
- [ ] **Vídeo** gravado e link incluído
- [ ] Documento técnico conferido (`README.md` + `docs/`)
