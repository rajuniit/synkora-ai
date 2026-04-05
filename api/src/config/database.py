"""Database configuration."""

from typing import Any
from urllib.parse import quote_plus

from pydantic import Field, NonNegativeInt, computed_field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""

    db_host: str = Field(
        default="localhost",
        description="Hostname or IP address of the database server",
    )

    db_port: int = Field(
        default=5432,
        description="Port number for database connection",
    )

    db_username: str = Field(
        default="postgres",
        description="Username for database authentication",
    )

    db_password: str = Field(
        default="",
        description="Password for database authentication",
    )

    db_database: str = Field(
        default="synkora",
        description="Name of the database to connect to",
    )

    db_charset: str = Field(
        default="",
        description="Character set for database connection",
    )

    db_extras: str = Field(
        default="",
        description="Additional database connection parameters",
    )

    sqlalchemy_database_uri_scheme: str = Field(
        default="postgresql",
        description="Database URI scheme for SQLAlchemy sync connection",
    )

    sqlalchemy_async_database_uri_scheme: str = Field(
        default="postgresql+asyncpg",
        description="Database URI scheme for SQLAlchemy async connection (requires asyncpg driver)",
    )

    sqlalchemy_pool_size: NonNegativeInt = Field(
        default=5,
        description=(
            "Connections held open per process. "
            "With PgBouncer (PGBOUNCER_ENABLED=true) in front of PostgreSQL, "
            "keep this small — PgBouncer multiplexes app connections to a fixed "
            "pool of real PostgreSQL connections, so a large per-process pool "
            "wastes memory without adding PostgreSQL capacity."
        ),
    )

    sqlalchemy_max_overflow: NonNegativeInt = Field(
        default=5,
        description=(
            "Burst connections beyond pool_size. "
            "PgBouncer handles multiplexing; keep overflow small (5) to avoid "
            "a thundering-herd of client connections to PgBouncer under load."
        ),
    )

    sqlalchemy_pool_recycle: NonNegativeInt = Field(
        default=3600,
        description="Number of seconds after which a connection is automatically recycled",
    )

    sqlalchemy_pool_use_lifo: bool = Field(
        default=True,
        description="Use LIFO for connection pool - reuses recently-returned (warm) connections first, keeping fewer connections open",
    )

    sqlalchemy_pool_pre_ping: bool = Field(
        default=True,
        description="Pre-ping connections before reuse. Catches stale connections (e.g. after DB restart or load-balancer timeout) before they cause a 500 error",
    )

    sqlalchemy_echo: bool = Field(
        default=False,
        description="If True, SQLAlchemy will log all SQL statements",
    )

    sqlalchemy_pool_timeout: NonNegativeInt = Field(
        default=30,
        description="Number of seconds to wait for a connection from the pool before raising a timeout error",
    )

    @computed_field  # type: ignore[misc]
    @property
    def sqlalchemy_database_uri(self) -> str:
        """Construct SQLAlchemy sync database URI."""
        db_extras = (
            f"{self.db_extras}&client_encoding={self.db_charset}" if self.db_charset else self.db_extras
        ).strip("&")
        db_extras = f"?{db_extras}" if db_extras else ""
        return (
            f"{self.sqlalchemy_database_uri_scheme}://"
            f"{quote_plus(self.db_username)}:{quote_plus(self.db_password)}@"
            f"{self.db_host}:{self.db_port}/{self.db_database}"
            f"{db_extras}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def sqlalchemy_async_database_uri(self) -> str:
        """Construct SQLAlchemy async database URI."""
        db_extras = (
            f"{self.db_extras}&client_encoding={self.db_charset}" if self.db_charset else self.db_extras
        ).strip("&")
        db_extras = f"?{db_extras}" if db_extras else ""
        return (
            f"{self.sqlalchemy_async_database_uri_scheme}://"
            f"{quote_plus(self.db_username)}:{quote_plus(self.db_password)}@"
            f"{self.db_host}:{self.db_port}/{self.db_database}"
            f"{db_extras}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def sqlalchemy_engine_options(self) -> dict[str, Any]:
        """Get SQLAlchemy sync engine options (for psycopg2)."""
        connect_args = {"options": "-c timezone=UTC"}

        return {
            "pool_size": self.sqlalchemy_pool_size,
            "max_overflow": self.sqlalchemy_max_overflow,
            "pool_recycle": self.sqlalchemy_pool_recycle,
            "pool_pre_ping": self.sqlalchemy_pool_pre_ping,
            "connect_args": connect_args,
            "pool_use_lifo": self.sqlalchemy_pool_use_lifo,
            "pool_reset_on_return": "rollback",
            "pool_timeout": self.sqlalchemy_pool_timeout,
        }

    pgbouncer_enabled: bool = Field(
        default=False,
        description=(
            "Set to True when PgBouncer sits between the app and PostgreSQL. "
            "Disables asyncpg prepared-statement caching (statement_cache_size=0), "
            "which is incompatible with PgBouncer transaction-mode pooling."
        ),
    )

    @computed_field  # type: ignore[misc]
    @property
    def sqlalchemy_async_engine_options(self) -> dict[str, Any]:
        """Get SQLAlchemy async engine options (for asyncpg)."""
        # asyncpg uses different connection args format than psycopg2.
        # server_settings is the asyncpg equivalent of psycopg2's options.
        connect_args: dict[str, Any] = {
            "server_settings": {"timezone": "UTC"},
            "command_timeout": 30,  # Statement timeout in seconds
        }

        if self.pgbouncer_enabled:
            # PgBouncer transaction mode does not support named prepared statements.
            # asyncpg caches prepared statements by default — disable to prevent
            # "prepared statement ... already exists" errors under transaction pooling.
            connect_args["statement_cache_size"] = 0

        # pool_use_lifo is omitted: AsyncAdaptedQueuePool (used by async engines)
        # does not support the use_lifo parameter — only the sync QueuePool does.
        #
        # pool_pre_ping: disabled when PgBouncer is in front. PgBouncer keeps persistent
        # connections to PostgreSQL and handles dead connection detection itself.
        # pre_ping sends SELECT 1 on every checkout — with cross-cloud latency (DO→AWS)
        # this adds ~15ms per session per request for zero benefit.
        pre_ping = False if self.pgbouncer_enabled else self.sqlalchemy_pool_pre_ping

        return {
            "pool_size": self.sqlalchemy_pool_size,
            "max_overflow": self.sqlalchemy_max_overflow,
            "pool_recycle": self.sqlalchemy_pool_recycle,
            "pool_pre_ping": pre_ping,
            "connect_args": connect_args,
            "pool_reset_on_return": "rollback",
            "pool_timeout": self.sqlalchemy_pool_timeout,
        }
