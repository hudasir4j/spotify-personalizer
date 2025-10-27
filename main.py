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
import requests


for resource in ["stopwords", "punkt", "punkt_tab"]:
    try:
        nltk.data.find(resource)
    except LookupError:
        nltk.download(resource)


if os.environ.get("PYTHON_ENV") == "local":
    load_dotenv(".env.local")


CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")


sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
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


session_data = {}


def clean_old_sessions():
    cutoff = datetime.now() - timedelta(hours=2)
    stale = [s for s, v in session_data.items() if v["timestamp"] < cutoff]
    for key in stale:
        del session_data[key]


def clean_song_title(title):
    title = re.sub(r'\(.*?\)', '', title)
    title = re.sub(r'\[.*?\]', '', title)
    title = re.sub(r'-.*', '', title)
    return title.strip()


def get_song_lyrics(track_id, user_access_token):
    url = f"https://spclient.wg.spotify.com/color-lyrics/v2/track/{track_id}?format=json&vocalRemoval=false"
    headers = {
        "app-platform": "WebPlayer",
        "authorization": f"Bearer {user_access_token}"
    }
    print(f"Fetching lyrics for track {track_id} with token length {len(user_access_token)}")
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"Lyrics fetch response code: {resp.status_code}")
    
    if resp.status_code != 200:
        print("Lyrics fetch failed response text:", resp.text)
        return None
    try:
        data = resp.json()
        lines = data["lyrics"]["lines"]
        lyric_text = "\n".join([line.get("words", "") for line in lines])
        return lyric_text
    except Exception as e:
        print("Error parsing lyrics JSON:", e)
        print("Response content:", resp.text)
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
        "love": ["hopeless romantic", "crushing", "yearning"],
        "loss": ["moving on playlist"],
        "hope": ["romanticizing life"],
        "joy": ["main character"],
        "nostalgia": ["missing what used to be", "unc", "reminiscing"],
        "heartbreak": ["it's ok i'm ok", "thugging it out"]
    }
    import random
    return random.choice(mapping.get(theme, ["feeling everything"]))


def get_top_words(highlights):
    text = " ".join([h["line"] for h in highlights])
    tokens = word_tokenize(text.lower())
    tokens = [t for t in tokens if t.isalpha() and t not in stopwords.words("english")]
    return Counter(tokens).most_common(10)


def process_track(info):
    title, artist, track_id, genres, user_access_token = info
    lyrics = get_song_lyrics(track_id, user_access_token)
    if not lyrics:
        return None
    line, themes = analyze_lyrics(lyrics)
    return {"song": title, "artist": artist, "line": line, "theme": themes[0], "genres": genres[:3]}


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
def process_songs(code: str):
    try:
        token = sp_oauth.get_access_token(code)
        print(f"Obtained Spotify token: {token}")
        sp = Spotify(auth=token["access_token"])
        top_tracks = sp.current_user_top_tracks(limit=10)["items"]
        track_data = []
        seen = set()
        for t in top_tracks:
            title = t["name"]
            artist = t["artists"][0]["name"]
            artist_id = t["artists"][0]["id"]
            track_id = t["id"]
            if f"{title.lower()}_{artist.lower()}" in seen:
                continue
            genres = sp.artist(artist_id).get("genres", [])
            track_data.append((title, artist, track_id, genres, token["access_token"]))
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
