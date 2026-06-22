# Roteiro do vídeo de demonstração — Sprint 2

Duração alvo: **4 a 6 minutos**. Grave a tela (OBS, ShareX ou a gravação do
Windows `Win+G`). Tenha dois terminais abertos e o navegador.

## Preparação (antes de gravar)
1. `docker compose up --build` e aguarde os 3 contêineres subirem.
2. **Não** rode o `seed` ainda — vamos mostrar as RPAs criando os dados ao vivo.
3. Deixe abertos: Terminal A (comandos), Terminal B (`docker compose logs -f app`),
   navegador em `http://localhost:8501`.

## Roteiro (fala + ação)

### 0:00 — Abertura (30s)
> "Esta é a Sprint 2 do nosso Digital Twin de motores. Ela reaproveita o banco da
> Sprint 1 e adiciona: navegação pela planta, duas automações RPA — extração da
> placa do motor e associação Ativo-TAG-Localização — e uma interface operacional
> com login."

Mostre rapidamente a estrutura de pastas (`src/sprint2/...`) e o diagrama do
`docs/arquitetura-sprint2.md`.

### 0:30 — RPA de extração da placa (90s)
No Terminal A:
```bash
docker compose run --rm app python -m sprint2.tools.gen_nameplates
```
> "Geramos imagens de placa de motor. Cada PNG é uma imagem real."

Abra uma das imagens em `data/nameplates_drop/` e mostre os campos da placa.

```bash
docker compose run --rm app python -m sprint2.main once nameplate
```
> "A RPA varre a pasta, lê a imagem, extrai TAG, fabricante, potência, tensão,
> corrente e rotação, e **preenche o cadastro automaticamente**. A imagem
> processada vai para o archive e a execução fica auditada."

Mostre no Terminal B o log (`status=SUCCESS`, `novos=...`).

### 2:00 — RPA de associação Ativo-TAG-Localização (60s)
```bash
docker compose run --rm app python -m sprint2.main once associate
```
> "Esta RPA lê o layout da planta e vincula cada TAG à sua planta e área —
> criando a hierarquia de navegação, sem digitação manual. Rodar de novo não
> duplica nada: é idempotente."

(Opcional) abra `data/associations/layout.csv` e mostre o formato.

### 3:00 — Popular histórico para os gráficos (20s)
```bash
docker compose run --rm app python -m sprint2.main seed
```
> "O seed também injeta um histórico de leituras para os dashboards terem o que
> mostrar." (Em produção, esse histórico vem dos bots de coleta da Sprint 1.)

### 3:20 — Interface: login e controle de acesso (40s)
No navegador, entre como **operador / operador123**.
> "A interface exige login. Cada acesso e cada consulta ficam registrados em
> `access_logs` — rastreabilidade e controle de acesso."

### 4:00 — Navegação pela planta (40s)
Na barra lateral, modo **Navegar pela planta**: escolha Planta → Área → Ativo.
> "Navego pela hierarquia: planta, área e o motor específico. Aqui está a
> localização do ativo e seus dados de placa."

### 4:40 — Busca por TAG + dashboards (50s)
Troque para **Buscar por TAG**, digite `MTR-0`.
> "Posso localizar o equipamento direto pela TAG."

No detalhe do ativo, destaque:
- os **valores atuais** dos 5 sensores (tensão, corrente, temperatura, rotação, vibração);
- as **séries temporais** (gráficos das últimas 24h);
- os **dados de placa** e a proveniência da extração.

### 5:30 — Admin dispara RPA + auditoria (30s)
Saia e entre como **admin / admin123**. No painel "Automação (RPA)", clique em
**Rodar RPA de placa**. Abra a seção **Auditoria** e mostre `execution_logs` e
`access_logs`.
> "O papel admin pode disparar as automações pela própria interface, e tudo fica
> auditado."

### 6:00 — Fechamento (15s)
> "Resumindo: RPAs autônomas e idempotentes mantêm o cadastro e a associação
> Ativo-TAG-Localização consistentes; a interface entrega navegação e dashboards
> com controle de acesso. Tudo conectado ao mesmo banco da Sprint 1."

## Checklist de evidências a aparecer no vídeo
- [ ] RPA de placa criando/atualizando cadastro (log + interface).
- [ ] RPA de associação vinculando TAG → planta/área.
- [ ] Login com os dois papéis (operador e admin).
- [ ] Navegação planta → área → ativo **e** busca por TAG.
- [ ] Valores atuais dos 5 sensores + gráficos temporais.
- [ ] Auditoria (`execution_logs` e `access_logs`).
