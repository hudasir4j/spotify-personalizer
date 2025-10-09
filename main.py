from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
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
import string
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

from transformers import pipeline
from langdetect import detect, LangDetectException
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

sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model = "tabularisai/multilingual-sentiment-analysis"
)

theme_classifier = pipeline("zero-shot-classification")

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

load_dotenv()
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")
LOADING_URL = os.getenv("LOADING_URL")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")

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
    allow_origins=["http://localhost:3000","https://spotify-personalizer.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_song_title(title):
    clean_title = re.sub(r'\(.*?\)', '', title)
    clean_title = re.sub(r'-.*', '', clean_title)
    clean_title = re.sub(r'\[.*?\]', '', clean_title)
    return clean_title.strip()

def get_song_lyrics(title, artist):
    clean_title = clean_song_title(title)
    try:
        print(f"Searching for '{clean_title}' by '{artist}'")
        song = genius.search_song(clean_title, artist)
        if not song or not song.lyrics:
            print(f"Could not find lyrics for: {title} by {artist}")
            return None
        return song.lyrics
    except Exception as e:
        print(f"Error fetching lyrics for {title}: {e}")
        return None

def analyze_lyrics_sentiment(lyrics):
    lines = [line.strip() for line in lyrics.split("\n") if line.strip()]

    clean_lines = []
    for line in lines:
        line = re.sub(r'\[.*?\]', '', line).strip()
        if any(keyword.lower() in line.lower() for keyword in [
            "contributors", "translations", "romanization", "lyrics by", "embed"
        ]):
            continue
        if line:
            clean_lines.append(line)
    
    scored_lines = []
    for line in clean_lines:
        try:
            result = sentiment_pipeline(line)[0]
            score = result['score']
            if result['label'].lower() == "negative":
                score = -score

            display_text = line
            try: 
                lang = detect(line)
                if lang != 'en':
                    try:
                        translated_text = GoogleTranslator(source=lang, target='en').translate(line)
                        
                        if translated_text and translated_text.lower() != line.lower():
                            display_text = f"{line} ({translated_text})"
                            
                    except Exception as e:
                        print(f"Translation failed for '{line[:30]}...': {e}")
            except (LangDetectException, Exception):
                pass

            scored_lines.append({
                'original': line, 
                'display': display_text, 
                'score': score
            })
        
        except Exception as e:
            print(f"Error analyzing line '{line}': {e}")
            continue
    
    return scored_lines

def get_top_words(highlight_lyrics_list):
    all_lyrics = " ".join([hl['original'] for hl in highlight_lyrics_list])
    tokens = word_tokenize(all_lyrics.lower())
    stop_words = set(stopwords.words('english'))
    tokens = [t for t in tokens if t.isalpha() and t not in stop_words]
    word_counts = Counter(tokens)
    return word_counts.most_common(10)

def map_genres_to_themes(genres, sentiment_score):
    if not genres:
        return "Unknown"
    
    if sentiment_score < -0.7:
        return "Heartbreak/Sadness"
    
    genre_text = " ".join(genres).lower()
    
    if any(word in genre_text for word in ['r&b', 'soul', 'neo soul', 'contemporary r&b']):
        return "Love/Romance"
    elif any(word in genre_text for word in ['hip hop', 'rap', 'trap', 'drill', 'gangsta']):
        return "Life struggles"
    elif any(word in genre_text for word in ['rock', 'metal', 'punk', 'grunge']):
        return "Motivation/Inspiration"
    elif any(word in genre_text for word in ['gospel', 'christian', 'devotional', 'spiritual']):
        return "Spiritual/Devotional"
    elif any(word in genre_text for word in ['folk', 'acoustic', 'singer-songwriter']):
        return "Loneliness"
    elif any(word in genre_text for word in ['latin', 'reggaeton', 'salsa', 'bachata']):
        return "Celebration"
    elif any(word in genre_text for word in ['sad', 'indie', 'alternative', 'emo', 'blues']):
        return "Heartbreak/Sadness"
    elif any(word in genre_text for word in ['pop', 'dance', 'edm', 'house', 'electronic', 'party']):
        if sentiment_score < -0.3:
            return "Heartbreak/Sadness"
        else:
            return "Party/Fun"
    else:
        return genres[0] if genres else "Unknown"

def process_single_track(track_info):
    title, artist, genres = track_info
    
    print(f"Processing: {title} by {artist}")
    
    lyrics = get_song_lyrics(title, artist)
    if not lyrics:
        return None
        
    scored_lines = analyze_lyrics_sentiment(lyrics)
    if not scored_lines:
        print(f"No valid lines found for {title}")
        return None
    
    scored_lines.sort(key=lambda x: abs(x['score']), reverse=True)
    most_emotional_line = scored_lines[0]
    sentiment_score = most_emotional_line['score']
    
    theme = map_genres_to_themes(genres, sentiment_score) if genres else "Unknown"
    
    return {
        'song': title,
        'artist': artist,
        'line': most_emotional_line['display'],
        'original': most_emotional_line['original'],
        'theme': theme,
        'genres': genres[:3] if genres else []
    }

@app.get("/login")
def login():
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)

@app.get("/callback")
def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "No authorization code received"}
    
    return RedirectResponse(url=f"{LOADING_URL}?code={code}")

@app.get("/api/process")
async def process_songs(code: str):
    try:
        token_info = sp_oauth.get_access_token(code)
        access_token = token_info["access_token"]

        sp = Spotify(auth=access_token)
        top_tracks = sp.current_user_top_tracks(limit=10, time_range='short_term')["items"]

        highlight_lyrics.clear()
        total_songs = len(top_tracks)
        
        unique_tracks = []
        seen_songs = set()
        for track in top_tracks:
            title = track['name']
            artist = track['artists'][0]['name']
            
            artist_id = track['artists'][0]['id']
            try:
                artist_info = sp.artist(artist_id)
                genres = artist_info['genres']
            except:
                genres = []
            
            song_key = f"{title.lower().strip()}_{artist.lower().strip()}"
            
            if song_key not in seen_songs:
                unique_tracks.append((title, artist, genres))
                seen_songs.add(song_key)
            else:
                print(f"Skipping duplicate: {title} by {artist}")
        
        print(f"Processing {len(unique_tracks)} unique tracks out of {total_songs} total...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_single_track, unique_tracks))
        
        successful_results = [result for result in results if result is not None]
        highlight_lyrics.extend(successful_results)
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        successful_analyses = len(successful_results)
        
        print(f"Successfully analyzed {successful_analyses}/{len(unique_tracks)} tracks in {processing_time} seconds")

        return {"status": "complete", "count": successful_analyses}
        
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

@app.get("/api/results")
def get_results():
    if not highlight_lyrics:
        return JSONResponse(
            status_code=404,
            content={"error": "No data available"}
        )
    
    top_words = get_top_words(highlight_lyrics)
    theme_counts = Counter(hl['theme'] for hl in highlight_lyrics)
    
    return {
        "highlights": highlight_lyrics,
        "top_words": [{"word": word, "count": count} for word, count in top_words],
        "themes": [{"theme": theme, "count": count} for theme, count in theme_counts.most_common()],
        "total_songs": len(highlight_lyrics)
    }