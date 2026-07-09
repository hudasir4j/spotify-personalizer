import os
import re
from collections import Counter

import nltk
import requests
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.text_rank import TextRankSummarizer

try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")

_sia = SentimentIntensityAnalyzer()
_textrank = TextRankSummarizer()
THEME_LABELS = ["love", "loss", "hope", "joy", "nostalgia", "heartbreak"]
VIBE_NAMES = [
    "baddie",
    "villain era",
    "main character",
    "locked in",
    "hopeless romantic",
    "yearning",
    "delulu",
    "situationship",
    "it's ok i'm ok",
    "thugging it out",
    "romanticizing life",
    "soft girl autumn",
    "missing what used to be",
    "unc",
    "moving on playlist",
    "3am overthinking",
]

# Each vibe: keywords (full lyrics), title_keywords, genre_terms, raw_boost, sentiment range, audio hints
VIBE_PROFILES = {
    "baddie": {
        "keywords": [
            "money", "boss", "rich", "flex", "queen", "king", "power", "chain",
            "diamond", "luxury", "unbothered", "attitude", "stunt", "drip",
            "naughty", "bad girl", "bad bitch", "prettier", "prettiest", "savage",
            "body", "sexy", "hot", "fine", "look at me", "want me",
        ],
        "title_keywords": [
            "naughty", "bad", "boss", "savage", "queen", "rich", "money",
            "flex", "drip", "baddie", "freak", "sexy", "hot",
        ],
        "genre_terms": ["hip hop", "rap", "trap", "drill", "r&b"],
        "raw_boost": {},
        "sentiment": (0.0, 1.0),
        "audio": {"energy": (0.55, 1.0), "danceability": (0.5, 1.0), "speechiness": (0.08, 1.0)},
    },
    "villain era": {
        "keywords": [
            "devil", "dark", "blood", "kill", "poison", "revenge", "danger",
            "obsession", "toxic", "psycho", "sin", "hell", "monster", "enemy",
        ],
        "title_keywords": ["devil", "villain", "monster", "toxic", "psycho", "dark"],
        "genre_terms": ["rock", "alternative", "metal", "electronic"],
        "raw_boost": {"heartbreak": 0.5},
        "sentiment": (-0.8, 0.35),
        "audio": {"valence": (0.0, 0.45), "energy": (0.45, 1.0)},
    },
    "main character": {
        "keywords": [
            "star", "shine", "world", "dream", "tonight", "alive", "legend",
            "moment", "stage", "spotlight", "center", "icon", "best",
        ],
        "title_keywords": ["star", "queen", "king", "hero", "icon", "legend"],
        "genre_terms": ["pop", "indie pop", "dance pop"],
        "raw_boost": {"joy": 2.0, "hope": 1.0},
        "sentiment": (0.3, 1.0),
        "audio": {"valence": (0.55, 1.0), "energy": (0.45, 0.85)},
    },
    "locked in": {
        "keywords": [
            "grind", "work", "hustle", "focus", "win", "never stop", "level up",
            "no sleep", "mission", "goal",
        ],
        "title_keywords": ["grind", "hustle", "work", "win", "go"],
        "genre_terms": ["hip hop", "edm", "electronic"],
        "raw_boost": {"joy": 1.0},
        "sentiment": (0.15, 1.0),
        "audio": {"energy": (0.65, 1.0), "valence": (0.4, 0.85)},
    },
    "hopeless romantic": {
        "keywords": [
            "forever", "always", "marry", "wedding", "soulmate", "perfect",
            "everything to me", "in love", "falling in love", "true love",
            "all of me", "loves all of", "give you my", "my heart",
        ],
        "title_keywords": ["love", "forever", "always", "marry", "wedding"],
        "genre_terms": ["pop", "r&b", "soul"],
        "raw_boost": {"love": 2.0},
        "sentiment": (0.35, 1.0),
        "audio": {"valence": (0.55, 1.0), "energy": (0.25, 0.65)},
    },
    "yearning": {
        "keywords": [
            "need you", "want you", "long for", "longing", "desire", "ache",
            "crave", "devotion", "only you", "can't live", "without you",
            "lady", "my life", "hold me", "stay with me", "miss your",
            "every night", "in my arms", "belong", "yours",
        ],
        "title_keywords": [
            "lady", "need", "want", "miss", "yours", "mine", "devotion",
            "longing", "heart", "love of my life",
        ],
        "genre_terms": ["r&b", "soul", "quiet storm", "soft rock"],
        "raw_boost": {"love": 2.5, "nostalgia": 0.5},
        "sentiment": (0.05, 0.55),
        "audio": {"valence": (0.3, 0.6), "energy": (0.15, 0.55), "acousticness": (0.15, 0.85)},
    },
    "delulu": {
        "keywords": [
            "maybe one day", "what if", "pretend", "fantasy", "could be us",
            "might be", "sign from", "manifest", "hope you",
        ],
        "title_keywords": ["maybe", "wish", "if", "what if"],
        "genre_terms": ["pop", "indie", "bedroom pop"],
        "raw_boost": {"love": 1.0, "hope": 1.5},
        "sentiment": (-0.05, 0.45),
        "audio": {"valence": (0.35, 0.65), "energy": (0.2, 0.55)},
    },
    "situationship": {
        "keywords": [
            "situationship", "don't label", "no title", "what are we",
            "mixed signals", "on and off", "almost", "just friends",
            "late night text", "booty call", "casual", "complicated",
        ],
        "title_keywords": ["situationship", "complicated", "mixed", "casual"],
        "genre_terms": ["pop", "r&b", "indie"],
        "raw_boost": {},
        "sentiment": (-0.35, 0.2),
        "audio": {"valence": (0.25, 0.55), "energy": (0.25, 0.6)},
    },
    "it's ok i'm ok": {
        "keywords": [
            "i'm fine", "im fine", "i'm okay", "im okay", "over it",
            "moving on", "healing", "better now", "don't care anymore",
        ],
        "title_keywords": ["fine", "okay", "ok", "over it", "moving on"],
        "genre_terms": ["pop", "indie"],
        "raw_boost": {"heartbreak": 1.5, "loss": 1.0},
        "sentiment": (-0.35, 0.15),
        "audio": {"valence": (0.35, 0.65), "energy": (0.3, 0.65)},
    },
    "thugging it out": {
        "keywords": [
            "cry", "tears", "pain", "hurt", "broken", "alone", "empty",
            "numb", "gone", "lost", "falling apart", "can't breathe",
        ],
        "title_keywords": ["cry", "tears", "hurt", "pain", "broken", "alone"],
        "genre_terms": ["r&b", "soul", "emo rap"],
        "raw_boost": {"heartbreak": 2.5, "loss": 1.5},
        "sentiment": (-1.0, -0.2),
        "audio": {"valence": (0.0, 0.35), "energy": (0.2, 0.65)},
    },
    "romanticizing life": {
        "keywords": [
            "golden hour", "sunset", "sunrise", "bloom", "flower", "warm",
            "morning light", "coffee shop", "Sunday", "golden",
        ],
        "title_keywords": ["sun", "golden", "bloom", "daydream"],
        "genre_terms": ["indie", "folk", "dream pop"],
        "raw_boost": {"hope": 2.5},
        "sentiment": (0.15, 0.85),
        "audio": {"valence": (0.45, 0.85), "acousticness": (0.2, 0.9)},
    },
    "soft girl autumn": {
        "keywords": [
            "cozy", "sweater", "rain", "tea", "gentle", "quiet", "autumn",
            "fall leaves", "soft", "warm blanket",
        ],
        "title_keywords": ["cozy", "soft", "autumn", "fall", "rain"],
        "genre_terms": ["indie folk", "folk", "acoustic", "singer-songwriter"],
        "raw_boost": {"nostalgia": 1.0, "hope": 0.5},
        "sentiment": (-0.05, 0.45),
        "audio": {"acousticness": (0.45, 1.0), "energy": (0.0, 0.45)},
    },
    "missing what used to be": {
        "keywords": [
            "used to", "remember when", "back when", "before you", "once upon",
            "memory", "memories", "good old days", "those days",
        ],
        "title_keywords": ["remember", "used to", "memories", "past"],
        "genre_terms": ["indie", "alternative", "pop"],
        "raw_boost": {"nostalgia": 2.5},
        "sentiment": (-0.55, 0.1),
        "audio": {"valence": (0.15, 0.45), "energy": (0.15, 0.5)},
    },
    "unc": {
        "keywords": [
            "childhood", "grew up", "growing up", "years ago", "school days",
            "hometown", "when i was young", "kid again",
        ],
        "title_keywords": ["childhood", "young", "kid", "grew up", "school"],
        "genre_terms": ["indie", "rock", "pop rock"],
        "raw_boost": {"nostalgia": 2.0},
        "sentiment": (-0.35, 0.25),
        "audio": {"valence": (0.25, 0.55), "energy": (0.2, 0.55)},
    },
    "moving on playlist": {
        "keywords": [
            "goodbye", "let go", "walk away", "last time", "new chapter",
            "starting over", "done with you", "final",
        ],
        "title_keywords": ["goodbye", "bye", "over", "leave", "walk away"],
        "genre_terms": ["pop", "country", "indie"],
        "raw_boost": {"loss": 2.5},
        "sentiment": (-0.45, 0.15),
        "audio": {"valence": (0.25, 0.55), "energy": (0.3, 0.65)},
    },
    "3am overthinking": {
        "keywords": [
            "can't sleep", "3am", "overthink", "racing thoughts", "ceiling",
            "wide awake", "toss and turn", "in my head", "wonder why",
        ],
        "title_keywords": ["3am", "night", "sleep", "overthink", "insomnia"],
        "genre_terms": ["indie", "bedroom pop", "lo-fi"],
        "raw_boost": {"nostalgia": 0.5, "heartbreak": 0.5},
        "sentiment": (-0.55, 0.05),
        "audio": {"energy": (0.0, 0.4), "valence": (0.1, 0.45), "danceability": (0.0, 0.45)},
    },
}

HF_TOKEN = None


def _get_hf_token():
    global HF_TOKEN
    if HF_TOKEN is None:
        HF_TOKEN = os.getenv("HF_API_TOKEN") or ""
    return HF_TOKEN

_JUNK_PATTERNS = (
    r"^\d+\s*contributors?",
    r"^embed$",
    r"^you might also like$",
    r"^see .* on genius$",
)


def _normalize_line(line):
    return re.sub(r"\s+", " ", line.lower()).strip()


def clean_lyrics(lyrics):
    lines = []
    for raw in lyrics.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            continue
        if any(re.search(pat, line.lower()) for pat in _JUNK_PATTERNS):
            continue
        if len(line) < 12:
            continue
        lines.append(line)
    return lines


def _textrank_boost(lines):
    if len(lines) < 3:
        return {}
    document = PlaintextParser.from_string(
        ". ".join(lines),
        Tokenizer("english"),
    )
    try:
        ranked = _textrank(document.document, max(1, min(5, len(lines) // 4)))
    except Exception:
        return {}
    boosts = {}
    for sentence in ranked:
        normalized = _normalize_line(str(sentence))
        boosts[normalized] = boosts.get(normalized, 0) + 2.0
    return boosts


def _length_score(line):
    length = len(line)
    if 25 <= length <= 100:
        return 1.5
    if 15 <= length <= 140:
        return 1.0
    return 0.4


def _lyrics_sentiment(lines):
    if not lines:
        return {"compound": 0.0, "pos": 0.0, "neg": 0.0, "neu": 1.0}
    scores = [_sia.polarity_scores(line) for line in lines]
    n = len(scores)
    return {
        "compound": sum(s["compound"] for s in scores) / n,
        "pos": sum(s["pos"] for s in scores) / n,
        "neg": sum(s["neg"] for s in scores) / n,
        "neu": sum(s["neu"] for s in scores) / n,
    }


def pick_iconic_line(lyrics):
    lines = clean_lyrics(lyrics)
    if not lines:
        return "", "neutral"
    return _pick_best_from_lines(lines)


def pick_iconic_line_bilingual(original_lyrics, analysis_lyrics):
    """Pick display line from original; score using English analysis text when translated."""
    orig_lines = clean_lyrics(original_lyrics)
    if not orig_lines:
        return "", "neutral", False

    analysis_lines = clean_lyrics(analysis_lyrics or original_lyrics)
    if len(analysis_lines) == len(orig_lines):
        best_line, raw_theme, best_idx = _pick_best_from_lines(
            analysis_lines, return_index=True
        )
        display_line = orig_lines[best_idx]
        translated_display = display_line != best_line
        return display_line, raw_theme, translated_display

    display_line, raw_theme = _pick_best_from_lines(orig_lines)
    return display_line, raw_theme, False


def _pick_best_from_lines(lines, return_index=False):
    counts = Counter(_normalize_line(line) for line in lines)
    textrank_boosts = _textrank_boost(lines)

    best_idx = 0
    best_line = lines[0]
    best_score = -1.0
    for i, line in enumerate(lines):
        normalized = _normalize_line(line)
        repetition = counts[normalized]
        rep_score = min(repetition, 4) * 1.5
        sentiment = abs(_sia.polarity_scores(line)["compound"])
        score = (
            rep_score
            + _length_score(line)
            + sentiment * 2.5
            + textrank_boosts.get(normalized, 0)
        )
        if score > best_score:
            best_score = score
            best_line = line
            best_idx = i

    theme = classify_theme_from_lyrics(lines, best_line)
    if return_index:
        return best_line, theme, best_idx
    return best_line, theme


def classify_theme_from_lyrics(lines, anchor_line):
    theme = _hf_zero_shot_theme(_build_vibe_context("", "", anchor_line, lines))
    if theme:
        return theme
    sentiment = _lyrics_sentiment(lines)
    compound = sentiment["compound"]
    full_text = " ".join(lines).lower()
    if compound >= 0.35:
        return "joy" if "love" not in full_text else "love"
    if compound <= -0.35:
        return "heartbreak" if any(w in full_text for w in ("you", "her", "him", "us")) else "loss"
    if compound >= 0.08:
        return "hope"
    if compound <= -0.08:
        return "nostalgia"
    return "love"


def classify_theme(line):
    return classify_theme_from_lyrics([line], line)


def _build_vibe_context(title, artist, line, lines, genres=None):
    genre_text = ", ".join(genres or [])
    snippet = " ".join(lines[:8])[:600] if lines else line
    parts = [f'"{title}" by {artist}.']
    if genre_text:
        parts.append(f"Genres: {genre_text}.")
    if line:
        parts.append(f'Key lyric: "{line}".')
    if snippet:
        parts.append(f"Lyrics excerpt: {snippet}")
    return " ".join(parts)[:900]


def _hf_multilingual_sentiment(text):
    token = _get_hf_token()
    if not token:
        return None
    try:
        resp = requests.post(
            "https://api-inference.huggingface.co/models/tabularisai/multilingual-sentiment-analysis",
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": text[:512]},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if isinstance(data, list) and data:
            item = data[0]
            if isinstance(item, list) and item:
                item = max(item, key=lambda x: x.get("score", 0))
            return item.get("label"), item.get("score", 0)
        return None
    except requests.RequestException:
        return None


_SENTIMENT_THEME_MAP = {
    "Very Positive": "joy",
    "Positive": "hope",
    "Neutral": "nostalgia",
    "Negative": "loss",
    "Very Negative": "heartbreak",
}


def _apply_ml_sentiment_boost(scores, ml_result):
    if not ml_result:
        return
    label, confidence = ml_result
    if confidence < 0.35:
        return
    raw = _SENTIMENT_THEME_MAP.get(label)
    if not raw:
        return
    for vibe, profile in VIBE_PROFILES.items():
        scores[vibe] += profile["raw_boost"].get(raw, 0) * confidence * 0.8


def _hf_zero_shot_theme(text):
    token = _get_hf_token()
    if not token:
        return None
    try:
        resp = requests.post(
            "https://api-inference.huggingface.co/models/facebook/bart-large-mnli",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "inputs": text[:400],
                "parameters": {"candidate_labels": THEME_LABELS},
            },
            timeout=12,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        labels = data.get("labels") or []
        return labels[0] if labels else None
    except requests.RequestException:
        return None


def _hf_zero_shot_vibe(context):
    token = _get_hf_token()
    if not token:
        return None
    try:
        resp = requests.post(
            "https://api-inference.huggingface.co/models/facebook/bart-large-mnli",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "inputs": context[:512],
                "parameters": {"candidate_labels": VIBE_NAMES, "multi_label": False},
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        labels = data.get("labels") or []
        scores = data.get("scores") or []
        if labels and scores and scores[0] >= 0.22:
            return labels[0]
        return None
    except requests.RequestException:
        return None


def _genre_blob(genres):
    return " ".join(g.lower() for g in genres)


def _keyword_hits(text, keywords):
    hits = 0.0
    for kw in keywords:
        if kw in text:
            hits += 1.0 + (len(kw) / 20.0)
    return hits


def _title_hits(title, artist, title_keywords):
    blob = f"{title} {artist}".lower()
    return _keyword_hits(blob, title_keywords) * 2.5


def _sentiment_fit(compound, lo, hi):
    if lo <= compound <= hi:
        return 2.0
    margin = min(abs(compound - lo), abs(compound - hi))
    return max(-1.5, 1.0 - margin * 3.0)


def _audio_fit(audio, hints):
    if not audio or not hints:
        return 0.0
    score = 0.0
    for key, (lo, hi) in hints.items():
        val = audio.get(key)
        if val is None:
            continue
        if lo <= val <= hi:
            score += +2.0
        else:
            dist = min(abs(val - lo), abs(val - hi))
            score += max(-1.0, 1.0 - dist * 4.0)
    return score


def _score_vibes(title, artist, line, raw_theme, genres, lines, audio):
    full_text = " ".join(lines).lower() if lines else line.lower()
    line_text = line.lower()
    genre_text = _genre_blob(genres)
    sentiment = _lyrics_sentiment(lines) if lines else _sia.polarity_scores(line)
    compound = sentiment["compound"]

    scores = {}
    for vibe, profile in VIBE_PROFILES.items():
        score = 0.0
        score += _title_hits(title, artist, profile.get("title_keywords", [])) * 3.0
        score += _keyword_hits(full_text, profile["keywords"]) * 1.8
        score += _keyword_hits(line_text, profile["keywords"]) * 1.0
        score += _keyword_hits(genre_text, profile["genre_terms"]) * 1.5
        score += profile["raw_boost"].get(raw_theme, 0)
        score += _sentiment_fit(compound, *profile["sentiment"])
        score += _audio_fit(audio, profile.get("audio"))

        scores[vibe] = score

    return scores, compound


def _resolve_love_vibe(scores, compound, full_text):
    """Disambiguate love-related vibes using sentiment + keyword density."""
    romantic = scores.get("hopeless romantic", 0)
    yearning = scores.get("yearning", 0)
    delulu = scores.get("delulu", 0)
    situationship = scores.get("situationship", 0)
    baddie = scores.get("baddie", 0)

    if baddie >= max(romantic, yearning, delulu, situationship) and baddie > 2:
        return "baddie"

    if situationship > 2.5 and any(
        kw in full_text for kw in VIBE_PROFILES["situationship"]["keywords"]
    ):
        return "situationship"

    if compound >= 0.35 and romantic >= yearning:
        return "hopeless romantic"
    if compound <= 0.25 or any(
        kw in full_text for kw in ("need", "want", "long", "ache", "lady", "devotion")
    ):
        if yearning >= romantic - 0.5:
            return "yearning"
    if delulu > romantic and delulu > yearning:
        return "delulu"
    if yearning >= romantic:
        return "yearning"
    return "hopeless romantic"


def assign_aesthetic_vibe(title, artist, line, raw_theme, genres, lyrics="", audio=None):
    lines = clean_lyrics(lyrics) if lyrics else ([line] if line else [])
    full_text = " ".join(lines).lower()

    context = _build_vibe_context(title, artist, line, lines, genres)
    scores, compound = _score_vibes(title, artist, line, raw_theme, genres, lines, audio)

    hf_vibe = _hf_zero_shot_vibe(context)
    if hf_vibe:
        scores[hf_vibe] = scores.get(hf_vibe, 0) + 5.0

    ml_result = _hf_multilingual_sentiment(context[:512])
    _apply_ml_sentiment_boost(scores, ml_result)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_vibe, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if raw_theme == "love" and best_vibe in {
        "hopeless romantic", "yearning", "delulu", "situationship", "baddie"
    }:
        return _resolve_love_vibe(scores, compound, full_text)

    if best_score <= 1.0 or (best_score - second_score) < 0.4:
        fallbacks = {
            "love": _resolve_love_vibe(scores, compound, full_text),
            "heartbreak": "it's ok i'm ok" if compound > -0.4 else "thugging it out",
            "loss": "moving on playlist",
            "hope": "romanticizing life",
            "joy": "main character",
            "nostalgia": "missing what used to be",
        }
        return fallbacks.get(raw_theme, best_vibe if best_score > 0 else "main character")

    return best_vibe


def get_listening_eras(highlights, limit=4):
    groups = {}
    for song in highlights:
        vibe = song.get("theme")
        if not vibe:
            continue
        if vibe not in groups:
            groups[vibe] = {"vibe": vibe, "count": 0, "songs": []}
        groups[vibe]["count"] += 1
        groups[vibe]["songs"].append(
            {"song": song["song"], "artist": song["artist"], "line": song["line"]}
        )
    return sorted(groups.values(), key=lambda e: e["count"], reverse=True)[:limit]


def get_top_words(highlights):
    text = " ".join(h["line"] for h in highlights)
    tokens = word_tokenize(text.lower())
    tokens = [t for t in tokens if t.isalpha() and t not in stopwords.words("english")]
    return Counter(tokens).most_common(10)
