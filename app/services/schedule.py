"""
Logique de calcul des horaires théoriques GTFS.

GTFS gère le calendrier via deux mécanismes combinables :
- calendar.txt        : jours de la semaine + période de validité
- calendar_dates.txt  : exceptions ponctuelles (ajout=1 / suppression=2)
"""
import sqlite3
from datetime import date as date_cls

WEEKDAY_COLUMNS = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
]


def active_service_ids(conn: sqlite3.Connection, on_date: date_cls) -> set[str]:
    yyyymmdd = on_date.strftime("%Y%m%d")
    weekday_col = WEEKDAY_COLUMNS[on_date.weekday()]

    base = conn.execute(
        f"""
        SELECT service_id FROM calendar
        WHERE {weekday_col} = '1'
          AND start_date <= ? AND end_date >= ?
        """,
        (yyyymmdd, yyyymmdd),
    ).fetchall()
    services = {r["service_id"] for r in base}

    exceptions = conn.execute(
        "SELECT service_id, exception_type FROM calendar_dates WHERE date = ?",
        (yyyymmdd,),
    ).fetchall()
    for row in exceptions:
        if row["exception_type"] == "1":
            services.add(row["service_id"])
        elif row["exception_type"] == "2":
            services.discard(row["service_id"])

    return services


def apply_delay(gtfs_time: str, delay_s: int) -> str:
    """
    Additionne un décalage (en secondes, positif=retard/négatif=avance) à une
    heure GTFS 'HH:MM:SS'. GTFS autorise des heures > 24:00:00 (courses après
    minuit) : on préserve ce format plutôt que de repasser par un objet date.
    """
    h, m, s = (int(part) for part in gtfs_time.split(":"))
    total = h * 3600 + m * 60 + s + delay_s
    total = max(total, 0)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"



def next_departures(
    conn: sqlite3.Connection,
    stop_id: str,
    on_date: date_cls,
    after_time: str,
    limit: int = 10,
):
    services = active_service_ids(conn, on_date)
    if not services:
        return []

    placeholders = ",".join("?" for _ in services)
    rows = conn.execute(
        f"""
        SELECT st.trip_id, t.route_id, r.short_name AS route_short_name,
               t.headsign, st.departure_time, st.stop_sequence
        FROM stop_times st
        JOIN trips t ON t.trip_id = st.trip_id
        JOIN routes r ON r.route_id = t.route_id
        WHERE st.stop_id = ?
          AND t.service_id IN ({placeholders})
          AND st.departure_time >= ?
        ORDER BY st.departure_time ASC
        LIMIT ?
        """,
        (stop_id, *services, after_time, limit),
    ).fetchall()
    return [dict(r) for r in rows]
