"""
database.py
-----------
PostgreSQL connection helpers.

Usage:
    from database import get_connection

    conn = get_connection()
    # use conn, then conn.close()

    # OR use the context manager for auto-commit + auto-close:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load .env from the backend/ directory (works whether you run from
# backend/ or from a subdirectory like pipelines/).
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


def get_connection():
    """
    Return a psycopg2 connection using DB_* environment variables.

    Required env vars:
        DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
    """
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=int(os.getenv("DB_PORT", 5432)),
    )
