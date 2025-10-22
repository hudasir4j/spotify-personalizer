from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import lyricsgenius
import os
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from collections import Counter

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk

import requests

#NLTK setup
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
else:
    load_dotenv(".env")


CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# Debug prints
print(f"🔍 REDIRECT_URI: {REDIRECT_URI}")
print(f"🔍 FRONTEND_URL: {os.getenv('FRONTEND_URL')}")
print(f"🔍 CLIENT_ID: {CLIENT_ID[:10]}..." if CLIENT_ID else "None")

# Spotipy & Genius Setup
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-top-read user-read-recently-played"
)

genius = lyricsgenius.Genius(GENIUS_TOKEN)

# Fast API
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper Functions
def clean_song_title(title):
    title = re.sub(r'\(.*?\)', '', title)
    title = re.sub(r'-.*', '', title)
    title = re.sub(r'\[.*?\]', '', title)
    return title.strip()

def get_song_lyrics(title, artist):
    try:
        clean_title = clean_song_title(title)
        song = genius.search_song(clean_title, artist)
        if not song or not song.lyrics:
            return None
        
        lyrics = song.lyrics
        
        # Remove common Genius metadata patterns
        # Remove "X Contributors" lines
        lyrics = re.sub(r'\d+\s+Contributors?.*?(?=\n|$)', '', lyrics, flags=re.IGNORECASE)
        
        # Remove "Translations" references
        lyrics = re.sub(r'Translations\w*', '', lyrics, flags=re.IGNORECASE)
        
        # Remove "Romanization" references
        lyrics = re.sub(r'Romanization', '', lyrics, flags=re.IGNORECASE)
        
        # Remove song title repetitions (usually at the start)
        lyrics = re.sub(r'^.*?Lyrics', '', lyrics, flags=re.IGNORECASE)
        
        # Remove section headers like [Verse 1], [Chorus], [Intro: Artist]
        lyrics = re.sub(r'\[.*?\]', '', lyrics)
        
        # Remove "Embed" and other metadata
        lyrics = re.sub(r'\bEmbed\b', '', lyrics, flags=re.IGNORECASE)
        
        # Remove "See ... LiveGet tickets as low as $X"
        lyrics = re.sub(r'See.*?Live.*?\$\d+', '', lyrics, flags=re.IGNORECASE)
        
        # Remove extra whitespace and clean up
        lyrics = re.sub(r'\n\s*\n', '\n', lyrics)  # Multiple newlines to single
        lyrics = re.sub(r'^\s+', '', lyrics, flags=re.MULTILINE)  # Leading spaces
        lyrics = lyrics.strip()
        
        return lyrics if lyrics else None
        
    except Exception as e:
        print(f"Error fetching lyrics: {e}")
        return None

def get_top_words(highlight_lyrics_list):
    all_text = " ".join([hl['line'] for hl in highlight_lyrics_list])
    tokens = word_tokenize(all_text.lower())
    stop_words = set(stopwords.words('english'))
    tokens = [t for t in tokens if t.isalpha() and t not in stop_words]
    word_counts = Counter(tokens)
    return word_counts.most_common(10)

def analyze_lyrics(lyrics):
    if not lyrics:
        return "", []
    
    lines = [line.strip() for line in lyrics.split('\n') 
             if line.strip() 
             and len(line.strip()) > 15 
             and not line.strip().isdigit()
             and not re.match(r'^[\W_]+$', line.strip())
             ]
    
    if not lines:
        return "", []
    
    import random
    
    emotion_themes = ["love", "heartbreak", "nostalgia", "hope", "longing", "joy", "melancholy", "desire", "loss", "passion"]
    
    return lines[0], [random.choice(emotion_themes)]

def map_to_aesthetic_theme(emotion_theme):
    theme_mapping = {
        "love": ["hopeless romantic era", "falling in love energy", "soft life vibes"],
        "heartbreak": ["sad girl/boy autumn", "getting over it playlist", "healing journey"],
        "nostalgia": ["yearning hours", "missing what used to be", "living in memories"],
        "hope": ["main character energy", "new chapter unlocked", "manifesting good things"],
        "longing": ["yearning hours", "wanting what you can't have", "3am thoughts"],
        "joy": ["living your best life", "main character moment", "dancing alone energy"],
        "melancholy": ["feeling everything at once", "soft and vulnerable", "crying in the car"],
        "desire": ["manifesting energy", "wanting more", "chasing feelings"],
        "loss": ["moving on playlist", "outgrowing people", "emotional damage"],
        "passion": ["living for the drama", "feeling everything", "too much emotion"]
    }
    
    import random
    emotion = emotion_theme.lower()
    
    if emotion in theme_mapping:
        return random.choice(theme_mapping[emotion])
    else:
        fallback = [
            "3am overthinking", "feeling everything", "life in transition",
            "becoming someone new", "chaos and calm", "emotional rollercoaster"
        ]
        return random.choice(fallback)

def process_single_track(track_info):
    title, artist, genres = track_info
    lyrics = get_song_lyrics(title, artist)
    if not lyrics:
        return None
    line, themes = analyze_lyrics(lyrics)
    if not line:
        return None

    theme_label = themes[0] if themes else "Unknown"
    return {
        "song": title,
        "artist": artist,
        "line": line,
        "theme": theme_label,
        "genres": genres[:3] if genres else [],
    }

# Routes
@app.get("/login")
def login():
    return RedirectResponse(sp_oauth.get_authorize_url())

@app.get("/callback")
def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "No authorization code received"}
    return RedirectResponse(url=f"{os.getenv('FRONTEND_URL')}/loading?code={code}")

@app.get("/api/process")
async def process_songs(code: str):
    try:
        token_info = sp_oauth.get_access_token(code)
        access_token = token_info["access_token"]
        sp = Spotify(auth=access_token)

        top_tracks = sp.current_user_top_tracks(limit=10, time_range='short_term')["items"]

        track_list = []
        seen = set()
        for track in top_tracks:
            title = track['name']
            artist = track['artists'][0]['name']
            artist_id = track['artists'][0]['id']
            try:
                genres = sp.artist(artist_id).get('genres', [])
            except:
                genres = []

            key = f"{title.lower()}_{artist.lower()}"
            if key not in seen:
                track_list.append((title, artist, genres))
                seen.add(key)

        highlights = []
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_single_track, track_list))

        highlights = [r for r in results if r]
        end_time = time.time()
        print(f"Processed {len(highlights)} tracks in {round(end_time - start_time, 2)}s")

        # Map emotion themes to aesthetic themes for the recurring themes section
        aesthetic_themes = [map_to_aesthetic_theme(h['theme']) for h in highlights]
        theme_counts = Counter(aesthetic_themes)

        # Top words
        top_words = get_top_words(highlights)

        # Store in-memory for /api/results
        app.state.highlights = highlights
        app.state.top_words = top_words
        app.state.themes = [{"theme": k, "count": v} for k, v in theme_counts.most_common()]

        return {"status": "complete", "count": len(highlights)}

    except Exception as e:
        return {"error": str(e)}

@app.get("/api/results")
def get_results():
    highlights = getattr(app.state, "highlights", [])
    top_words = getattr(app.state, "top_words", [])
    themes = getattr(app.state, "themes", [])

    if not highlights:
        return JSONResponse(status_code=404, content={"error": "No data available"})

    return {
        "highlights": highlights,
        "top_words": [{"word": w, "count": c} for w, c in top_words],
        "themes": themes,
        "total_songs": len(highlights)
    }