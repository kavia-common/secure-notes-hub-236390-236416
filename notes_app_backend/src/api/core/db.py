from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.core.settings import get_settings


def _to_async_db_url(url: str) -> str:
    """
    Convert a SQLAlchemy/Postgres URL into an asyncpg URL if needed.

    Accepts:
      - postgresql://...
      - postgres://...
      - postgresql+asyncpg://...
    """
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


_settings = get_settings()
if not _settings.postgres_url:
    # Keep engine creation lazy-ish (but defined) so import-time doesn't crash tests that don't set env.
    # Actual requests will fail with a clear 500 if DB URL is missing.
    _engine: AsyncEngine | None = None
    _SessionLocal: async_sessionmaker[AsyncSession] | None = None
else:
    _engine = create_async_engine(_to_async_db_url(_settings.postgres_url), pool_pre_ping=True)
    _SessionLocal = async_sessionmaker(bind=_engine, expire_on_commit=False)


# PUBLIC_INTERFACE
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession."""
    if _SessionLocal is None:
        raise RuntimeError(
            "Database is not configured. Please set POSTGRES_URL in the backend environment."
        )
    async with _SessionLocal() as session:
        yield session
