from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.config import DB_PATH
from app.routers import lines, realtime, stops

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Bibus API",
    description=(
        "API non-officielle construite sur les données open data du réseau Bibus "
        "(Brest Métropole) — GTFS statique. "
        "Source : https://transport.data.gouv.fr/datasets/"
        "horaires-theoriques-et-temps-reel-des-bus-et-tramways-circulant-sur-le-territoire-de-brest-metropole"
    ),
    version="1.0.0",
)

app.include_router(lines.router)
app.include_router(stops.router)
app.include_router(realtime.router)


@app.get("/map", tags=["Carte"], summary="Carte interactive (arrêts + bus en temps réel)", include_in_schema=False)
def map_view():
    return FileResponse(STATIC_DIR / "map.html")


@app.get("/health", tags=["Santé"], summary="Vérifie que l'API et la base de données sont prêtes")
def health():
    return {
        "status": "ok" if Path(DB_PATH).exists() else "db_missing",
        "db_path": DB_PATH,
    }


@app.get("/", tags=["Santé"], include_in_schema=False)
def root():
    return {"message": "Bibus API — voir /docs pour la documentation interactive"}
