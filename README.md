## Overview
Analyzing your top Spotify tracks to extract emotional highlights, recurring themes, and common lyrical patterns. Built to explore NLP, data processing, and API integration, this project is designed as a showcase of applied data engineering and Python/React skills.

## Tech Stack

**Disclaimer** - AI Usage: I used tools like Claude to guide the setup of this project, like telling me what the most effective models are for my use cases. The rest of the code, however, was done personally as this is my first project in this backend stack and I wanted to gain the experience.

### Backend (Python/FastAPI)

* **FastAPI**: API server to manage Spotify OAuth, lyrics retrieval, and processing endpoints.

* **Spotipy**: Spotify Web API integration for user authentication and top track retrieval.

* **LyricsGenius**: Fetching song lyrics from Genius.

* **NLP Pipelines (Hugging Face Transformers)**:

  * tabularisai/multilingual-sentiment-analysis for sentiment scoring of individual lines.

  * zero-shot-classification for theme inference when mapping songs to emotional categories.

* **LangDetect + deep-translator**: Detects non-English lyrics and translates them reliably (fixing issues with non-Roman scripts).

* **ThreadPoolExecutor**: Parallel processing of multiple songs to drastically reduce egregiously long waiting times.

* **NLTK**: Tokenization and stopword filtering for word frequency analysis.

### Frontend (React)

* **React Router**: Navigation between Home, Loading, and Results pages.

* **Dynamic UI**: Floating notes, progress bars, and animated word clouds to visualize analysis.

* **Polling Logic**: Handles asynchronous processing with feedback during analysis.



## Features & Challenges

* **Non-Roman lyric translation:** Many APIs fail with Hindi, Arabic, or other non-Latin scripts; solved using deep-translator to maintain accurate context.

* **Efficient processing**: Initial sequential processing caused 5–10 minute waits; implementing ThreadPoolExecutor enabled concurrent processing of multiple songs, cutting time down to ~ 1 minute.

* **Data cleaning & filtering**: Removed lines that interfered with sentiment analysis like “contributors” and “chorus” to improve NLP analysis quality.

* **Theme weighting**: Combined Spotify genre data with sentiment scores to classify songs intelligently (e.g., unique cases like a sad pop song, would now labeled Heartbreak/Sadness instead of Party/Fun).

## Cloning
If you're interested in cloning my project, you can follow these steps. But honestly I'd just wait for the beta...

1. Clone Repo
```
git clone https://github.com/hudasir4j/spotify-personalizer
cd spotify-personalizer
```
2. Install backend dependencies:
```
pip install -r requirements.txt
```
3. Add .env file (use your own keys):
```
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=
GENIUS_TOKEN=
```
4. Start backend:
```
uvicorn main:app --reload
```
5. Start frontend (React):
```
cd client
npm install
npm start
```

## Spotify Personalizer's Future
Because the project is in it's alpha phase, there are still many problems I would like to fix. There's many features I'm currently planning out but am excited to implement in later versions. Here are some of them:
* Expand support for more songs and historical time ranges (you can select the range of the top tracks)
* Improve theme inference using custom-trained models, more inclusive to all languages
* Refine sentiment scoring with context-aware NLP (e.g., transformer embeddings for entire verses).
* Speeding up lyric retrieval and song processing even further, making a better user experience.

## Demonstration

<img width="1508" height="899" alt="Screenshot 2025-10-04 at 7 23 28 PM" src="https://github.com/user-attachments/assets/cf7062d1-fa83-49b2-ac92-1fb5040bad51" />
<img width="1497" height="882" alt="Screenshot 2025-10-04 at 7 23 40 PM" src="https://github.com/user-attachments/assets/6492d0ee-ee29-4ad6-9496-c5327b97e0b1" />
<img width="1497" height="856" alt="Screenshot 2025-10-04 at 7 25 17 PM" src="https://github.com/user-attachments/assets/d5af450f-0ef1-4040-a770-77a6ef3e539b" />
<img width="1482" height="878" alt="Screenshot 2025-10-04 at 7 25 33 PM" src="https://github.com/user-attachments/assets/be7c7db3-5c96-4770-8763-55677075ec77" />


