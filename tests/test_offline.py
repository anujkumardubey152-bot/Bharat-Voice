"""Offline tests with mocked HTTP. These do NOT prove the real APIs work."""
import io, wave, unittest
from unittest.mock import patch, MagicMock
from services import speech_to_text as stt, gemini_service as g, text_to_speech as tts
from services.errors import ServiceError
from utils.audio_utils import validate_wav


def wav(seconds):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))
    return b.getvalue()


def resp(status=200, js=None, content=b""):
    r = MagicMock(); r.status_code = status; r.json.return_value = js or {}; r.content = content
    return r


class T(unittest.TestCase):
    def test_audio_validation(self):
        self.assertAlmostEqual(validate_wav(wav(2)), 2, places=1)
        for bad in (b"", wav(0.1), wav(31)):
            with self.assertRaises(ServiceError): validate_wav(bad)

    @patch("services.http.requests.post")
    def test_stt_ok_and_params(self, p):
        p.return_value = resp(js={"transcript": "नमस्ते", "detected_language_code": "hi-IN"})
        self.assertEqual(stt.transcribe(wav(1), "Hinglish", "k"), ("नमस्ते", "hi-IN"))
        kw = p.call_args.kwargs
        self.assertEqual(kw["data"]["model"], "prisma-v3.0")
        self.assertEqual(kw["data"]["format"], "codemix")
        self.assertEqual(kw["headers"], {"X-API-Key-ID": "k"})

    @patch("services.http.requests.post")
    def test_stt_empty_and_403(self, p):
        p.return_value = resp(js={"transcript": ""})
        with self.assertRaises(ServiceError): stt.transcribe(wav(1), "Hindi", "k")
        p.return_value = resp(403, {"detail": {"error_code": "SCOPE_NOT_ALLOWED"}})
        with self.assertRaises(ServiceError): stt.transcribe(wav(1), "Hindi", "k")

    @patch("services.http.time.sleep")
    @patch("services.http.requests.post")
    def test_retry_on_429(self, p, _s):
        p.side_effect = [resp(429), resp(200, {"transcript": "hi"})]
        self.assertEqual(stt.transcribe(wav(1), "English", "k")[0], "hi")
        self.assertEqual(p.call_count, 2)

    @patch("services.http.requests.post")
    def test_gemini(self, p):
        p.return_value = resp(js={"candidates": [{"content": {"parts": [{"text": "Namaste."}]}}]})
        h = [{"role": "user", "text": "hi"}]
        self.assertEqual(g.reply(h, "Hindi", "k", "m"), "Namaste.")
        self.assertEqual(p.call_args.kwargs["headers"]["x-goog-api-key"], "k")
        p.return_value = resp(js={"candidates": []})
        with self.assertRaises(ServiceError): g.reply(h, "Hindi", "k", "m")
        p.return_value = resp(404)
        with self.assertRaises(ServiceError): g.reply(h, "Hindi", "k", "m")

    @patch("services.http.requests.post")
    def test_tts(self, p):
        p.return_value = resp(content=b"ID3audio")
        self.assertEqual(tts.synthesize("**Hello**", "Hinglish", "Shivani", "k"), b"ID3audio")
        body = p.call_args.kwargs["json"]
        self.assertEqual((body["model"], body["language"], body["text"]), ("timbre-v3.0", "hi-en", "Hello"))
        p.return_value = resp(500)
        with patch("services.http.time.sleep"), self.assertRaises(ServiceError):
            tts.synthesize("x", "Hindi", "Shivani", "k")

    def test_missing_keys(self):
        for f in (lambda: stt.transcribe(b"x", "Hindi", ""), lambda: g.reply([], "Hindi", "", "m"),
                  lambda: tts.synthesize("x", "Hindi", "Shivani", "")):
            with self.assertRaises(ServiceError): f()


if __name__ == "__main__":
    unittest.main()
