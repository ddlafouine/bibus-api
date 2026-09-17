"""
Cache mémoire minimal (TTL) pour les réponses coûteuses/externes.

Volontairement simple (dict + timestamp) : pas besoin de Redis pour une seule
instance de process. Si l'API est un jour déployée sur plusieurs workers, ce
cache devient per-worker, ce qui reste acceptable pour du temps réel avec un
TTL court (chaque worker re-tape le flux au plus 1x/TTL).
"""
import time
from threading import Lock
from typing import Callable, TypeVar

T = TypeVar("T")

_store: dict[str, tuple[float, object]] = {}
_lock = Lock()


def cached(key: str, ttl_s: float, fetch_fn: Callable[[], T]) -> T:
    """Retourne la valeur en cache si elle a moins de ttl_s secondes, sinon
    appelle fetch_fn(), stocke le résultat et le retourne."""
    now = time.monotonic()
    with _lock:
        entry = _store.get(key)
        if entry is not None and (now - entry[0]) < ttl_s:
            return entry[1]  # type: ignore[return-value]

    value = fetch_fn()

    with _lock:
        _store[key] = (now, value)
    return value
