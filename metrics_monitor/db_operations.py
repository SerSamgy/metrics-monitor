import os
from datetime import datetime

import asyncpg


async def get_db_connection() -> asyncpg.Connection:
    """
    Get a connection to the database where website metrics will be stored.

    Returns:
        asyncpg.Connection: The connection to the database where website metrics will be stored.
    """
    pg_user = os.getenv("POSTGRES_USER")
    pg_password = os.getenv("POSTGRES_PASSWORD")
    pg_host = os.getenv("POSTGRES_HOST")
    pg_port = os.getenv("POSTGRES_PORT")
    pg_database = os.getenv("POSTGRES_DATABASE")
    dsn = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"

    return await asyncpg.connect(dsn)


async def create_table(conn: asyncpg.Connection):
    """
    Create the table in the database where website metrics will be stored.

    Args:
        conn (asyncpg.Connection): The database connection.

    Returns:
        None
    """
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS website_metrics (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL,
            request_timestamp TIMESTAMP NOT NULL,
            response_time FLOAT NOT NULL,
            status_code INTEGER NOT NULL,
            pattern_found BOOLEAN NOT NULL
        )"""
    )


async def save_metrics(
    url: str,
    request_timestamp: datetime,
    response_time: float,
    status_code: int,
    pattern_found: bool,
    conn: asyncpg.Connection,
):
    """
    Saves website metrics to the database.

    Args:
        url (str): The URL of the website.
        request_timestamp (datetime): The timestamp of the request.
        response_time (float): The response time of the request.
        status_code (int): The HTTP status code of the response.
        pattern_found (bool): Whether the expected pattern was found in the response.
        conn (asyncpg.Connection): The database connection.

    Returns:
        None
    """
    await conn.execute(
        """INSERT INTO website_metrics (url, request_timestamp, response_time, status_code, pattern_found) 
        VALUES ($1, $2, $3, $4, $5)""",
        url,
        request_timestamp,
        response_time,
        status_code,
        pattern_found,
    )
