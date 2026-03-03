from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Note: Do not hard-code secrets. Provide values via the container .env.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    postgres_url: str = Field(
        default="",
        alias="POSTGRES_URL",
        description="PostgreSQL connection string. Example: postgresql://user:pass@host:port/db",
    )

    # Security / JWT
    jwt_secret_key: str = Field(
        default="",
        alias="JWT_SECRET_KEY",
        description="Secret used to sign JWT access tokens (HS256). MUST be set in production.",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        alias="JWT_ALGORITHM",
        description="JWT signing algorithm. Default HS256.",
    )
    access_token_expire_minutes: int = Field(
        default=60 * 24 * 7,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
        description="Access token lifetime in minutes. Default 7 days.",
    )

    # CORS
    cors_allow_origins: str = Field(
        default="",
        alias="CORS_ALLOW_ORIGINS",
        description=(
            "Comma-separated list of allowed origins (e.g. https://example.com,http://localhost:3000). "
            "If empty, backend will default to allowing http://localhost:3000."
        ),
    )

    # Environment
    environment: str = Field(
        default="development",
        alias="ENVIRONMENT",
        description="Environment name (development/staging/production).",
    )


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return Settings instance (env-backed)."""
    return Settings()
