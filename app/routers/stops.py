import unicodedata
from datetime import date as date_cls
from math import asin, cos, radians, sin, sqrt
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.database import get_conn
from app.schemas import Departure, Stop
from app.services.realtime import get_delay_map
from app.services.schedule import apply_delay, next_departures

router = APIRouter(prefix="/stops", tags=["Arrêts"])


def _strip_accents(text: str) -> str:
    """'Liberté' -> 'liberte' : pour matcher indépendamment des accents/casse."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c)).lower()


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


@router.get(
    "",
    response_model=List[Stop],
    summary="Recherche d'arrêts par nom, ou par proximité géographique (lat/lon/radius_m)",
)
def search_stops(
    q: Optional[str] = Query(None, description="Recherche texte sur le nom de l'arrêt"),
    lat: Optional[float] = Query(None, description="Latitude pour une recherche par proximité"),
    lon: Optional[float] = Query(None, description="Longitude pour une recherche par proximité"),
    radius_m: float = Query(500, description="Rayon de recherche en mètres (avec lat/lon)"),
    limit: int = Query(20, le=2000, description="200+ pour charger tous les arrêts (ex: une carte)"),
):
    with get_conn() as conn:
        if lat is not None and lon is not None:
            rows = conn.execute("SELECT stop_id, name, lat, lon, wheelchair_boarding FROM stops").fetchall()
            results = []
            for r in rows:
                if r["lat"] is None or r["lon"] is None:
                    continue
                d = _haversine_m(lat, lon, r["lat"], r["lon"])
                if d <= radius_m:
                    item = dict(r)
                    item["distance_m"] = round(d, 1)
                    results.append(item)
            results.sort(key=lambda x: x["distance_m"])
            return results[:limit]

        rows = conn.execute(
            "SELECT stop_id, name, lat, lon, wheelchair_boarding FROM stops ORDER BY name"
        ).fetchall()
        if not q:
            return [dict(r) for r in rows][:limit]

        needle = _strip_accents(q)
        matches = [dict(r) for r in rows if r["name"] and needle in _strip_accents(r["name"])]
        return matches[:limit]


@router.get("/{stop_id}", response_model=Stop, summary="Détail d'un arrêt")
def get_stop(stop_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT stop_id, name, lat, lon, wheelchair_boarding FROM stops WHERE stop_id = ?",
            (stop_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Arrêt introuvable")
    return dict(row)


@router.get(
    "/{stop_id}/departures",
    response_model=List[Departure],
    summary="Prochains passages théoriques à un arrêt (calcul depuis le GTFS statique)",
)
def get_departures(
    stop_id: str,
    on_date: Optional[date_cls] = Query(None, alias="date", description="Défaut: aujourd'hui"),
    after: Optional[str] = Query(None, description="Heure HH:MM:SS, défaut: maintenant"),
    limit: int = Query(10, le=100),
    realtime: bool = Query(True, description="Enrichir avec les retards temps réel (GTFS-RT)"),
):
    from datetime import datetime

    now = datetime.now()
    on_date = on_date or now.date()
    after = after or now.strftime("%H:%M:%S")

    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM stops WHERE stop_id = ?", (stop_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Arrêt introuvable")
        rows = next_departures(conn, stop_id, on_date, after, limit)

    if not realtime:
        return rows

    # Best-effort : si le flux GTFS-RT est indisponible, get_delay_map() renvoie
    # {} et on retombe silencieusement sur les horaires théoriques.
    delay_map = get_delay_map()
    for row in rows:
        delay = delay_map.get((row["trip_id"], stop_id))
        if delay is not None:
            row["is_realtime"] = True
            row["delay_s"] = delay
            row["realtime_departure_time"] = apply_delay(row["departure_time"], delay)
    return rows
