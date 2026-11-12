"""Google Gemini via the public generateContent REST endpoint (x-goog-api-key header)."""
from config import HISTORY_TURNS, LANGUAGES
from services.errors import ServiceError
from services.http import post_with_retry

BASE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM = (
    "You are Bharat Voice AI, a friendly voice assistant for people in India. "
    "Your answer will be read aloud, so write 2 to 4 short plain sentences. "
    "No markdown, no bullet points, no emojis. Write numbers and amounts the way they are spoken. "
    "Reply in {lang}. If the question is unclear, ask one short clarifying question. "
    "For medical, legal or money questions give general information and suggest asking a qualified person. "
    "Never invent facts; say when you are not sure."
)


def build_payload(history, lang_label):
    hint = LANGUAGES[lang_label][2]
    contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["text"]}]}
                for m in history[-HISTORY_TURNS * 2:]]
    return {
        "system_instruction": {"parts": [{"text": SYSTEM.format(lang=hint)}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 1024},
    }


def reply(history, lang_label, api_key, model):
    if not api_key:
        raise ServiceError("Gemini API key is missing. Add GEMINI_API_KEY in settings.")
    r = post_with_retry(
        BASE.format(model=model), what="Gemini",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json=build_payload(history, lang_label),
    )
    if r.status_code in (400, 401, 403):
        raise ServiceError(f"Gemini rejected the request (HTTP {r.status_code}). Check GEMINI_API_KEY and GEMINI_MODEL.")
    if r.status_code == 404:
        raise ServiceError(f"Gemini model '{model}' was not found. Set GEMINI_MODEL to a model available to your key.")
    if r.status_code != 200:
        raise ServiceError(f"Gemini failed (HTTP {r.status_code}). Please try again.")
    try:
        parts = r.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError, ValueError):
        text = ""
    if not text:
        raise ServiceError("Gemini returned no answer (it may have blocked the topic). Try rephrasing.")
    return text
