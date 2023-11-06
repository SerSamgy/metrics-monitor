import asyncpg

from metrics_monitor.models import WebsiteMetrics


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


async def save_metrics(metrics: WebsiteMetrics, conn: asyncpg.Connection):
    """
    Saves website metrics to the database.

    Args:
        metrics (WebsiteMetrics): The website metrics to be saved.
        conn (asyncpg.Connection): The database connection.

    Returns:
        None
    """

    await conn.execute(
        """INSERT INTO website_metrics (url, request_timestamp, response_time, status_code, pattern_found) 
        VALUES ($1, $2, $3, $4, $5)""",
        metrics.url,
        metrics.request_timestamp,
        metrics.response_time,
        metrics.status_code,
        metrics.pattern_found,
    )
