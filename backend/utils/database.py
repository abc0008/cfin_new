import os
import sqlite3
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

# Import sqlite3 error classes for aiosqlite
import aiosqlite
aiosqlite.DatabaseError = sqlite3.DatabaseError
aiosqlite.Error = sqlite3.Error

def _postgres_to_asyncpg_url(url: str) -> str:
    """Convert Supabase/Postgres URLs into a SQLAlchemy asyncpg URL."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        # asyncpg expects ssl=require; Supabase pooler URLs commonly use sslmode=require.
        if key == "sslmode":
            query.append(("ssl", value))
        else:
            query.append((key, value))

    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _postgres_to_sync_url(url: str) -> str:
    """Convert configured URLs into a psycopg2-compatible SQLAlchemy URL."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    elif url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)

    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key == "ssl":
            query.append(("sslmode", value))
        else:
            query.append((key, value))

    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


# Get the database URL from environment variables
RAW_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fdas.db")
DATABASE_URL = RAW_DATABASE_URL

# Convert database URLs to work with SQLAlchemy asynchronous engines.
if DATABASE_URL.startswith("sqlite"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
elif DATABASE_URL.startswith(("postgres://", "postgresql://", "postgresql+psycopg2://", "postgresql+asyncpg://")):
    DATABASE_URL = _postgres_to_asyncpg_url(DATABASE_URL)

# Create async engine
engine_kwargs = {
    "echo": True if os.getenv("DEBUG") == "True" else False,
    "future": True,
}

if DATABASE_URL.startswith("postgresql+asyncpg"):
    # Supabase recommends avoiding a second SQLAlchemy pool when using its pooler,
    # which is also the right shape for serverless Vercel functions.
    engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(DATABASE_URL, **engine_kwargs)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Alias for backward compatibility
AsyncSessionLocal = SessionLocal

# Create Base class for models
Base = declarative_base()

# Dependency to get database session
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()

# For non-async operations
sync_engine = None
SyncSessionLocal = None

if DATABASE_URL.startswith("sqlite+aiosqlite"):
    # Create sync engine for SQLite
    sync_url = DATABASE_URL.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
    sync_engine = create_engine(sync_url, connect_args={"check_same_thread": False})
    SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
else:
    # For PostgreSQL or other databases
    sync_url = _postgres_to_sync_url(DATABASE_URL)
    sync_engine = create_engine(sync_url)
    SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
