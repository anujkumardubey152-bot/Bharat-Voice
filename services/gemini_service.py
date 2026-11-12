"""Google Gemini via the public generateContent REST endpoint (x-goog-api-key header).
If the configured model is not found, the app asks Google which models your key can use and picks one."""
import requests
from config import HISTORY_TURNS, LANGUAGES
from services.errors import ServiceError
from services.http import post_with_retry

ROOT = "https://generativelanguage.googleapis.com/v1beta"
BASE = ROOT + "/models/{model}:generateContent"
_BAD = ("image", "tts", "live", "audio", "embedding", "robotics", "computer", "lite", "vision", "aqa")
FALLBACKS = ("gemini-3.8-flash", "gemini-3.6-flash", "gemini-3-flash-preview")
_found = {}  # api key -> discovered model name (kept in memory only)

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
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 2048},
    }


def pick_model(models):
    names = [m["name"].split("/", 1)[-1] for m in models
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    names = [n for n in names if n.startswith("gemini") and not any(b in n for b in _BAD)]
    for pref in ("flash", "pro"):
        c = sorted((n for n in names if pref in n), key=lambda n: ("preview" in n or "exp" in n, n))
        if c:
            return c[0]
    return names[0] if names else None


def discover_model(api_key):
    try:
        r = requests.get(ROOT + "/models", headers={"x-goog-api-key": api_key}, params={"pageSize": 100}, timeout=20)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    return pick_model(r.json().get("models", []))


def _call(model, history, lang_label, api_key):
    return post_with_retry(
        BASE.format(model=model), what="Gemini",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json=build_payload(history, lang_label),
    )


def reply(history, lang_label, api_key, model):
    if not api_key:
        raise ServiceError("Gemini API key is missing. Add GEMINI_API_KEY in settings.")
    tried = [_found.get(api_key, model)] + [m for m in FALLBACKS if m != model]
    r = None
    for m in tried:
        r = _call(m, history, lang_label, api_key)
        if r.status_code != 404:
            _found[api_key] = m
            break
    else:
        alt = discover_model(api_key)
        if not alt or alt in tried:
            raise ServiceError("No Gemini model was found for this key. Set GEMINI_MODEL to a current model name "
                               "from ai.google.dev/gemini-api/docs/models (for example gemini-3.8-flash).")
        _found[api_key] = alt
        r = _call(alt, history, lang_label, api_key)
    if r.status_code in (400, 401, 403):
        raise ServiceError(f"Gemini rejected the request (HTTP {r.status_code}). Check GEMINI_API_KEY "
                           "(a key from aistudio.google.com/apikey; AQ. keys are valid).")
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
