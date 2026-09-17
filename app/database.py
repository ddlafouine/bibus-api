import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException

from app.config import DB_PATH


@contextmanager
def get_conn():
    if not Path(DB_PATH).exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Base de données introuvable. Lance d'abord l'ETL : "
                "python -m app.etl.download_gtfs && python -m app.etl.load_gtfs"
            ),
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
