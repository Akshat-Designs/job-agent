import hashlib
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "jobs.db"


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            external_id TEXT,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            description TEXT,
            url TEXT NOT NULL,
            posted_date TEXT,
            content_hash TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'new',
            score INTEGER,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.commit()
    return connection


def job_hash(job: dict) -> str:
    value = "|".join([
        job.get("company", "").strip().lower(),
        job.get("title", "").strip().lower(),
        job.get("url", "").strip().lower()
    ])
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def insert_job(job: dict):
    connection = connect()
    try:
        connection.execute("""
            INSERT OR IGNORE INTO jobs
            (source, external_id, title, company, location, description, url, posted_date, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.get("source", ""), job.get("external_id", ""), job.get("title", ""),
            job.get("company", ""), job.get("location", ""), job.get("description", ""),
            job.get("url", ""), job.get("posted_date", ""), job_hash(job)
        ))
        connection.commit()
    finally:
        connection.close()
