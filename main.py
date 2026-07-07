import os
import hashlib
import json
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

if os.environ.get("PYTHON_ENV") == "local":
    load_dotenv(".env.local")

from services.analysis import assign_aesthetic_vibe, get_top_words, pick_iconic_line
from services.lyrics import get_song_lyrics, init_genius

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")

init_genius(GENIUS_TOKEN)

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-top-read user-read-recently-played",
    cache_path=".spotify_token_cache",
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_data = {}
session_lock = threading.Lock()
_startup_locks = {}
_startup_locks_guard = threading.Lock()
VALID_TIME_RANGES = {"short_term", "medium_term", "long_term"}
SESSION_DIR = Path(".cache/sessions")


def _save_session(session_id):
    with session_lock:
        session = session_data.get(session_id)
        if not session:
            return
        payload = {
            **session,
            "timestamp": session["timestamp"].isoformat(),
        }
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    (SESSION_DIR / f"{session_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def _load_sessions():
    if not SESSION_DIR.exists():
        return
    cutoff = datetime.now() - timedelta(hours=2)
    for path in SESSION_DIR.glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            ts = datetime.fromisoformat(raw["timestamp"])
            if ts < cutoff:
                path.unlink(missing_ok=True)
                continue
            raw["timestamp"] = ts
            session_data[path.stem] = raw
        except (json.JSONDecodeError, OSError, KeyError, ValueError):
            path.unlink(missing_ok=True)


_load_sessions()


def _get_startup_lock(session_id):
    with _startup_locks_guard:
        if session_id not in _startup_locks:
            _startup_locks[session_id] = threading.Lock()
        return _startup_locks[session_id]


def _session_response(session_id, session):
    return {
        "status": session["status"],
        "session_id": session_id,
        "total": session["progress"]["total"],
        "requested_limit": session.get("requested_limit"),
        "duplicates_skipped": session.get("duplicates_skipped", 0),
        "time_range": session.get("time_range"),
        "resumed": True,
    }


def clean_old_sessions():
    cutoff = datetime.now() - timedelta(hours=2)
    with session_lock:
        stale = [s for s, v in session_data.items() if v["timestamp"] < cutoff]
        for key in stale:
            del session_data[key]
            path = SESSION_DIR / f"{key}.json"
            if path.exists():
                path.unlink()


def _update_aggregates(highlights):
    themes = [h["theme"] for h in highlights]
    counts = Counter(themes)
    return {
        "highlights": highlights,
        "themes": [{"theme": k, "count": v} for k, v in counts.items()],
        "top_words": get_top_words(highlights) if highlights else [],
    }


def _process_track(track, genre_cache):
    title, artist, track_id, album, duration_ms, artist_id, access_token, album_art = track
    try:
        sp = None
        try:
            sp = Spotify(auth=access_token)
        except Exception:
            pass

        if artist_id in genre_cache:
            genres = genre_cache[artist_id]
        elif sp:
            try:
                genres = sp.artist(artist_id).get("genres", [])
            except Exception:
                genres = []
            genre_cache[artist_id] = genres
        else:
            genres = []
            genre_cache[artist_id] = genres

        lyrics = get_song_lyrics(title, artist, album, duration_ms, track_id)
        if not lyrics:
            return None

        line, raw_theme = pick_iconic_line(lyrics)
        if not line:
            return None

        audio = None
        if sp:
            try:
                features = sp.audio_features([track_id])
                if features and features[0]:
                    audio = features[0]
            except Exception:
                audio = None

        return {
            "song": title,
            "artist": artist,
            "line": line,
            "theme": assign_aesthetic_vibe(
                title, artist, line, raw_theme, genres, lyrics, audio
            ),
            "genres": genres[:3],
            "album_art": album_art,
            "track_id": track_id,
        }
    except Exception as exc:
        print(f"Failed to process {title} by {artist}: {exc}")
        return None


def run_analysis(session_id, track_data):
    highlights = []
    genre_cache = {}
    start = time.time()

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_process_track, track, genre_cache): track
            for track in track_data
        }
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as exc:
                print(f"Track worker error: {exc}")
                result = None
            with session_lock:
                session = session_data.get(session_id)
                if not session:
                    return
                session["progress"]["done"] += 1
                if result:
                    highlights.append(result)
                    session["data"] = _update_aggregates(highlights)
            _save_session(session_id)

    with session_lock:
        session = session_data.get(session_id)
        if session:
            session["status"] = "complete"
            session["timestamp"] = datetime.now()
    _save_session(session_id)

    print(
        f"Session {session_id}: processed {len(highlights)}/{len(track_data)} "
        f"tracks in {round(time.time() - start, 2)}s"
    )


@app.get("/login")
def login():
    return RedirectResponse(sp_oauth.get_authorize_url())


@app.get("/callback")
def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "Missing code"}
    return RedirectResponse(f"{FRONTEND_URL}/loading?code={code}")


@app.get("/api/process")
def process_songs(
    code: str,
    background_tasks: BackgroundTasks,
    time_range: str = "medium_term",
    limit: int = 50,
):
    if time_range not in VALID_TIME_RANGES:
        return JSONResponse(
            status_code=400,
            content={"error": f"time_range must be one of {sorted(VALID_TIME_RANGES)}"},
        )

    limit = max(1, min(50, limit))
    session_id = hashlib.md5(f"{code}:{time_range}:{limit}".encode()).hexdigest()

    with session_lock:
        existing = session_data.get(session_id)
        if existing:
            return _session_response(session_id, existing)

    startup_lock = _get_startup_lock(session_id)
    with startup_lock:
        with session_lock:
            existing = session_data.get(session_id)
            if existing:
                return _session_response(session_id, existing)

        try:
            token = sp_oauth.get_access_token(code)
            sp = Spotify(auth=token["access_token"])
            top_tracks = sp.current_user_top_tracks(
                limit=limit,
                time_range=time_range,
            )["items"]

            track_data = []
            seen_ids = set()
            for track in top_tracks:
                track_id = track["id"]
                if track_id in seen_ids:
                    continue
                seen_ids.add(track_id)
                title = track["name"]
                artist = track["artists"][0]["name"]
                artist_id = track["artists"][0]["id"]
                album = track["album"]["name"]
                duration_ms = track.get("duration_ms", 0)
                images = track.get("album", {}).get("images") or []
                album_art = images[0]["url"] if images else None
                track_data.append(
                    (
                        title,
                        artist,
                        track_id,
                        album,
                        duration_ms,
                        artist_id,
                        token["access_token"],
                        album_art,
                    )
                )

            total = len(track_data)
            duplicates_skipped = len(top_tracks) - total

            with session_lock:
                session_data[session_id] = {
                    "status": "processing",
                    "progress": {"done": 0, "total": total},
                    "data": {"highlights": [], "themes": [], "top_words": []},
                    "time_range": time_range,
                    "requested_limit": limit,
                    "duplicates_skipped": duplicates_skipped,
                    "timestamp": datetime.now(),
                }

            clean_old_sessions()
            _save_session(session_id)
            background_tasks.add_task(run_analysis, session_id, track_data)

            return {
                "status": "processing",
                "session_id": session_id,
                "total": total,
                "requested_limit": limit,
                "duplicates_skipped": duplicates_skipped,
                "time_range": time_range,
            }
        except Exception as exc:
            error_text = str(exc)
            if "invalid_grant" in error_text:
                with session_lock:
                    existing = session_data.get(session_id)
                    if existing:
                        return _session_response(session_id, existing)
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Login expired — please go back and log in again.",
                    },
                )
            return JSONResponse(status_code=500, content={"error": error_text})


@app.get("/api/results")
def get_results(session_id: str):
    with session_lock:
        session = session_data.get(session_id)
        if not session:
            return JSONResponse(status_code=404, content={"error": "No data available"})
        payload = {
            **session["data"],
            "status": session["status"],
            "progress": session["progress"],
            "time_range": session.get("time_range"),
            "total_songs": len(session["data"]["highlights"]),
        }
    return payload


@app.get("/")
def root():
    return {"status": "ok", "active_sessions": len(session_data)}
