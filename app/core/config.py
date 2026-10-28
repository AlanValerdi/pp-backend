from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SOURCE_URL = "http://webserver.siiaa.siu.buap.mx/serv_social/SS_ALUM_AUTSV_OFERTA_C"
SCHEMA_VERSION = 1
CAREERS_PATH = "ss_oferta_ss?se=ABE63459925DAD50"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://pp:pp@localhost:5432/pp"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    admin_api_key: str = ""
    siiaa_base_url: str = "http://webserver.siiaa.siu.buap.mx/serv_social/"
    scrape_concurrency: int = Field(default=4, ge=1)
    scrape_timeout_seconds: float = Field(default=60, gt=0)
    scrape_delay_seconds: float = Field(default=0.25, ge=0)
    log_level: str = "INFO"

    # Inicio de sesión con Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = (
        "http://localhost:3000/api/backend/auth/google/callback"
    )

    # Transacción temporal de OAuth
    oauth_session_secret: str = ""

    # Sesión de nuestra aplicación
    frontend_url: str = "http://localhost:3000"
    session_ttl_seconds: int = Field(default=600, gt=0)
    cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
