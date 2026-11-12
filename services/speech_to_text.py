"""Gnani Prisma v3.0 REST. Source: docs.gnani.ai/api/STT/speech-to-text"""
from config import LANGUAGES
from services.errors import ServiceError
from services.http import post_with_retry

URL = "https://api.vachana.ai/stt/v3"


def transcribe(audio: bytes, language: str, api_key: str):
    """Returns (transcript, detected_language_code or None)."""
    if not api_key:
        raise ServiceError("Gnani API key is missing. Add GNANI_API_KEY in settings.")
    code = LANGUAGES[language][0]
    data = {"model": "prisma-v3.0", "language_code": code}
    if language == "Hinglish":
        data["format"] = "codemix"  # keeps English words in Latin script
    r = post_with_retry(
        URL, what="Speech recognition",
        headers={"X-API-Key-ID": api_key},
        files={"audio_file": ("recording.wav", audio, "audio/wav")},
        data=data,
    )
    if r.status_code == 200:
        body = r.json()
        text = (body.get("transcript") or "").strip()
        if not text:
            raise ServiceError("No speech was detected. Move closer to the microphone and try again.")
        return text, body.get("detected_language_code")
    raise ServiceError(_explain(r))


def _explain(r) -> str:
    code = None
    try:
        j = r.json()
        d = j.get("detail")
        if isinstance(d, dict):
            code = d.get("error_code")
        elif isinstance(j.get("error"), dict):
            code = j["error"].get("type")
    except Exception:
        pass
    s = r.status_code
    if s == 401:
        return "Gnani rejected the API key. Check GNANI_API_KEY."
    if s == 402:
        return "Gnani credits are exhausted."
    if s == 403:
        return "This Gnani key cannot use speech recognition (scope or credits). Create a key with STT and TTS access."
    if code == "MAX_AUDIO_DURATION_EXCEEDED":
        return "Recording is longer than 30 seconds. Record a shorter message."
    return f"Speech recognition failed (HTTP {s}). You can type your message instead."
