from typing import Optional

from pydantic import BaseModel


class Line(BaseModel):
    route_id: str
    short_name: Optional[str] = None
    long_name: Optional[str] = None
    route_type: Optional[int] = None
    color: Optional[str] = None
    text_color: Optional[str] = None


class Stop(BaseModel):
    stop_id: str
    name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    wheelchair_boarding: Optional[int] = None
    distance_m: Optional[float] = None


class StopOnLine(BaseModel):
    stop_id: str
    name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class Departure(BaseModel):
    trip_id: str
    route_id: str
    route_short_name: Optional[str] = None
    headsign: Optional[str] = None
    departure_time: str
    stop_sequence: Optional[int] = None
    is_realtime: bool = False
    delay_s: Optional[int] = None
    realtime_departure_time: Optional[str] = None
