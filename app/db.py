"""
Database configuration and helper utilities.

This module centralizes the logic for connecting to the MySQL database.
Using a connection pool improves performance by re‑using existing
connections instead of creating new ones on every request. The
connection parameters are read from environment variables to avoid
hard‑coding secrets in the source code. When the application starts,
``init_pool`` should be called to set up the pool; subsequent calls
to ``get_connection`` will return a connection from the pool. If
``init_pool`` has not been called the first call to ``get_connection``
will automatically initialize the pool with sane defaults.
"""

import os
from typing import Optional

import mysql.connector
from mysql.connector import pooling


#: Global variable holding the connection pool instance. It is set by
#: :func:`init_pool` and used by :func:`get_connection`.
_POOL: Optional[pooling.MySQLConnectionPool] = None


def init_pool() -> None:
    """Initialize the MySQL connection pool.

    Reads the database connection settings from environment variables
    and creates a pool of connections. This function should be
    idempotent; calling it multiple times will reinitialize the pool.

    Environment variables used:

    - ``DB_HOST``: the database host (default: ``"localhost"``)
    - ``DB_PORT``: the database port (default: ``3306``)
    - ``DB_NAME``: the database name (default: ``"uabc_retina"``)
    - ``DB_USER``: the database user (default: ``"root"``)
    - ``DB_PASSWORD``: the database password (default: ``"fifolin123"``)
    - ``DB_POOL_SIZE``: the number of connections in the pool (default: ``5``)
    """
    global _POOL

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "3306"))
    database = os.getenv("DB_NAME", "uabc_retina")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "fifolin123")
    pool_size = int(os.getenv("DB_POOL_SIZE", "5"))

    _POOL = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="fastapi_pool",
        pool_size=pool_size,
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        autocommit=True,
    )


def get_connection() -> mysql.connector.connection.MySQLConnection:
    """Get a connection from the pool.

    If the pool has not been initialized yet this function will call
    :func:`init_pool` automatically. The caller is responsible for
    closing the returned connection when done. The returned
    connection is configured to autocommit by default.

    Returns:
        mysql.connector.connection.MySQLConnection: a connection from
        the pool ready for use.
    """
    global _POOL
    if _POOL is None:
        init_pool()
    assert _POOL is not None  # mypy/linters
    return _POOL.get_connection()
