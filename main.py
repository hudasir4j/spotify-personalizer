from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import hashlib
from collections import Counter
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# NLTK setup
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# .env Variables
if os.environ.get("PYTHON_ENV") == "local":
    load_dotenv(".env.local")

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

genius = lyricsgenius.Genius(GENIUS_TOKEN)
sp_oauth = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-top-read user-read-recently-played"
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- SESSION MANAGEMENT ----------
session_data = {}

def clean_old_sessions():
    cutoff = datetime.now() - timedelta(hours=2)
    stale = [s for s, v in session_data.items() if v["timestamp"] < cutoff]
    for key in stale:
        del session_data[key]

# ---------- HELPERS ----------
def clean_song_title(title):
    title = re.sub(r'\(.*?\)', '', title)
    title = re.sub(r'\[.*?\]', '', title)
    title = re.sub(r'-.*', '', title)
    return title.strip()

def get_song_lyrics(title, artist):
    try:
        song = genius.search_song(clean_song_title(title), artist)
        if not song or not song.lyrics:
            return None
        lyrics = re.sub(r'\[.*?\]', '', song.lyrics)
        lyrics = re.sub(r'\d+\s+Contributors?.*', '', lyrics)
        lyrics = re.sub(r'Embed', '', lyrics)
        lyrics = lyrics.strip()
        return lyrics
    except Exception as e:
        print("Error getting lyrics:", e)
        return None

def analyze_lyrics(lyrics):
    lines = [l.strip() for l in lyrics.split('\n') if len(l.strip()) > 15]
    if not lines:
        return "", []
    emotion_themes = ["love", "loss", "hope", "joy", "nostalgia", "heartbreak"]
    import random
    return random.choice(lines), [random.choice(emotion_themes)]

def map_to_aesthetic_theme(theme):
    mapping = {
        "love": ["hopeless romantic era", "falling in love"],
        "loss": ["moving on playlist"],
        "hope": ["new chapter unlocked"],
        "joy": ["main character moment"],
        "nostalgia": ["missing what used to be"],
        "heartbreak": ["healing journey"]
    }
    import random
    return random.choice(mapping.get(theme, ["feeling everything"]))

def get_top_words(highlights):
    text = " ".join([h["line"] for h in highlights])
    tokens = word_tokenize(text.lower())
    tokens = [t for t in tokens if t.isalpha() and t not in stopwords.words("english")]
    return Counter(tokens).most_common(10)

def process_track(info):
    title, artist, genres = info
    lyrics = get_song_lyrics(title, artist)
    if not lyrics:
        return None
    line, themes = analyze_lyrics(lyrics)
    return {"song": title, "artist": artist, "line": line, "theme": themes[0], "genres": genres[:3]}

# ---------- ROUTES ----------
@app.get("/login")
def login():
    return RedirectResponse(sp_oauth.get_authorize_url())

@app.get("/callback")
def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "Missing code"}
    return RedirectResponse(f"{os.getenv('FRONTEND_URL')}/loading?code={code}")

@app.get("/api/process")
def process_songs(code: str):
    try:
        token = sp_oauth.get_access_token(code)
        sp = Spotify(auth=token["access_token"])
        top_tracks = sp.current_user_top_tracks(limit=10)["items"]

        track_data = []
        seen = set()
        for t in top_tracks:
            title = t["name"]
            artist = t["artists"][0]["name"]
            artist_id = t["artists"][0]["id"]
            if f"{title.lower()}_{artist.lower()}" in seen:
                continue
            genres = sp.artist(artist_id).get("genres", [])
            track_data.append((title, artist, genres))
            seen.add(f"{title.lower()}_{artist.lower()}")

        start = time.time()
        with ThreadPoolExecutor(max_workers=5) as ex:
            results = list(ex.map(process_track, track_data))
        highlights = [r for r in results if r]

        themes = [map_to_aesthetic_theme(h["theme"]) for h in highlights]
        counts = Counter(themes)
        top_words = get_top_words(highlights)

        session_id = hashlib.md5(code.encode()).hexdigest()
        session_data[session_id] = {
            "data": {
                "highlights": highlights,
                "themes": [{"theme": k, "count": v} for k, v in counts.items()],
                "top_words": top_words
            },
            "timestamp": datetime.now()
        }
        clean_old_sessions()
        print(f"Processed {len(highlights)} tracks in {round(time.time() - start, 2)}s")
        return {"status": "complete", "session_id": session_id}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/results")
def get_results(session_id: str):
    if session_id not in session_data:
        return JSONResponse(status_code=404, content={"error": "No data available"})
    data = session_data[session_id]["data"]
    return {**data, "total_songs": len(data["highlights"])}

@app.get("/")
def root():
    return {"status": "ok", "active_sessions": len(session_data)}
