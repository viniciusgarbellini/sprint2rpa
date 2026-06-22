"""Configuração centralizada via variáveis de ambiente (12-factor app).

Reaproveita a mesma convenção da Sprint 1 (POSTGRES_*), de modo que a Sprint 2
conecta no MESMO banco — não duplica dado nem lógica de coleta.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Postgres (mesma instância da Sprint 1) ----------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "rpa_assets"
    postgres_user: str = "rpa"
    postgres_password: str = "rpa_secret_change_me"

    # Aplicação ---------------------------------------------------------------
    app_env: str = "development"
    log_level: str = "INFO"
    log_format: str = "json"

    # Caminhos das RPAs da Sprint 2 -------------------------------------------
    nameplate_drop_folder: Path = Path("./data/nameplates_drop")
    nameplate_archive_folder: Path = Path("./data/nameplates_archive")
    association_source: Path = Path("./data/associations/layout.csv")
    log_folder: Path = Path("./logs")

    # Agendamento (cron: m h dom mon dow) -------------------------------------
    schedule_nameplate_bot: str = "*/2 * * * *"
    schedule_association_bot: str = "*/3 * * * *"

    # Autenticação da interface ----------------------------------------------
    # Override opcional via env. Formato: "usuario:role:sha256hex,usuario2:..."
    # Vazio → sprint2.app.auth usa os usuários demo embutidos (ver auth.py).
    # Em produção: cofre de segredos, nunca senha em texto/código.
    auth_users: str = ""

    @property
    def db_dsn(self) -> str:
        return (
            f"host={self.postgres_host} port={self.postgres_port} "
            f"dbname={self.postgres_db} user={self.postgres_user} "
            f"password={self.postgres_password}"
        )


settings = Settings()
