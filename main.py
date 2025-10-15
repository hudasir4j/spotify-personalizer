from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import lyricsgenius
import os
import re
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from collections import Counter
import time
from concurrent.futures import ThreadPoolExecutor
import requests
from langdetect import detect
from deep_translator import GoogleTranslator

import nltk

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')


load_dotenv()
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-top-read user-read-recently-played"
)

genius = lyricsgenius.Genius(GENIUS_TOKEN, timeout=10)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://spotify-personalizer.vercel.app",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_song_title(title):
    t = re.sub(r'\(.*?\)', '', title)
    t = re.sub(r'-.*', '', t)
    t = re.sub(r'\[.*?\]', '', t)
    return t.strip()

def get_song_lyrics(title, artist):
    ct = clean_song_title(title)
    try:
        song = genius.search_song(ct, artist)
        if not song or not song.lyrics:
            return None
        return song.lyrics
    except Exception:
        return None

def call_hf_sentiment(text):
    try:
        resp = requests.post(
            "https://api-inference.huggingface.co/models/tabularisai/multilingual-sentiment-analysis",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": text},
            timeout=20
        )
        result = resp.json()
        if isinstance(result, list) and result:
            label = result[0].get("label", "NEUTRAL")
            score = result[0].get("score", 0)
            if label.lower() == "negative":
                score = -score
            return score
    except Exception:
        return None
    return None

def analyze_lyrics_sentiment(lyrics):
    lines = [l.strip() for l in lyrics.split("\n") if l.strip()]
    clean_lines = []
    for line in lines:
        s = re.sub(r'\[.*?\]', '', line).strip()
        if any(k in s.lower() for k in ["contributors", "translations", "romanization", "lyrics by", "embed"]):
            continue
        if s:
            clean_lines.append(s)
    scored = []
    for line in clean_lines:
        display = line
        try:
            lang = detect(line)
            if lang != 'en':
                try:
                    translated = GoogleTranslator(source=lang, target='en').translate(line)
                    if translated and translated.lower() != line.lower():
                        display = f"{line} ({translated})"
                except Exception:
                    pass
        except Exception:
            pass
        score = call_hf_sentiment(display)
        if score is None:
            continue
        scored.append({"original": line, "display": display, "score": score})
    return scored

def get_top_words(highlight_lyrics_list):
    all_lyrics = " ".join([hl['original'] for hl in highlight_lyrics_list])
    tokens = word_tokenize(all_lyrics.lower())
    stop_words = set(stopwords.words('english'))
    tokens = [t for t in tokens if t.isalpha() and t not in stop_words]
    counts = Counter(tokens)
    return counts.most_common(10)

def map_genres_to_themes(genres, sentiment_score):
    if not genres:
        return "Unknown"
    if sentiment_score < -0.7:
        return "Heartbreak/Sadness"
    genre_text = " ".join(genres).lower()
    if any(w in genre_text for w in ['r&b','soul','neo soul','contemporary r&b']):
        return "Love/Romance"
    if any(w in genre_text for w in ['hip hop','rap','trap','drill','gangsta']):
        return "Life struggles"
    if any(w in genre_text for w in ['rock','metal','punk','grunge']):
        return "Motivation/Inspiration"
    if any(w in genre_text for w in ['gospel','christian','devotional','spiritual']):
        return "Spiritual/Devotional"
    if any(w in genre_text for w in ['folk','acoustic','singer-songwriter']):
        return "Loneliness"
    if any(w in genre_text for w in ['latin','reggaeton','salsa','bachata']):
        return "Celebration"
    if any(w in genre_text for w in ['sad','indie','alternative','emo','blues']):
        return "Heartbreak/Sadness"
    if any(w in genre_text for w in ['pop','dance','edm','house','electronic','party']):
        return "Party/Fun" if sentiment_score >= -0.3 else "Heartbreak/Sadness"
    return genres[0] if genres else "Unknown"

def process_single_track(track_tuple):
    title, artist, genres = track_tuple
    lyrics = get_song_lyrics(title, artist)
    if not lyrics:
        return None
    scored = analyze_lyrics_sentiment(lyrics)
    if not scored:
        return None
    scored.sort(key=lambda x: abs(x['score']), reverse=True)
    top = scored[0]
    sentiment_score = top['score']
    theme = map_genres_to_themes(genres, sentiment_score) if genres else "Unknown"
    return {
        "song": title,
        "artist": artist,
        "line": top['display'],
        "original": top['original'],
        "theme": theme,
        "genres": genres[:3] if genres else []
    }

@app.get("/login")
def login():
    url = sp_oauth.get_authorize_url()
    return RedirectResponse(url)

@app.get("/callback")
def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(status_code=400, content={"error":"No authorization code received"})
    return RedirectResponse(url=f"{FRONTEND_URL}/loading?code={code}")

@app.get("/api/process")
async def process_songs(code: str = None):
    try:
        if not code:
            return JSONResponse(status_code=400, content={"error":"Missing code parameter"})
        token_info = sp_oauth.get_access_token(code)
        access_token = token_info.get("access_token")
        if not access_token:
            return JSONResponse(status_code=400, content={"error":"Could not obtain access token"})
        sp = Spotify(auth=access_token)
        items = sp.current_user_top_tracks(limit=10, time_range='short_term').get("items", [])
        unique = []
        seen = set()
        for tr in items:
            title = tr.get("name")
            artist = tr.get("artists", [{}])[0].get("name")
            artist_id = tr.get("artists", [{}])[0].get("id")
            genres = []
            if artist_id:
                try:
                    artist_info = sp.artist(artist_id)
                    genres = artist_info.get("genres", [])
                except Exception:
                    genres = []
            key = f"{title.lower().strip()}_{artist.lower().strip()}"
            if key not in seen:
                unique.append((title, artist, genres))
                seen.add(key)
        start = time.time()
        results = []
        with ThreadPoolExecutor(max_workers=5) as ex:
            for res in ex.map(process_single_track, unique):
                if res:
                    results.append(res)
        top_words = get_top_words(results)
        theme_counts = Counter(r['theme'] for r in results)
        payload = {
            "highlights": results,
            "top_words": [{"word": w, "count": c} for w, c in top_words],
            "themes": [{"theme": t, "count": c} for t, c in theme_counts.most_common()],
            "total_songs": len(results)
        }
        return payload
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})