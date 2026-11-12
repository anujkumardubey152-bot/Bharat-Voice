"""Settings. Keys come from Streamlit secrets or environment variables, never from code."""
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # dotenv is optional
    pass

# label -> (STT language_code, TTS language, Gemini reply-language hint)
# Codes verified in docs.gnani.ai (STT: indic-auto/lists are Prisma v3.0 only; TTS: auto, hi-en).
LANGUAGES = {
    "Auto-detect": ("indic-auto", "auto", "the same language the user spoke or wrote"),
    "Hinglish": ("hi-IN,en-IN", "hi-en", "Hinglish (Hindi written in Roman letters, mixed with English)"),
    "Hindi": ("hi-IN,en-IN", "hi-IN", "Hindi in Devanagari script"),
    "English": ("en-IN", "en-IN", "English"),
    "Bengali": ("bn-IN", "bn-IN", "Bengali"),
    "Gujarati": ("gu-IN", "gu-IN", "Gujarati"),
    "Kannada": ("kn-IN", "kn-IN", "Kannada"),
    "Malayalam": ("ml-IN", "ml-IN", "Malayalam"),
    "Marathi": ("mr-IN", "mr-IN", "Marathi"),
    "Punjabi": ("pa-IN", "pa-IN", "Punjabi"),
    "Tamil": ("ta-IN", "ta-IN", "Tamil"),
    "Telugu": ("te-IN", "te-IN", "Telugu"),
}
TESTED_LANGUAGES = {"Hindi", "English", "Hinglish"}  # only these are promised for the demo

# Timbre v3.0 voices listed in the Gnani docs (each speaks all languages).
VOICES = ["Shivani", "Lakshmi", "Kalpana", "Chetana", "Vasudha", "Riyaa", "Tarika",
          "Avinash", "Shubham", "Prakash", "Devansh", "Yashraj", "Harshad"]

MAX_AUDIO_SECONDS = 30      # Prisma REST limit
MAX_AUDIO_BYTES = 5_000_000
MAX_TEXT_CHARS = 1000
TTS_MAX_CHARS = 600
HISTORY_TURNS = 10


def _secret(name: str, default: str = "") -> str:
    try:
        import streamlit as st
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    gnani_key: str
    gemini_key: str
    gemini_model: str

    @property
    def ready(self) -> bool:
        return bool(self.gnani_key and self.gemini_key)


def get_settings() -> Settings:
    return Settings(
        gnani_key=_secret("GNANI_API_KEY"),
        gemini_key=_secret("GEMINI_API_KEY"),
        gemini_model=_secret("GEMINI_MODEL", "gemini-2.5-flash"),
    )
