import re

try:
    from langdetect import LangDetectException, detect
except ImportError:
    detect = None
    LangDetectException = Exception

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

_ASCII_HEAVY = re.compile(r"[a-zA-Z]")
_CHUNK_SIZE = 4500


def detect_language(text):
    if not text or not text.strip():
        return "en"
    sample = text[:2000]
    if len(_ASCII_HEAVY.findall(sample)) / max(len(sample), 1) > 0.85:
        return "en"
    if not detect:
        return "unknown"
    try:
        code = detect(sample)
        return code if code else "unknown"
    except LangDetectException:
        return "unknown"


def translate_to_english(text, source_lang=None):
    if not text or not text.strip():
        return text
    if source_lang in (None, "en", "unknown"):
        return text
    if not GoogleTranslator:
        return text
    try:
        chunks = []
        for i in range(0, len(text), _CHUNK_SIZE):
            chunk = text[i : i + _CHUNK_SIZE]
            chunks.append(GoogleTranslator(source=source_lang, target="en").translate(chunk))
        return "\n".join(chunks)
    except Exception as exc:
        print(f"Translation failed ({source_lang}): {exc}")
        return text


def prepare_lyrics_for_analysis(original_lyrics):
    language = detect_language(original_lyrics)
    if language in ("en", "unknown"):
        return {
            "language": language if language != "unknown" else "en",
            "original": original_lyrics,
            "analysis_text": original_lyrics,
            "translated": False,
        }
    translated = translate_to_english(original_lyrics, language)
    return {
        "language": language,
        "original": original_lyrics,
        "analysis_text": translated,
        "translated": translated != original_lyrics,
    }
