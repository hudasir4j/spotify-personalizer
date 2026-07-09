"""Resolve 30s preview URLs when Spotify Web API returns preview_url=null."""

import json
import re
import threading
from pathlib import Path
from typing import Dict, Optional

import requests

CACHE_PATH = Path(".cache/previews.json")
_lock = threading.Lock()
_cache: Dict[str, Optional[str]] = {}

EMBED_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; spotify-personalizer/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return {}


def _persist_cache() -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(_cache))


def _from_spotify_embed(track_id: str) -> Optional[str]:
    url = f"https://open.spotify.com/embed/track/{track_id}"
    try:
        response = requests.get(url, headers=EMBED_HEADERS, timeout=6)
        response.raise_for_status()
        match = re.search(
            r'"audioPreview"\s*:\s*\{\s*"url"\s*:\s*"([^"]+)"',
            response.text,
        )
        return match.group(1) if match else None
    except Exception:
        return None


def _from_deezer(title: str, artist: str) -> Optional[str]:
    try:
        response = requests.get(
            "https://api.deezer.com/search",
            params={"q": f"{artist} {title}", "limit": 5},
            timeout=10,
        )
        response.raise_for_status()
        for item in response.json().get("data", []):
            preview = item.get("preview")
            if preview:
                return preview
    except Exception:
        pass
    return None


def resolve_preview_url(
    track_id: str,
    *,
    title: Optional[str] = None,
    artist: Optional[str] = None,
    spotify_preview: Optional[str] = None,
) -> Optional[str]:
    """Return a playable 30s preview URL, using cache + fallbacks."""
    if spotify_preview:
        return spotify_preview

    if not track_id:
        return None

    with _lock:
        if not _cache:
            _cache.update(_load_cache())
        if track_id in _cache:
            return _cache[track_id]

    preview = _from_spotify_embed(track_id)
    if not preview and title and artist:
        preview = _from_deezer(title, artist)

    with _lock:
        _cache[track_id] = preview
        _persist_cache()

    return preview
