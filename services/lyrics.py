import json
import os
import re
from pathlib import Path

import lyricsgenius
import requests

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "lyrics"
LRCLIB_HEADERS = {"User-Agent": "spotify-personalizer/1.0 (local dev)"}

_genius_client = None


def init_genius(token):
    global _genius_client
    if token:
        _genius_client = lyricsgenius.Genius(
            token,
            verbose=False,
            remove_section_headers=True,
            excluded_terms=["(Remix)", "(Live)", "(Demo)"],
        )


def _ensure_cache_dir():
    if CACHE_DIR.exists() and not CACHE_DIR.is_dir():
        CACHE_DIR.unlink()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(track_id):
    _ensure_cache_dir()
    return CACHE_DIR / f"{track_id}.json"


def _read_cache(track_id):
    path = _cache_path(track_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("lyrics")
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(track_id, lyrics, source):
    path = _cache_path(track_id)
    path.write_text(
        json.dumps({"lyrics": lyrics, "source": source}, ensure_ascii=False),
        encoding="utf-8",
    )


def clean_song_title(title):
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"\[.*?\]", "", title)
    title = re.sub(r"-.*", "", title)
    return title.strip()


def _fetch_lrclib(title, artist, album, duration_sec, cached_only=False):
    params = {
        "track_name": title,
        "artist_name": artist,
        "album_name": album,
        "duration": duration_sec,
    }
    endpoint = "get-cached" if cached_only else "get"
    try:
        resp = requests.get(
            f"https://lrclib.net/api/{endpoint}",
            params=params,
            headers=LRCLIB_HEADERS,
            timeout=12 if cached_only else 20,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        lyrics = (data.get("plainLyrics") or "").strip()
        if not lyrics and data.get("syncedLyrics"):
            lyrics = _lrc_to_plain(data["syncedLyrics"])
        return lyrics or None
    except requests.RequestException as exc:
        print(f"LRCLIB fetch failed for {title}: {exc}")
        return None


def _lrc_to_plain(synced):
    lines = []
    for line in synced.splitlines():
        cleaned = re.sub(r"\[\d{2}:\d{2}\.\d{2,3}\]", "", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def _fetch_genius(title, artist):
    if not _genius_client:
        return None
    try:
        song = _genius_client.search_song(clean_song_title(title), artist)
        if song and song.lyrics:
            return song.lyrics
    except Exception as exc:
        print(f"Genius fetch failed for {title}: {exc}")
    return None


def get_song_lyrics(title, artist, album, duration_ms, track_id):
    cached = _read_cache(track_id)
    if cached:
        return cached

    duration_sec = max(1, int(duration_ms / 1000))
    source = None

    lyrics = _fetch_lrclib(title, artist, album, duration_sec, cached_only=True)
    if lyrics:
        source = "lrclib"
    if not lyrics:
        lyrics = _fetch_lrclib(title, artist, album, duration_sec, cached_only=False)
        if lyrics:
            source = "lrclib"
    if not lyrics:
        lyrics = _fetch_genius(title, artist)
        if lyrics:
            source = "genius"

    if lyrics:
        _write_cache(track_id, lyrics, source or "unknown")
    return lyrics
