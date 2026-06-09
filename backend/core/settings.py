# backend/core/settings.py
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> str:
    """Retourne le chemin du fichier .env selon APP_ENV."""
    return os.getenv("APP_ENV", ".env")


class Settings(BaseSettings):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    postgres_host: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_ssl: str

    redis_host: str
    redis_port: int = 6379
    redis_url: str

    upload_temp_dir: str = "/tmp"

    url_salesforce_cpu_large: str
    url_florance_2_large: str
    url_git_large: str
    batch_size: int = 5
    batch_max: int = 200

    fastapi_url: str
    vps_host: str = ""
    debug: bool

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    # env_file passé dynamiquement pour respecter APP_ENV au moment de l'appel
    return Settings(_env_file=_env_file())


settings = get_settings()
