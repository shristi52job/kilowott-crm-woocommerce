"""
Database configuration and SQLite connection management.
Supports automatic schema migration and configurable DB paths.
"""

import sqlite3
import os
from contextlib import contextmanager

DEFAULT_DB_PATH = os.environ.get("CRM_DB_PATH", "/tmp/kilowott_crm.db")


def init_db(db_path: str = DEFAULT_DB_PATH):
    """Initialize database tables if they do not exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Customers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        woocommerce_id INTEGER UNIQUE,
        email TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        phone TEXT,
        total_spent REAL DEFAULT 0.0,
        order_count INTEGER DEFAULT 0,
        lifecycle_stage TEXT DEFAULT 'Lead',
        tags TEXT DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Orders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        woocommerce_order_id INTEGER UNIQUE NOT NULL,
        customer_id INTEGER NOT NULL,
        customer_email TEXT NOT NULL,
        total_amount REAL NOT NULL,
        currency TEXT DEFAULT 'INR',
        status TEXT NOT NULL,
        items TEXT NOT NULL,
        customer_notes TEXT,
        order_date TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)

    # Communications log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS communications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        customer_email TEXT NOT NULL,
        trigger_event TEXT NOT NULL,
        subject TEXT NOT NULL,
        body TEXT NOT NULL,
        status TEXT DEFAULT 'draft',
        sentiment TEXT DEFAULT 'neutral',
        agent_reasoning TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)

    conn.commit()
    conn.close()


@contextmanager
def get_db_connection(db_path: str = DEFAULT_DB_PATH):
    """Context manager for SQLite connections with row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
