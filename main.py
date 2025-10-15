from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
import os
import requests
import base64
import nltk
from dotenv import load_dotenv
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from transformers import pipeline

load_dotenv()

nltk.download('stopwords')
nltk.download('punkt')
nltk.download('punkt_tab')

app = FastAPI()

origins = [
    os.getenv("FRONTEND_URL"),
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

results_data = None  # store globally for /api/results

@app.get("/login")
def login():
    scope = "user-top-read"
    auth_url = (
        f"https://accounts.spotify.com/authorize?response_type=code"
        f"&client_id={SPOTIFY_CLIENT_ID}"
        f"&redirect_uri={SPOTIFY_REDIRECT_URI}"
        f"&scope={scope}"
    )
    return RedirectResponse(auth_url)

@app.get("/callback")
def callback(code: str):
    return RedirectResponse(f"{os.getenv('FRONTEND_URL')}/loading?code={code}")

@app.get("/api/process")
def process_data(code: str):
    global results_data

    token_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
    }
    headers = {"Authorization": f"Basic {auth_header}"}
    token_res = requests.post(token_url, data=payload, headers=headers)
    access_token = token_res.json().get("access_token")

    if not access_token:
        return JSONResponse({"error": "Failed to get access token"}, status_code=400)

    headers = {"Authorization": f"Bearer {access_token}"}
    top_tracks = requests.get("https://api.spotify.com/v1/me/top/tracks?limit=10", headers=headers).json()

    analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english", token=HF_TOKEN)

    song_results = []
    for item in top_tracks.get("items", []):
        track = item["name"]
        artist = item["artists"][0]["name"]
        print(f"Searching for \"{track}\" by {artist}...")

        genius_res = requests.get(
            f"https://api.genius.com/search?q={track} {artist}",
            headers={"Authorization": f"Bearer {GENIUS_TOKEN}"}
        ).json()

        if genius_res["response"]["hits"]:
            url = genius_res["response"]["hits"][0]["result"]["url"]
        else:
            url = None

        sentiment = analyzer(track)[0]  # dummy text analysis
        song_results.append({
            "track": track,
            "artist": artist,
            "lyrics_url": url,
            "sentiment": sentiment["label"],
            "confidence": round(sentiment["score"], 3)
        })

    results_data = {"songs": song_results}
    return JSONResponse({"message": "Processing complete"})

@app.get("/api/results")
def get_results():
    if not results_data:
        return JSONResponse({"error": "No data available"})
    return JSONResponse(results_data)
