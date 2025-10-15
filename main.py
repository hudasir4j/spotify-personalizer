from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
import os, requests, base64
from dotenv import load_dotenv
import nltk

load_dotenv()
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)

app = FastAPI()

origins = [os.getenv("FRONTEND_URL"), "http://localhost:3000"]
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

results_data = None

@app.get("/login")
def login():
    scope = "user-top-read"
    return RedirectResponse(
        f"https://accounts.spotify.com/authorize?response_type=code"
        f"&client_id={SPOTIFY_CLIENT_ID}"
        f"&redirect_uri={SPOTIFY_REDIRECT_URI}"
        f"&scope={scope}"
    )

@app.get("/callback")
def callback(code: str):
    return RedirectResponse(f"{os.getenv('FRONTEND_URL')}/loading?code={code}")

@app.get("/api/process")
def process_data(code: str):
    global results_data

    token_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
    payload = {"grant_type": "authorization_code", "code": code, "redirect_uri": SPOTIFY_REDIRECT_URI}
    headers = {"Authorization": f"Basic {auth_header}"}
    token_res = requests.post(token_url, data=payload, headers=headers)
    access_token = token_res.json().get("access_token")
    if not access_token:
        return JSONResponse({"error": "Spotify token failed"}, status_code=400)

    headers = {"Authorization": f"Bearer {access_token}"}
    top_tracks = requests.get("https://api.spotify.com/v1/me/top/tracks?limit=10", headers=headers).json()

    song_results = []
    for item in top_tracks.get("items", []):
        track = item["name"]
        artist = item["artists"][0]["name"]
        print(f"Analyzing {track} by {artist}")

        genius_res = requests.get(
            f"https://api.genius.com/search?q={track} {artist}",
            headers={"Authorization": f"Bearer {GENIUS_TOKEN}"}
        ).json()

        lyrics_url = genius_res["response"]["hits"][0]["result"]["url"] if genius_res["response"]["hits"] else None

        # Sentiment via Hugging Face API (no local model)
        hf_resp = requests.post(
            "https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": track}
        )
        sentiment_json = hf_resp.json()
        label = sentiment_json[0][0]["label"]
        score = sentiment_json[0][0]["score"]

        song_results.append({
            "track": track,
            "artist": artist,
            "lyrics_url": lyrics_url,
            "sentiment": label,
            "confidence": round(score, 3)
        })

    results_data = {"songs": song_results}
    return JSONResponse({"message": "Processing complete"})

@app.get("/api/results")
def get_results():
    return JSONResponse(results_data or {"error": "No data available"})
