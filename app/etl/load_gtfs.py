"""
Charge les fichiers GTFS (data/gtfs/*.txt) dans une base SQLite structurée
(data/bibus.db), prête à être servie par l'API.

Usage:
    python -m app.etl.load_gtfs
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

from app.config import DATA_DIR, DB_PATH

GTFS_DIR = DATA_DIR / "gtfs"

SCHEMA = """
DROP TABLE IF EXISTS routes;
DROP TABLE IF EXISTS stops;
DROP TABLE IF EXISTS trips;
DROP TABLE IF EXISTS stop_times;
DROP TABLE IF EXISTS calendar;
DROP TABLE IF EXISTS calendar_dates;

CREATE TABLE routes (
    route_id        TEXT PRIMARY KEY,
    short_name      TEXT,
    long_name       TEXT,
    route_type      INTEGER,   -- 0 tram, 3 bus, 6 telepherique (gondola), cf GTFS spec
    color           TEXT,
    text_color      TEXT
);

CREATE TABLE stops (
    stop_id             TEXT PRIMARY KEY,
    name                TEXT,
    lat                 REAL,
    lon                 REAL,
    wheelchair_boarding INTEGER
);

CREATE TABLE trips (
    trip_id                 TEXT PRIMARY KEY,
    route_id                TEXT,
    service_id              TEXT,
    headsign                TEXT,
    direction_id            INTEGER,
    wheelchair_accessible   INTEGER,
    bikes_allowed           INTEGER
);

CREATE TABLE stop_times (
    trip_id         TEXT,
    stop_id         TEXT,
    arrival_time    TEXT,
    departure_time  TEXT,
    stop_sequence   INTEGER
);

CREATE TABLE calendar (
    service_id  TEXT PRIMARY KEY,
    monday      INTEGER, tuesday INTEGER, wednesday INTEGER,
    thursday    INTEGER, friday INTEGER, saturday INTEGER, sunday INTEGER,
    start_date  TEXT, end_date TEXT
);

CREATE TABLE calendar_dates (
    service_id      TEXT,
    date            TEXT,
    exception_type  INTEGER
);

CREATE INDEX idx_stop_times_stop ON stop_times(stop_id);
CREATE INDEX idx_stop_times_trip ON stop_times(trip_id);
CREATE INDEX idx_trips_route ON trips(route_id);
CREATE INDEX idx_trips_service ON trips(service_id);
CREATE INDEX idx_calendar_dates_service ON calendar_dates(service_id);
"""


def _read(name: str) -> pd.DataFrame:
    path = GTFS_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str)


def load() -> None:
    if not GTFS_DIR.exists():
        print(
            f"Dossier {GTFS_DIR} introuvable. "
            "Lance d'abord: python -m app.etl.download_gtfs",
            file=sys.stderr,
        )
        sys.exit(1)

    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    routes = _read("routes.txt")
    if not routes.empty:
        routes = routes.rename(columns={
            "route_short_name": "short_name",
            "route_long_name": "long_name",
            "route_color": "color",
            "route_text_color": "text_color",
        })[["route_id", "short_name", "long_name", "route_type", "color", "text_color"]]
        routes.to_sql("routes", conn, if_exists="append", index=False)

    stops = _read("stops.txt")
    if not stops.empty:
        stops = stops.rename(columns={
            "stop_name": "name",
            "stop_lat": "lat",
            "stop_lon": "lon",
        })
        for col in ["wheelchair_boarding"]:
            if col not in stops.columns:
                stops[col] = None
        stops = stops[["stop_id", "name", "lat", "lon", "wheelchair_boarding"]]
        stops.to_sql("stops", conn, if_exists="append", index=False)

    trips = _read("trips.txt")
    if not trips.empty:
        trips = trips.rename(columns={"trip_headsign": "headsign"})
        for col in ["direction_id", "wheelchair_accessible", "bikes_allowed"]:
            if col not in trips.columns:
                trips[col] = None
        trips = trips[[
            "trip_id", "route_id", "service_id", "headsign",
            "direction_id", "wheelchair_accessible", "bikes_allowed",
        ]]
        trips.to_sql("trips", conn, if_exists="append", index=False)

    stop_times = _read("stop_times.txt")
    if not stop_times.empty:
        stop_times = stop_times[[
            "trip_id", "stop_id", "arrival_time", "departure_time", "stop_sequence",
        ]]
        stop_times.to_sql("stop_times", conn, if_exists="append", index=False)

    calendar = _read("calendar.txt")
    if not calendar.empty:
        calendar.to_sql("calendar", conn, if_exists="append", index=False)

    calendar_dates = _read("calendar_dates.txt")
    if not calendar_dates.empty:
        calendar_dates.to_sql("calendar_dates", conn, if_exists="append", index=False)

    conn.commit()

    counts = {}
    for table in ["routes", "stops", "trips", "stop_times", "calendar", "calendar_dates"]:
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()

    print(f"Base SQLite créée : {DB_PATH}")
    for table, n in counts.items():
        print(f"  {table:<15} {n} lignes")


if __name__ == "__main__":
    load()
