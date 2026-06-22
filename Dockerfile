# Mesma versão do pyproject (requires-python >=3.12). Sem ambiguidade de versão.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY pyproject.toml ./
COPY src/ ./src/
COPY db/ ./db/
COPY tests/ ./tests/

# Pastas mutáveis (montadas como volume no compose; default garantido aqui).
RUN mkdir -p /app/data/nameplates_drop /app/data/nameplates_archive \
             /app/data/associations /app/logs

# Orquestrador das RPAs por padrão (o serviço dashboard sobrescreve o command).
CMD ["python", "-m", "sprint2.main", "run"]
