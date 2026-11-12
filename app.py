"""Bharat Voice AI - Streamlit app. Voice -> Gnani Prisma -> Gemini -> Gnani Timbre."""
import html
import uuid
import streamlit as st

from config import LANGUAGES, TESTED_LANGUAGES, VOICES, get_settings
from services import gemini_service, speech_to_text, text_to_speech
from services.errors import ServiceError
from utils.audio_utils import validate_wav
from utils.validators import clean_text

st.set_page_config(page_title="Bharat Voice AI", page_icon="🎙️", layout="wide",
                   initial_sidebar_state="auto")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind:wght@400;500;600&family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap');
:root{--bg:#141416;--panel:#1B1B1E;--line:#2C2C31;--text:#ECE8E1;--mute:#9A968E;--accent:#E3A53B;--ok:#6FBF8B;--err:#E5736A;}
html,body,[class*="css"],.stApp{font-family:'Hind',system-ui,sans-serif;}
#MainMenu,footer,header[data-testid="stHeader"]{visibility:hidden;height:0}
.block-container{max-width:860px;padding-top:1.2rem;padding-bottom:7rem}
h1.hero{font-family:'Fraunces',serif;font-weight:600;font-size:clamp(2rem,6vw,3.2rem);line-height:1.1;margin:2.2rem 0 .8rem;letter-spacing:-.01em}
.sub{color:var(--mute);font-size:1.08rem;max-width:34rem;line-height:1.55}
.topbar{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:.7rem;margin-bottom:1rem}
.brand{font-family:'Fraunces',serif;font-weight:600;font-size:1.25rem}
.chip{font-size:.85rem;border:1px solid var(--line);border-radius:6px;padding:.2rem .6rem;color:var(--mute)}
.chip.ok{color:var(--ok);border-color:#2F4A3A}.chip.err{color:var(--err);border-color:#5A302C}
.bubble{padding:.7rem .95rem;border-radius:10px;margin:.5rem 0;line-height:1.6;max-width:92%;white-space:normal;border:1px solid var(--line)}
.bubble.user{background:#22221F;margin-left:auto;border-color:#3A3426}
.bubble.ai{background:var(--panel)}
.meta{font-size:.78rem;color:var(--mute);margin:.9rem 0 -.2rem}
.meta.user{text-align:right}
.mic-wrap{border:1px solid var(--line);border-radius:12px;padding:.8rem;background:var(--panel);margin-top:.8rem}
.stage{font-size:.95rem;color:var(--accent);margin:.2rem 0 .4rem;min-height:1.4rem}
.stButton>button{border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--text)}
.stButton>button[kind="primary"]{background:var(--accent);color:#1a1405;border:0;font-weight:600}
.stButton>button:focus-visible,input:focus-visible{outline:2px solid var(--accent)!important}
.uc{border-left:2px solid var(--accent);padding:.1rem 0 .1rem .8rem;margin:.7rem 0;color:var(--text)}
.uc span{color:var(--mute);display:block;font-size:.92rem}
@media (max-width:640px){.block-container{padding-left:.8rem;padding-right:.8rem}.bubble{max-width:100%}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
S = get_settings()

# ---------- session state ----------
ss = st.session_state
ss.setdefault("view", "landing")
ss.setdefault("convs", {})
ss.setdefault("active", None)
ss.setdefault("mic_n", 0)
ss.setdefault("draft_input", "")
ss.setdefault("pending", None)       # text waiting to be sent
ss.setdefault("pending_voice", False)
ss.setdefault("notice", None)
ss.setdefault("autoplay_id", None)
ss.setdefault("lang", "Auto-detect")
ss.setdefault("voice", "Shivani")
ss.setdefault("review", True)


def new_conv():
    cid = uuid.uuid4().hex[:8]
    ss.convs[cid] = {"title": "New conversation", "messages": []}
    ss.active = cid


if ss.active is None or ss.active not in ss.convs:
    new_conv()
conv = ss.convs[ss.active]


def on_send():
    text = ss.draft_input
    ss.draft_input = ""
    if text.strip():
        ss.pending = text
    elif ss.pending is None:
        ss.notice = "Type or record something first."


def esc(t: str) -> str:
    return html.escape(t).replace("\n", "<br>")


# ---------- landing ----------
if ss.view == "landing":
    st.markdown('<div class="brand">Bharat Voice AI</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero">Your Language.<br>Your Voice. Your AI.</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub">Speak a question in Hindi, English or Hinglish. Bharat Voice AI listens, '
                'thinks, and answers out loud in the same language. No typing needed.</p>', unsafe_allow_html=True)
    if st.button("Start conversation", type="primary"):
        ss.view = "app"
        st.rerun()
    st.markdown("""
<div class="uc">Ask about a government scheme<span>Get a plain-language explanation you can listen to.</span></div>
<div class="uc">Clear a study doubt<span>Ask follow-up questions as you would to a teacher.</span></div>
<div class="uc">Get help without reading a screen<span>Voice in, voice out, for people who prefer speaking.</span></div>
""", unsafe_allow_html=True)
    st.caption("Speech recognition and voice: Gnani Prisma v3.0 and Timbre v3.0 (10 Indian languages in the API). "
               "Answers: Google Gemini. Hindi, English and Hinglish are the tested demo languages.")
    st.stop()

# ---------- sidebar ----------
with st.sidebar:
    st.markdown("**Bharat Voice AI**")
    if st.button("New conversation", use_container_width=True, type="primary"):
        new_conv()
        st.rerun()
    st.caption("History (this session)")
    for cid, c in reversed(list(ss.convs.items())):
        label = ("● " if cid == ss.active else "") + c["title"]
        if st.button(label, key=f"h_{cid}", use_container_width=True):
            ss.active = cid
            st.rerun()
    st.divider()
    ss.lang = st.selectbox("Language", list(LANGUAGES), index=list(LANGUAGES).index(ss.lang))
    if ss.lang not in TESTED_LANGUAGES and ss.lang != "Auto-detect":
        st.caption("Supported by the Gnani API but not tested by the builder.")
    ss.voice = st.selectbox("Voice", VOICES, index=VOICES.index(ss.voice))
    ss.review = st.toggle("Review text before sending", value=ss.review)
    if st.button("Clear conversation", use_container_width=True):
        conv["messages"].clear()
        conv["title"] = "New conversation"
        st.rerun()

# ---------- header ----------
chip = ('<span class="chip ok">API keys set</span>' if S.ready
        else '<span class="chip err">Setup needed</span>')
st.markdown(f'<div class="topbar"><span class="brand">Bharat Voice AI</span>{chip}</div>', unsafe_allow_html=True)
if not S.ready:
    st.error("Add GNANI_API_KEY and GEMINI_API_KEY in Streamlit secrets or your .env file. See README.")
if ss.notice:
    st.warning(ss.notice)
    ss.notice = None

stage = st.empty()


def set_stage(text: str):
    stage.markdown(f'<div class="stage">{html.escape(text)}</div>', unsafe_allow_html=True)


# ---------- voice input ----------
mic_slot = st.container()
with mic_slot:
    st.markdown('<div class="mic-wrap">', unsafe_allow_html=True)
    audio = st.audio_input("Tap the microphone, speak (up to 30 seconds), then stop", key=f"mic_{ss.mic_n}")
    st.markdown('</div>', unsafe_allow_html=True)

if audio is not None and S.ready:
    try:
        set_stage("Analysing your audio…")
        data = audio.getvalue()
        validate_wav(data)
        text, detected = speech_to_text.transcribe(data, ss.lang, S.gnani_key)
        if ss.review:
            ss.draft_input = text
            ss.notice = None
            set_stage("Heard you. Check the text below, then press Send.")
        else:
            ss.pending = text
            ss.pending_voice = True
    except ServiceError as e:
        ss.notice = str(e)
    ss.mic_n += 1
    if ss.pending is not None or ss.notice or ss.review:
        st.rerun()

# ---------- text input ----------
c1, c2 = st.columns([5, 1])
with c1:
    st.text_input("Message", key="draft_input", placeholder="Type here, or record above",
                  label_visibility="collapsed", on_change=on_send)
with c2:
    st.button("Send", on_click=on_send, use_container_width=True, type="primary")

# ---------- run a turn ----------
if ss.pending is not None:
    text, ss.pending = ss.pending, None
    try:
        text = clean_text(text)
        conv["messages"].append({"id": uuid.uuid4().hex[:6], "role": "user", "text": text,
                                 "voice": ss.pending_voice})
        ss.pending_voice = False
        if conv["title"] == "New conversation":
            conv["title"] = text[:34] + ("…" if len(text) > 34 else "")
        set_stage("Thinking…")
        answer = gemini_service.reply(conv["messages"], ss.lang, S.gemini_key, S.gemini_model)
        msg = {"id": uuid.uuid4().hex[:6], "role": "ai", "text": answer, "audio": None}
        conv["messages"].append(msg)
        set_stage("Generating voice…")
        try:
            msg["audio"] = text_to_speech.synthesize(answer, ss.lang, ss.voice, S.gnani_key)
            ss.autoplay_id = msg["id"]
        except ServiceError as e:
            ss.notice = str(e)
    except ServiceError as e:
        ss.notice = str(e)
    ss.pending_voice = False
    st.rerun()

# ---------- conversation ----------
if not conv["messages"]:
    st.markdown('<p class="sub" style="margin-top:1.2rem">Record a question or type one. '
                'Try: “Mujhe PM Kisan yojana ke baare mein batao.”</p>', unsafe_allow_html=True)
for m in conv["messages"]:
    if m["role"] == "user":
        tag = "You · spoken, recognised text" if m.get("voice") else "You"
        st.markdown(f'<div class="meta user">{tag}</div><div class="bubble user">{esc(m["text"])}</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="meta">Bharat Voice AI</div><div class="bubble ai">{esc(m["text"])}</div>',
                    unsafe_allow_html=True)
        if m.get("audio"):
            auto = ss.autoplay_id == m["id"]
            st.audio(m["audio"], format="audio/mpeg", autoplay=auto)
            if auto:
                ss.autoplay_id = None
        else:
            st.caption("Voice not available for this answer.")
