from typing import List

from fastapi import APIRouter, HTTPException

from app.database import get_conn
from app.schemas import Line, StopOnLine

router = APIRouter(prefix="/lines", tags=["Lignes"])


@router.get("", response_model=List[Line], summary="Liste toutes les lignes (bus, tram, téléphérique)")
def list_lines():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT route_id, short_name, long_name, route_type, color, text_color "
            "FROM routes ORDER BY short_name"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{route_id}", response_model=Line, summary="Détail d'une ligne")
def get_line(route_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT route_id, short_name, long_name, route_type, color, text_color "
            "FROM routes WHERE route_id = ?",
            (route_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Ligne introuvable")
    return dict(row)


@router.get(
    "/{route_id}/stops",
    response_model=List[StopOnLine],
    summary="Liste (dédupliquée) des arrêts desservis par une ligne",
)
def get_line_stops(route_id: str):
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM routes WHERE route_id = ?", (route_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Ligne introuvable")

        rows = conn.execute(
            """
            SELECT DISTINCT s.stop_id, s.name, s.lat, s.lon
            FROM stop_times st
            JOIN trips t ON t.trip_id = st.trip_id
            JOIN stops s ON s.stop_id = st.stop_id
            WHERE t.route_id = ?
            ORDER BY s.name
            """,
            (route_id,),
        ).fetchall()
    return [dict(r) for r in rows]
