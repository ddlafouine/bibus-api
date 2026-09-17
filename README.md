# Bibus API

<p align="center">
  <img src="logo.png" alt="Description de l'image" width="500">
</p>

API REST (non-officielle) sur les données open data du réseau **Bibus**
(Brest Métropole) : lignes, arrêts, horaires théoriques et positions temps réel.

Source des données : [transport.data.gouv.fr — Réseau urbain Bibus](https://transport.data.gouv.fr/datasets/horaires-theoriques-et-temps-reel-des-bus-et-tramways-circulant-sur-le-territoire-de-brest-metropole)
(GTFS statique + flux GTFS-RT, licence ODbL / Etalab).

## Architecture

```
bibus-api/
├── app/
│   ├── config.py              # URLs sources, chemin de la base SQLite
│   ├── database.py            # connexion SQLite
│   ├── schemas.py             # modèles Pydantic (contrats de l'API)
│   ├── main.py                # app FastAPI, montage des routers
│   ├── etl/
│   │   ├── download_gtfs.py   # télécharge et dézippe le GTFS officiel
│   │   └── load_gtfs.py       # parse les .txt GTFS -> SQLite structuré
│   ├── services/
│   │   └── schedule.py        # calcul des services actifs / prochains passages
│   └── routers/
│       ├── lines.py           # /lines
│       ├── stops.py           # /stops
│       └── realtime.py        # /realtime (GTFS-RT, bonus)
├── data/                      # gtfs/ (bruts) + bibus.db (générée), ignorés par git
├── requirements.txt
└── README.md
```

Le choix GTFS statique → SQLite plutôt qu'un simple parsing CSV à la volée : les
fichiers `stop_times.txt` de Bibus font plusieurs Mo (des milliers de lignes),
donc une base indexée rend les requêtes (prochains passages, arrêts d'une ligne)
instantanées, et permet d'écrire l'API en SQL plutôt qu'en boucles Python.

## Installation

```bash
cd bibus-api
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 1. Charger les données (ETL)

```bash
python -m app.etl.download_gtfs   # télécharge le zip GTFS officiel dans data/gtfs/
python -m app.etl.load_gtfs       # construit data/bibus.db
```

À relancer périodiquement (les horaires Bibus changent plusieurs fois par an) —
tu peux en faire un cron.

## 2. Lancer l'API

```bash
uvicorn app.main:app --reload --port 8000
```

Documentation interactive (Swagger) : http://localhost:8000/docs

## Carte

Une carte Leaflet minimaliste est servie directement par l'API, sans build ni
serveur séparé (aucun souci de CORS : la page et l'API sont sur la même origine) :

http://localhost:8000/map

Elle affiche tous les arrêts (`/stops?limit=2000`) et les positions des bus en
temps réel (`/realtime/vehicles`, rafraîchi toutes les 15s), colorées par
ligne. Si le flux temps réel est indisponible, un bandeau discret l'indique
et la carte continue d'afficher les arrêts normalement.

Le fichier est dans `app/static/map.html` — modifiable librement (fond de
carte, style des marqueurs, clustering si besoin une fois qu'il y a beaucoup
d'arrêts, etc.).

## Endpoints

| Méthode | Route | Description |
|---|---|---|
| GET | `/health` | État de l'API et présence de la base |
| GET | `/lines` | Liste des lignes (bus, tram, téléphérique) |
| GET | `/lines/{route_id}` | Détail d'une ligne |
| GET | `/lines/{route_id}/stops` | Arrêts desservis par une ligne |
| GET | `/stops?q=...` | Recherche d'arrêts par nom |
| GET | `/stops?lat=..&lon=..&radius_m=..` | Recherche d'arrêts par proximité géo |
| GET | `/stops/{stop_id}` | Détail d'un arrêt |
| GET | `/stops/{stop_id}/departures?date=&after=&limit=&realtime=` | Prochains passages **fusionnés théorique + temps réel** (gère le calendrier GTFS ; `realtime=false` pour désactiver l'enrichissement) |
| GET | `/realtime/vehicles` | Positions live des véhicules (proxy + décodage GTFS-RT, cache 20s) |
| GET | `/realtime/trip-updates` | Retards/avances live par course (proxy + décodage GTFS-RT, cache 20s) |
| GET | `/map` | Carte interactive (Leaflet) : arrêts + bus en temps réel |

### Exemples

```bash
curl "http://localhost:8000/stops?q=Liberte"
curl "http://localhost:8000/stops/SIAM1/departures?limit=5"
curl "http://localhost:8000/lines/A/stops"
curl "http://localhost:8000/realtime/vehicles"
curl "http://localhost:8000/stops/S1/departures?realtime=false"
```

## Notes

- `/stops/{id}/departures` renvoie l'horaire théorique **et**, quand c'est
  possible, l'heure corrigée par le temps réel (`is_realtime`, `delay_s`,
  `realtime_departure_time`). Si le flux GTFS-RT est indisponible, l'endpoint
  ne plante jamais : il retombe silencieusement sur le théorique seul.
- Les flux `/realtime/*` sont mis en cache 20s (voir `app/cache.py` et
  `app/services/realtime.py`) pour éviter de re-taper le flux officiel à
  chaque requête entrante — un cache mémoire simple, pas besoin de Redis pour
  une instance unique.
- Les identifiants (`route_id`, `stop_id`) sont ceux du GTFS Bibus ; regarde
  `/lines` et `/stops` pour les découvrir.
- Le token dans les URLs GTFS-RT (`app/config.py`) est le token public publié
  sur la fiche du jeu de données transport.data.gouv.fr, pas un secret perso.

## Pour aller plus loin (pistes, pas implémenté)

- Tests (pytest) sur `services/schedule.py` et `services/realtime.py`
- APScheduler pour relancer l'ETL GTFS statique automatiquement (1x/nuit)
- Dockerfile + docker-compose (service API + service cron ETL)
- Endpoint `/lines/{id}/shape` (tracé GeoJSON) depuis `shapes.txt`
- Auth (clé API) si l'API est un jour exposée publiquement
