"""
Télécharge l'archive GTFS officielle de Bibus et l'extrait dans data/gtfs/.

Usage:
    python -m app.etl.download_gtfs
"""
import io
import sys
import zipfile

import requests

from app.config import DATA_DIR, GTFS_ZIP_URL

GTFS_DIR = DATA_DIR / "gtfs"


def download_and_extract() -> None:
    GTFS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Téléchargement de {GTFS_ZIP_URL} ...")
    resp = requests.get(GTFS_ZIP_URL, timeout=60)
    resp.raise_for_status()

    print(f"Extraction dans {GTFS_DIR} ...")
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(GTFS_DIR)

    files = sorted(p.name for p in GTFS_DIR.glob("*.txt"))
    print(f"OK. Fichiers GTFS extraits : {files}")


if __name__ == "__main__":
    try:
        download_and_extract()
    except requests.RequestException as exc:
        print(f"Erreur de téléchargement : {exc}", file=sys.stderr)
        sys.exit(1)
