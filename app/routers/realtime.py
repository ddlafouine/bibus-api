"""
Endpoints temps réel : proxy + décodage des flux GTFS-RT officiels, avec
cache de 20s (voir app/services/realtime.py) pour éviter de re-taper le flux
à chaque requête entrante.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.realtime import (
    RealtimeUnavailable,
    get_trip_updates_feed,
    get_vehicle_positions_feed,
)

router = APIRouter(prefix="/realtime", tags=["Temps réel"])


class VehiclePosition(BaseModel):
    vehicle_id: Optional[str] = None
    trip_id: Optional[str] = None
    route_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    bearing: Optional[float] = None
    speed: Optional[float] = None
    timestamp: Optional[int] = None


class TripUpdateStop(BaseModel):
    stop_id: Optional[str] = None
    arrival_delay_s: Optional[int] = None
    departure_delay_s: Optional[int] = None


class TripUpdate(BaseModel):
    trip_id: Optional[str] = None
    route_id: Optional[str] = None
    stops: List[TripUpdateStop] = []


@router.get(
    "/vehicles",
    response_model=List[VehiclePosition],
    summary="Positions des véhicules en temps réel (flux GTFS-RT officiel, cache 20s)",
)
def vehicle_positions():
    try:
        feed = get_vehicle_positions_feed()
    except RealtimeUnavailable as exc:
        raise HTTPException(status_code=502, detail=f"Flux GTFS-RT inaccessible : {exc}")

    results = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        v = entity.vehicle
        results.append(
            VehiclePosition(
                vehicle_id=v.vehicle.id or None,
                trip_id=v.trip.trip_id or None,
                route_id=v.trip.route_id or None,
                lat=v.position.latitude or None,
                lon=v.position.longitude or None,
                bearing=v.position.bearing if v.position.HasField("bearing") else None,
                speed=v.position.speed if v.position.HasField("speed") else None,
                timestamp=v.timestamp or None,
            )
        )
    return results


@router.get(
    "/trip-updates",
    response_model=List[TripUpdate],
    summary="Retards / avances en temps réel par course (flux GTFS-RT officiel, cache 20s)",
)
def trip_updates():
    try:
        feed = get_trip_updates_feed()
    except RealtimeUnavailable as exc:
        raise HTTPException(status_code=502, detail=f"Flux GTFS-RT inaccessible : {exc}")

    results = []
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        tu = entity.trip_update
        stops = [
            TripUpdateStop(
                stop_id=stu.stop_id or None,
                arrival_delay_s=stu.arrival.delay if stu.HasField("arrival") else None,
                departure_delay_s=stu.departure.delay if stu.HasField("departure") else None,
            )
            for stu in tu.stop_time_update
        ]
        results.append(
            TripUpdate(trip_id=tu.trip.trip_id or None, route_id=tu.trip.route_id or None, stops=stops)
        )
    return results
