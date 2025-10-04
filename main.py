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
import string
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

from transformers import pipeline
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

#load in all pipelines
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model = "tabularisai/multilingual-sentiment-analysis"
)

import nltk
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

theme_classifier = pipeline("zero-shot-classification")

#theme groups
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

# Spotify oAuth
load_dotenv()
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
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

# React - Python conversation; CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper Functions

def clean_song_title(title):
    # clean text to make genius results more accurate
    clean_title = re.sub(r'\(.*?\)', '', title)  # remove (feat. xyz)
    clean_title = re.sub(r'-.*', '', clean_title)  # remove - remix text
    clean_title = re.sub(r'\[.*?\]', '', clean_title)  # remove [explicit] etc
    return clean_title.strip()

def get_song_lyrics(title, artist):
    # fetch lyrics
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
    #seperating lines and striping white spaces
    lines = [line.strip() for line in lyrics.split("\n") if line.strip()]

    #cleaning data for only useful lyrics
    clean_lines = []
    for line in lines:
        line = re.sub(r'\[.*?\]', '', line).strip()
        if any(keyword.lower() in line.lower() for keyword in [
            "contributors", "translations", "romanization", "lyrics by", "embed"
        ]):
            continue
        if line:
            clean_lines.append(line)
    
    #scoring lines for sentiment analysis
    scored_lines = []
    for line in clean_lines:
        try:
            result = sentiment_pipeline(line)[0]
            score = result['score']
            if result['label'].lower() == "negative":
                score = -score

            # translation for non-english lines
            display_text = line
            try: 
                lang = detect(line)
                if lang != 'en':
                    try:
                        # translate to english using deep-translator
                        translated_text = GoogleTranslator(source=lang, target='en').translate(line)
                        
                        # make sure translation worked
                        if translated_text and translated_text.lower() != line.lower():
                            # show: "original --> (english)"
                            display_text = f"{line} ({translated_text})"
                            
                    except Exception as e:
                        # if translation fails, just use original
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

# word frequency analysis
def get_top_words(highlight_lyrics_list):
    all_lyrics = " ".join([hl['original'] for hl in highlight_lyrics_list])
    tokens = word_tokenize(all_lyrics.lower())
    stop_words = set(stopwords.words('english'))
    tokens = [t for t in tokens if t.isalpha() and t not in stop_words]
    word_counts = Counter(tokens)
    return word_counts.most_common(10)

# map genres to themes, but use sentiment to override certain themes (like sadness)
def map_genres_to_themes(genres, sentiment_score):
    if not genres:
        return "Unknown"
    
    # if the song is very negative (negative sentiment value), override genre classification
    if sentiment_score < -0.7:  # threshhold = -0.7
        return "Heartbreak/Sadness"
    
    # convert genres to lowercase for easier matching
    genre_text = " ".join(genres).lower()
    
    # genre mapping based on spotify's actual genre classifications
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
        # for pop, check sentiment - sad pop songs exist!
        if sentiment_score < -0.3:
            return "Heartbreak/Sadness"
        else:
            return "Party/Fun"
    else:
        # if no clear match, return the "main" genre
        return genres[0] if genres else "Unknown"

def process_single_track(track_info):
    #process single track (quicker)
    title, artist, genres = track_info
    
    print(f"Processing: {title} by {artist}")
    
    # getting lyrics
    lyrics = get_song_lyrics(title, artist)
    if not lyrics:
        return None
        
    # analyze sentiment
    scored_lines = analyze_lyrics_sentiment(lyrics)
    if not scored_lines:
        print(f"No valid lines found for {title}")
        return None
    
    # find most emotional line and get its sentiment score
    scored_lines.sort(key=lambda x: abs(x['score']), reverse=True)
    most_emotional_line = scored_lines[0]
    sentiment_score = most_emotional_line['score']
    
    # get theme using both genres AND sentiment
    theme = map_genres_to_themes(genres, sentiment_score) if genres else "Unknown"
    
    # return result
    return {
        'song': title,
        'artist': artist,
        'line': most_emotional_line['display'],
        'original': most_emotional_line['original'],
        'theme': theme,
        'genres': genres[:3] if genres else []  # keep first 3 genres
    }

@app.get("/login")
def login():
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)

@app.get("/themes")
def themes():
    # return word frequency if we have processed lyrics
    if not highlight_lyrics:
        return {"error": "No lyrics processed yet. Please login first."}
    top_words = get_top_words(highlight_lyrics)
    return {"themes": top_words}

@app.get('/api/results')
def get_results():
    if not highlight_lyrics:
        return JSONResponse (status_code = 404, content={"error": "No data available. Please login first."})
    top_words = get_top_words(highlight_lyrics)
    theme_counts = Counter(hl['theme'] for hl in highlight_lyrics)
    
    return {
        "highlights": highlight_lyrics,
        "top_words": [{"word": word, "count": count} for word, count in top_words],
        "themes": [{"theme": theme, "count": count} for theme, count in theme_counts.most_common()],
        "total_songs": len(highlight_lyrics)
    }

@app.get("/callback")
def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "No authorization code received"}
    
    try:
        # get spotify access token
        token_info = sp_oauth.get_access_token(code)
        access_token = token_info["access_token"]

        # get top 20 tracks from spotify
        sp = Spotify(auth=access_token)
        top_tracks = sp.current_user_top_tracks(limit=20, time_range='short_term')["items"]

        # clear previous highlights so they don't accumulate between logins
        highlight_lyrics.clear()
        total_songs = len(top_tracks)
        
        # remove duplicates first (before processing) and get genres
        unique_tracks = []
        seen_songs = set()
        for track in top_tracks:
            title = track['name']
            artist = track['artists'][0]['name']
            
            # get genres from the artist or album
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
        
        # process tracks in parallel to speed up *egregiously* slow processing times
        with ThreadPoolExecutor(max_workers=5) as executor:  # process 5 songs at once
            results = list(executor.map(process_single_track, unique_tracks))
        
        # filter out failed results and add to highlight_lyrics
        successful_results = [result for result in results if result is not None]
        highlight_lyrics.extend(successful_results)
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        successful_analyses = len(successful_results)
        
        print(f"Successfully analyzed {successful_analyses}/{len(unique_tracks)} tracks in {processing_time} seconds")

        return RedirectResponse(url="http://localhost:3000/results")
        
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

