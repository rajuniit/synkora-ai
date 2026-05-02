"""
Database connection and session management.

This module provides SQLAlchemy database engine and session management
with connection pooling and proper lifecycle handling.

Supports both sync (psycopg2) and async (asyncpg) engines.
Sync engine is used by Celery tasks and legacy code paths.
Async engine is used by FastAPI controllers and hot-path services.
"""

from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from src.config import settings

# Naming convention for PostgreSQL indexes
POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

# Create metadata with naming convention
metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)

# Create declarative base for models
Base = declarative_base(metadata=metadata)


def create_db_engine() -> Engine:
    """
    Create SQLAlchemy database engine with connection pooling.

    Returns:
        Engine: Configured SQLAlchemy engine

    Note:
        Uses QueuePool for production and NullPool for testing.
        Connection pooling parameters are configured via settings.
    """
    pool_class = NullPool if settings.app_env == "test" else QueuePool

    # Build engine kwargs based on pool class
    engine_kwargs = {
        "poolclass": pool_class,
        "echo": settings.sqlalchemy_echo,  # Log SQL based on config
        "future": True,  # Use SQLAlchemy 2.0 style
    }

    # Only add pool parameters for QueuePool
    if pool_class == QueuePool:
        engine_kwargs.update(settings.sqlalchemy_engine_options)

    engine = create_engine(settings.sqlalchemy_database_uri, **engine_kwargs)

    # Add event listeners for connection management
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, _connection_record) -> None:  # type: ignore
        """Set connection parameters on connect."""
        # Set statement timeout to prevent long-running queries
        with dbapi_conn.cursor() as cursor:
            cursor.execute("SET statement_timeout = '30s'")

    return engine


# Create global engine instance
engine = create_db_engine()

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Async engine and session factory (asyncpg)
# ---------------------------------------------------------------------------

# Lazy-initialized async engine and session factory
# These are created on first use to ensure they're created in the correct event loop
_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_async_db_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy database engine with connection pooling.

    Returns:
        AsyncEngine: Configured async SQLAlchemy engine

    Note:
        Async engines use the internal AsyncAdaptedQueuePool automatically.
        NullPool is used for testing to avoid connection pooling issues.
    """
    # For async engines, we don't specify a pool class unless using NullPool
    # SQLAlchemy automatically uses AsyncAdaptedQueuePool for async engines
    engine_kwargs: dict = {
        "echo": settings.sqlalchemy_echo,
    }

    if settings.app_env == "test":
        engine_kwargs["poolclass"] = NullPool
    else:
        # Add pool parameters (SQLAlchemy will use AsyncAdaptedQueuePool internally)
        async_options = settings.sqlalchemy_async_engine_options.copy()
        # Remove connect_args that might cause issues and handle separately
        connect_args = async_options.pop("connect_args", {})
        engine_kwargs.update(async_options)
        # Merge server_settings to set per-statement timeout via asyncpg session params.
        # statement_timeout value must be a string in milliseconds for PostgreSQL.
        server_settings = connect_args.get("server_settings", {})
        server_settings.setdefault("statement_timeout", "30000")
        connect_args["server_settings"] = server_settings
        engine_kwargs["connect_args"] = connect_args

    return create_async_engine(settings.sqlalchemy_async_database_uri, **engine_kwargs)


def reset_async_engine() -> None:
    """
    Reset the async engine and session factory.

    This should be called between tests to ensure a fresh engine is created
    for each test's event loop.
    """
    global _async_engine, _async_session_factory
    _async_engine = None
    _async_session_factory = None


def get_async_engine() -> AsyncEngine:
    """
    Get or create the async engine (lazy initialization).

    Returns:
        AsyncEngine: The global async engine instance
    """
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_db_engine()
    return _async_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the async session factory (lazy initialization).

    Returns:
        async_sessionmaker: The global async session factory
    """
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


def create_celery_async_session() -> async_sessionmaker[AsyncSession]:
    """
    Create a fresh async session factory for Celery tasks.

    Unlike get_async_session_factory(), this creates a NEW engine every time
    with NullPool. This is necessary because each asyncio.run() in a Celery
    task creates a new event loop, and cached engines/pools are bound to the
    old (closed) loop, causing 'Event loop is closed' errors.

    Usage in Celery tasks:
        async def _do_work():
            async_session_factory = create_celery_async_session()
            async with async_session_factory() as db:
                ...

        asyncio.run(_do_work())
    """
    celery_engine = create_async_engine(
        settings.sqlalchemy_async_database_uri,
        echo=settings.sqlalchemy_echo,
        poolclass=NullPool,  # No connection caching - avoids stale loop references
    )
    return async_sessionmaker(
        bind=celery_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,  # Prevent autoflush during tool-triggered SELECTs
    )


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session with automatic cleanup.

    Yields:
        AsyncSession: SQLAlchemy async database session

    Note:
        Use this as a FastAPI dependency for async controllers:
        ``db: AsyncSession = Depends(get_async_db)``

    Handles CancelledError gracefully to prevent noisy errors when
    requests are cancelled (e.g., client disconnect, middleware timeout).
    """
    import asyncio
    import logging

    factory = get_async_session_factory()
    session = factory()
    try:
        yield session
    except asyncio.CancelledError:
        # Request was cancelled - rollback and close gracefully
        try:
            await asyncio.shield(session.rollback())
        except Exception:
            pass  # Ignore errors during cleanup
        raise
    finally:
        try:
            # Shield the close operation from cancellation
            await asyncio.shield(session.close())
        except asyncio.CancelledError:
            # If cancelled during close, force close without waiting
            try:
                await asyncio.wait_for(session.close(), timeout=1.0)
            except Exception:
                pass  # Connection will be cleaned up by pool
        except Exception as e:
            # Log unexpected errors but don't fail
            logging.debug(f"Session cleanup error (safe to ignore): {e}")


def get_db() -> Generator[Session, None, None]:
    """
    Get database session with automatic cleanup.

    Yields:
        Session: SQLAlchemy database session

    Example:
        ```python
        def get_user(user_id: str) -> User:
            db = next(get_db())
            try:
                return db.query(User).filter(User.id == user_id).first()
            finally:
                db.close()
        ```

    Note:
        This is a generator function that ensures the session is
        properly closed even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Get database session as context manager.

    Yields:
        Session: SQLAlchemy database session

    Example:
        ```python
        with get_db_context() as db:
            user = db.query(User).filter(User.id == user_id).first()
        ```

    Note:
        Automatically commits on success and rolls back on exception.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.

    Note:
        This should only be used in development/testing.
        In production, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """
    Drop all database tables.

    Warning:
        This will delete all data! Only use in testing.
    """
    Base.metadata.drop_all(bind=engine)


def close_db() -> None:
    """
    Close sync database engine and dispose of connection pool.

    Note:
        Call this when shutting down the application.
        For async engine disposal, use close_async_db().
    """
    engine.dispose()


async def close_async_db() -> None:
    """
    Close async database engine and dispose of connection pool.

    Note:
        Call this when shutting down the application.
        Must be called from an async context.
    """
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
