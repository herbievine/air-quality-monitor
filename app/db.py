import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    co2_ppm INTEGER,
    temp_c REAL,
    humidity_pct REAL,
    pm1_0 INTEGER,
    pm2_5 INTEGER,
    pm10 INTEGER,
    voc_index INTEGER,
    nox_index INTEGER
);
"""

INSERT = """
INSERT INTO readings (co2_ppm, temp_c, humidity_pct, pm1_0, pm2_5, pm10, voc_index, nox_index)
VALUES (:co2_ppm, :temp_c, :humidity_pct, :pm1_0, :pm2_5, :pm10, :voc_index, :nox_index);
"""


class Database:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(SCHEMA)
        self._conn.commit()

    def insert_reading(self, reading: dict) -> None:
        self._conn.execute(INSERT, reading)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
