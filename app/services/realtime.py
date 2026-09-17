"""
Service temps réel : interroge les flux GTFS-RT officiels (protobuf), les
décode, et les met en cache quelques secondes pour éviter de re-taper le flux
à chaque requête entrante sur l'API.
"""
import requests
from google.transit import gtfs_realtime_pb2

from app.cache import cached
from app.config import GTFS_RT_TRIP_UPDATES_URL, GTFS_RT_VEHICLE_POSITIONS_URL

REALTIME_TTL_S = 20  # les positions/retards Bibus sont republiés environ toutes les 15-30s


class RealtimeUnavailable(Exception):
    """Le flux GTFS-RT n'a pas pu être récupéré (réseau, format...)."""


def _fetch_feed_raw(url: str) -> gtfs_realtime_pb2.FeedMessage:
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RealtimeUnavailable(str(exc)) from exc
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(resp.content)
    return feed


def get_vehicle_positions_feed() -> gtfs_realtime_pb2.FeedMessage:
    return cached(
        "gtfs_rt_vehicles",
        REALTIME_TTL_S,
        lambda: _fetch_feed_raw(GTFS_RT_VEHICLE_POSITIONS_URL),
    )


def get_trip_updates_feed() -> gtfs_realtime_pb2.FeedMessage:
    return cached(
        "gtfs_rt_trip_updates",
        REALTIME_TTL_S,
        lambda: _fetch_feed_raw(GTFS_RT_TRIP_UPDATES_URL),
    )


def get_delay_map() -> dict[tuple[str, str], int]:
    """
    Retourne { (trip_id, stop_id): delai_depart_en_secondes }, construit à
    partir du flux trip-updates. Ne lève jamais d'exception : si le flux est
    indisponible, retourne un dict vide (mode "théorique seulement").
    """
    try:
        feed = get_trip_updates_feed()
    except RealtimeUnavailable:
        return {}

    delays: dict[tuple[str, str], int] = {}
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        tu = entity.trip_update
        trip_id = tu.trip.trip_id
        for stu in tu.stop_time_update:
            delay = None
            if stu.HasField("departure") and stu.departure.HasField("delay"):
                delay = stu.departure.delay
            elif stu.HasField("arrival") and stu.arrival.HasField("delay"):
                delay = stu.arrival.delay
            if delay is not None:
                delays[(trip_id, stu.stop_id)] = delay
    return delays
