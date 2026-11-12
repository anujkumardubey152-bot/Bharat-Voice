import io
import wave
from config import MAX_AUDIO_BYTES, MAX_AUDIO_SECONDS
from services.errors import ServiceError


def validate_wav(data: bytes) -> float:
    """Check recorded audio. Returns duration in seconds. Raises ServiceError with a fix."""
    if not data:
        raise ServiceError("No audio was recorded. Tap the microphone and try again.")
    if len(data) > MAX_AUDIO_BYTES:
        raise ServiceError("Recording is too large. Keep it under 30 seconds.")
    try:
        with wave.open(io.BytesIO(data)) as w:
            seconds = w.getnframes() / float(w.getframerate())
    except Exception:
        return 0.0  # not a WAV we can inspect; let Gnani decide
    if seconds < 0.3:
        raise ServiceError("Recording was too short. Speak for at least a second.")
    if seconds > MAX_AUDIO_SECONDS:
        raise ServiceError(f"Recording is {seconds:.0f}s long. Gnani accepts up to {MAX_AUDIO_SECONDS}s. Record a shorter message.")
    return seconds
