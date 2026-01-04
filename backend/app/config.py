"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="ai_email_app")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    worker_port: int = Field(default=8001)
    log_level: str = Field(default="info")

    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="ai_email_app")

    database_url: str | None = Field(default=None)

    google_oauth_client_id: str = Field(default="")
    google_oauth_client_secret: str = Field(default="")
    google_oauth_redirect_uri: str = Field(default="")
    session_jwt_secret: str = Field(default="")
    encryption_key: str = Field(default="")
    web_base_url: str = Field(default="http://localhost:3000")
    api_base_url: str = Field(default="http://localhost:8000")
    session_cookie_name: str = Field(default="session")
    session_cookie_secure: bool = Field(default=False)
    session_ttl_days: int = Field(default=7)
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-5.2")

    def resolved_database_url(self) -> str:
        """Return a SQLAlchemy-compatible database URL."""
        if self.database_url:
            return self.database_url
        return (
            "postgresql+psycopg2://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
