# music_comp_sorter/db.py
import sqlite3
import os
from .logger import logger

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    fingerprint TEXT,
    mbid TEXT,
    detected_title TEXT,
    detected_artist TEXT,
    detected_album TEXT,
    last_processed_timestamp INTEGER,
    error_message TEXT
);
CREATE TABLE IF NOT EXISTS metadata_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mbid TEXT UNIQUE,
    data_json TEXT NOT NULL,
    cover_path TEXT,
    last_fetched_ts INTEGER
);
CREATE TABLE IF NOT EXISTS conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    tried_options_json TEXT NOT NULL,
    chosen_option_json TEXT,
    auto_chosen BOOLEAN DEFAULT 0,
    created_ts INTEGER DEFAULT (strftime('%s','now')),
    reviewed_ts INTEGER
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

class DB:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init()

    def _init(self):
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def add_file(self, path, status="pending"):
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO files (path, status) VALUES (?, ?)",
                (path, status)
            )
            self.conn.commit()
        except Exception as e:
            logger.exception("DB add_file failed: %s", e)

    def update_file(self, path, **kwargs):
        cols = ", ".join(f"{k}=?" for k in kwargs.keys())
        vals = list(kwargs.values()) + [path]
        sql = f"UPDATE files SET {cols} WHERE path=?"
        self.conn.execute(sql, vals)
        self.conn.commit()

    def get_pending_files(self, limit=None):
        cur = self.conn.cursor()
        q = "SELECT path FROM files WHERE status IN ('pending','processing','error')"
        if limit:
            q += f" LIMIT {limit}"
        cur.execute(q)
        return [r[0] for r in cur.fetchall()]

    def insert_conflict(self, file_path, tried_options_json, auto_chosen=False, chosen_option_json=None):
        self.conn.execute(
            "INSERT INTO conflicts (file_path, tried_options_json, chosen_option_json, auto_chosen) VALUES (?, ?, ?, ?)",
            (file_path, tried_options_json, chosen_option_json, int(auto_chosen))
        )
        self.conn.commit()

    def close(self):
        self.conn.close()