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
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator
import nltk
import requests
from concurrent.futures import ThreadPoolExecutor
import time

# NLTK downloads
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

load_dotenv()
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")
LOADING_URL = os.getenv("LOADING_URL")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-top-read user-read-recently-played"
)

genius = lyricsgenius.Genius(GENIUS_TOKEN)
highlight_lyrics = []

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

candidate_themes = [
    "Love/Romance",
    "Heartbreak/Sadness",
    "Party/Fun",
    "Motivation/Inspiration",
    "Spiritual/Devotional",
    "Friendship",
    "Loneliness",
    "Celebration",
    "Life struggles"
]

headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

def sentiment_analysis(text):
    payload = {"inputs": text}
    response = requests.post(
        "https://api-inference.huggingface.co/models/tabularisai/multilingual-sentiment-analysis",
        headers=headers,
        json=payload
    )
    result = response.json()
    return result[0] if isinstance(result, list) else None

def classify_theme(text, candidate_labels):
    payload = {"inputs": text, "parameters": {"candidate_labels": candidate_labels}}
    response = requests.post(
        "https://api-inference.huggingface.co/models/facebook/bart-large-mnli",
        headers=headers,
        json=payload
    )
    result = response.json()
    return result

def clean_song_title(title):
    clean_title = re.sub(r'\(.*?\)', '', title)
    clean_title = re.sub(r'-.*', '', clean_title)
    clean_title = re.sub(r'\[.*?\]', '', clean_title)
    return clean_title.strip()

def get_song_lyrics(title, artist):
    clean_title = clean_song_title(title)
    try:
        song = genius.search_song(clean_title, artist)
        return song.lyrics if song and song.lyrics else None
    except Exception:
        return None

def analyze_lyrics_sentiment(lyrics):
    lines = [line.strip() for line in lyrics.split("\n") if line.strip()]
    clean_lines = [line for line in lines if not any(
        kw in line.lower() for kw in ["contributors", "translations", "romanization", "lyrics by", "embed"]
    )]
    scored_lines = []
    for line in clean_lines:
        try:
            result = sentiment_analysis(line)
            if not result:
                continue
            score = -result['score'] if result['label'].lower() == "negative" else result['score']
            display_text = line
            try:
                lang = detect(line)
                if lang != 'en':
                    translated_text = GoogleTranslator(source=lang, target='en').translate(line)
                    if translated_text and translated_text.lower() != line.lower():
                        display_text = f"{line} ({translated_text})"
            except Exception:
                pass
            scored_lines.append({'original': line, 'display': display_text, 'score': score})
        except Exception:
            continue
    return scored_lines

def get_top_words(highlight_lyrics_list):
    all_lyrics = " ".join([hl['original'] for hl in highlight_lyrics_list])
    tokens = [t for t in word_tokenize(all_lyrics.lower()) if t.isalpha()]
    stop_words = set(stopwords.words('english'))
    tokens = [t for t in tokens if t not in stop_words]
    return Counter(tokens).most_common(10)

def map_genres_to_themes(genres, sentiment_score):
    if not genres:
        return "Unknown"
    if sentiment_score < -0.7:
        return "Heartbreak/Sadness"
    genre_text = " ".join(genres).lower()
    if any(w in genre_text for w in ['r&b', 'soul', 'neo soul', 'contemporary r&b']):
        return "Love/Romance"
    elif any(w in genre_text for w in ['hip hop', 'rap', 'trap', 'drill', 'gangsta']):
        return "Life struggles"
    elif any(w in genre_text for w in ['rock', 'metal', 'punk', 'grunge']):
        return "Motivation/Inspiration"
    elif any(w in genre_text for w in ['gospel', 'christian', 'devotional', 'spiritual']):
        return "Spiritual/Devotional"
    elif any(w in genre_text for w in ['folk', 'acoustic', 'singer-songwriter']):
        return "Loneliness"
    elif any(w in genre_text for w in ['latin', 'reggaeton', 'salsa', 'bachata']):
        return "Celebration"
    elif any(w in genre_text for w in ['sad', 'indie', 'alternative', 'emo', 'blues']):
        return "Heartbreak/Sadness"
    elif any(w in genre_text for w in ['pop', 'dance', 'edm', 'house', 'electronic', 'party']):
        return "Heartbreak/Sadness" if sentiment_score < -0.3 else "Party/Fun"
    return genres[0]

def process_single_track(track_info):
    title, artist, genres = track_info
    lyrics = get_song_lyrics(title, artist)
    if not lyrics:
        return None
    scored_lines = analyze_lyrics_sentiment(lyrics)
    if not scored_lines:
        return None
    scored_lines.sort(key=lambda x: abs(x['score']), reverse=True)
    top_line = scored_lines[0]
    sentiment_score = top_line['score']
    theme_result = classify_theme(top_line['original'], candidate_themes)
    theme = theme_result.get('labels', [map_genres_to_themes(genres, sentiment_score)])[0] if theme_result else map_genres_to_themes(genres, sentiment_score)
    return {'song': title, 'artist': artist, 'line': top_line['display'], 'original': top_line['original'], 'theme': theme, 'genres': genres[:3] if genres else []}

@app.get("/login")
def login():
    return RedirectResponse(sp_oauth.get_authorize_url())

@app.get("/callback")
def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "No authorization code"}
    return RedirectResponse(f"{LOADING_URL}?code={code}")

@app.get("/api/process")
async def process_songs(code: str):
    try:
        token_info = sp_oauth.get_access_token(code)
        sp = Spotify(auth=token_info["access_token"])
        top_tracks = sp.current_user_top_tracks(limit=10, time_range='short_term')["items"]
        highlight_lyrics.clear()
        unique_tracks = []
        seen = set()
        for t in top_tracks:
            title = t['name']
            artist = t['artists'][0]['name']
            genres = sp.artist(t['artists'][0]['id']).get('genres', [])
            key = f"{title.lower().strip()}_{artist.lower().strip()}"
            if key not in seen:
                unique_tracks.append((title, artist, genres))
                seen.add(key)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(process_single_track, unique_tracks))
        highlight_lyrics.extend([r for r in results if r])
        return {"status": "complete", "count": len(highlight_lyrics)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/results")
def get_results():
    if not highlight_lyrics:
        return JSONResponse(status_code=404, content={"error": "No data available"})
    top_words = get_top_words(highlight_lyrics)
    theme_counts = Counter(hl['theme'] for hl in highlight_lyrics)
    return {
        "highlights": highlight_lyrics,
        "top_words": [{"word": w, "count": c} for w, c in top_words],
        "themes": [{"theme": t, "count": c} for t, c in theme_counts.most_common()],
        "total_songs": len(highlight_lyrics)
    }
