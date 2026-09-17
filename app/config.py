"""
Configuration centrale de l'API Bibus.

Sources officielles (transport.data.gouv.fr - dataset "Réseau urbain Bibus"):
https://transport.data.gouv.fr/datasets/horaires-theoriques-et-temps-reel-des-bus-et-tramways-circulant-sur-le-territoire-de-brest-metropole
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = os.environ.get("BIBUS_DB_PATH", str(DATA_DIR / "bibus.db"))

# GTFS statique (horaires théoriques, mis à jour régulièrement par RATP Dev / Bibus)
GTFS_ZIP_URL = os.environ.get(
    "BIBUS_GTFS_URL",
    "https://s3.eu-west-1.amazonaws.com/files.orchestra.ratpdev.com/networks/bibus/exports/medias.zip",
)

# Flux temps réel GTFS-RT (protobuf), proxifiés par le PAN (transport.data.gouv.fr)
# NB: le token dans l'URL est celui publié publiquement sur la fiche du jeu de
# données (pas un secret perso) ; transport.data.gouv.fr peut le faire tourner,
# vérifie-le sur la page du dataset si les flux se mettent à renvoyer du 403/401.
_GTFS_RT_TOKEN = "xdgqKBTAzhw4DSPz6zeGc4c5eW0LhwztcGv4-vpzP4U"

GTFS_RT_VEHICLE_POSITIONS_URL = os.environ.get(
    "BIBUS_GTFS_RT_VEHICLES_URL",
    f"https://proxy.transport.data.gouv.fr/resource/bibus-brest-gtfs-rt-vehicle-position?token={_GTFS_RT_TOKEN}",
)
GTFS_RT_TRIP_UPDATES_URL = os.environ.get(
    "BIBUS_GTFS_RT_TRIP_UPDATES_URL",
    f"https://proxy.transport.data.gouv.fr/resource/bibus-brest-gtfs-rt-trip-update?token={_GTFS_RT_TOKEN}",
)
GTFS_RT_ALERTS_URL = os.environ.get(
    "BIBUS_GTFS_RT_ALERTS_URL",
    f"https://proxy.transport.data.gouv.fr/resource/bibus-brest-gtfs-rt-alerts?token={_GTFS_RT_TOKEN}",
)
