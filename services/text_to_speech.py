"""Gnani Timbre v3.0 REST. Source: docs.gnani.ai/api/TTS/tts-inference"""
import re
from config import LANGUAGES, TTS_MAX_CHARS
from services.errors import ServiceError
from services.http import post_with_retry

URL = "https://api.vachana.ai/api/v1/tts/inference"


def speakable(text: str) -> str:
    text = re.sub(r"[*_`#>]+", "", text)           # strip markdown
    text = re.sub(r"<[^>]{1,20}>", "", text)       # strip anything that looks like an audio tag
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > TTS_MAX_CHARS:
        cut = text[:TTS_MAX_CHARS]
        text = cut[: max(cut.rfind(". "), cut.rfind("। "), 200) + 1]
    return text


def synthesize(text: str, language: str, voice: str, api_key: str) -> bytes:
    """Returns MP3 bytes."""
    if not api_key:
        raise ServiceError("Gnani API key is missing. Add GNANI_API_KEY in settings.")
    payload = {
        "text": speakable(text), "model": "timbre-v3.0", "voice": voice,
        "language": LANGUAGES[language][1], "speed": 1.0,
        "audio_config": {"container": "mp3", "bitrate": "128k", "sample_rate": 24000},
    }
    r = post_with_retry(
        URL, what="Voice generation",
        headers={"X-API-Key-ID": api_key, "Content-Type": "application/json"}, json=payload,
    )
    if r.status_code == 200 and r.content:
        return r.content
    if r.status_code == 403:
        raise ServiceError("This Gnani key cannot use text-to-speech (scope or credits).")
    if r.status_code in (401, 402):
        raise ServiceError("Gnani rejected the key or credits are exhausted.")
    raise ServiceError(f"Voice generation failed (HTTP {r.status_code}). The text answer is still available.")
