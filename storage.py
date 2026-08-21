"""Local SQLite storage for cumulative measurement logs."""

import hashlib
import json
import sqlite3
from pathlib import Path

from config import BASE_DIR

DATABASE_PATH = BASE_DIR / "data" / "gas_test_logs.sqlite3"


def _connection():
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS measurement_records (
            fingerprint TEXT PRIMARY KEY,
            test_type TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    return connection


def _fingerprint(test_type, record):
    identity = "|".join(
        str(record.get(field, ""))
        for field in ("performed_date", "no", "management_number", "location")
    )
    return hashlib.sha256(f"{test_type}|{identity}".encode()).hexdigest()


def save_and_load(test_type, records):
    """Upsert reviewed records and return every saved record for this test type."""
    with _connection() as connection:
        for record in records:
            connection.execute(
                """
                INSERT INTO measurement_records (fingerprint, test_type, payload)
                VALUES (?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET payload = excluded.payload
                """,
                (_fingerprint(test_type, record), test_type, json.dumps(record, ensure_ascii=False)),
            )
        rows = connection.execute(
            "SELECT payload FROM measurement_records WHERE test_type = ?", (test_type,)
        ).fetchall()
    return [json.loads(row[0]) for row in rows]
