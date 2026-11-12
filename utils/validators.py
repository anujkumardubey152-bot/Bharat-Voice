from config import MAX_TEXT_CHARS
from services.errors import ServiceError


def clean_text(text: str) -> str:
    text = (text or "").strip()
    if not text:
        raise ServiceError("Type or record something first.")
    if len(text) > MAX_TEXT_CHARS:
        raise ServiceError(f"Message is too long. Keep it under {MAX_TEXT_CHARS} characters.")
    return text
