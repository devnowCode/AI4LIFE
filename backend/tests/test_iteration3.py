"""AI4LIFE iteration 3 tests.

Coverage:
- GET /api/ version bumped to 1.2.0
- POST /api/transcribe (Whisper) with real WAV; also 400 for >25MB
- POST /api/orchestrate with weights_override alters routing (cost-heavy -> Gemini)
- POST /api/orchestrate/stream includes weights_override in meta event
- Image persistence: orchestrate image_generation -> /sessions/{id}/messages returns full data_url
- Intent bug fix: 'genera immagine minimalista di una foglia' -> image_generation
- Regression sanity: existing endpoints still work
"""
from __future__ import annotations

import base64
import io
import json
import os
import time
import uuid
from typing import Any

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

TIMEOUT_SHORT = 30
TIMEOUT_LLM = 180
TIMEOUT_IMG = 240

AUDIO_FIXTURE = "/app/test_fixtures/audio.wav"


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --------------------------- Version ---------------------------
class TestVersion:
    def test_root_version_1_2_0(self, api_client):
        r = api_client.get(f"{API}/", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        assert d["version"] == "1.2.0", f"Expected 1.2.0, got {d.get('version')}"
        assert d["app"] == "AI4LIFE"
        assert d["status"] == "online"


# --------------------------- Intent bug fix ---------------------------
class TestIntentBugFix:
    def test_multi_word_phrase_wins_over_single_word(self, api_client):
        """'genera immagine minimalista di una foglia' must be image_generation, not multimodal."""
        r = api_client.post(
            f"{API}/intent",
            json={"prompt": "genera immagine minimalista di una foglia"},
            timeout=TIMEOUT_SHORT,
        )
        assert r.status_code == 200
        d = r.json()
        assert d["intent_id"] == "image_generation", (
            f"Expected image_generation, got {d['intent_id']} (top: {d.get('top_candidates')})"
        )
        assert "genera immagine" in d["matched_keywords"]

    def test_pure_image_multimodal_still_multimodal_when_files(self, api_client):
        """When has_files=True with just 'immagine', multimodal boost should still promote multimodal."""
        r = api_client.post(
            f"{API}/intent",
            json={"prompt": "descrivi questa immagine", "has_files": True, "has_images": True},
            timeout=TIMEOUT_SHORT,
        )
        assert r.status_code == 200
        d = r.json()
        assert d["intent_id"] == "multimodal", f"Expected multimodal, got {d['intent_id']}"


# --------------------------- Whisper transcribe ---------------------------
class TestTranscribe:
    def test_transcribe_real_wav(self, api_client):
        """POST audio to /api/transcribe and expect {text, language}."""
        assert os.path.exists(AUDIO_FIXTURE), "Missing WAV fixture"
        with open(AUDIO_FIXTURE, "rb") as fh:
            files = {"audio": ("recording.wav", fh, "audio/wav")}
            data = {"language": "it"}
            # Remove default Content-Type: json header for multipart
            r = requests.post(
                f"{API}/transcribe",
                files=files,
                data=data,
                timeout=TIMEOUT_LLM,
            )
        assert r.status_code == 200, f"Body: {r.text}"
        d = r.json()
        assert "text" in d
        assert "language" in d
        assert d["language"] == "it"
        # A 1.5s 440Hz tone likely transcribes to empty or noise, but the endpoint
        # must succeed and return the shape. text may be empty string.
        assert isinstance(d["text"], str)

    def test_transcribe_rejects_oversize(self, api_client):
        """>25MB payload should return 400."""
        # 26 MB of zero bytes - valid multipart, backend must reject at size check
        big = b"\x00" * (26 * 1024 * 1024)
        files = {"audio": ("huge.wav", io.BytesIO(big), "audio/wav")}
        data = {"language": "it"}
        r = requests.post(
            f"{API}/transcribe",
            files=files,
            data=data,
            timeout=TIMEOUT_LLM,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text[:200]}"
        detail = r.json().get("detail", "").lower()
        assert "25mb" in detail or "grande" in detail or "large" in detail, detail


# --------------------------- Weights override ---------------------------
class TestWeightsOverride:
    def test_weights_override_prefers_cheap_gemini_for_text(self, api_client):
        """With cost-heavy weights, Gemini 3 Flash (highest cost_efficiency=95) should win over GPT-5.2 on a text prompt."""
        sid = str(uuid.uuid4())
        r = api_client.post(
            f"{API}/orchestrate",
            json={
                "prompt": "Ciao, dimmi cosa è python in una frase.",
                "session_id": sid,
                "weights_override": {
                    "cost": 0.8,
                    "capability": 0.1,
                    "latency": 0.05,
                    "context_bonus": 0.05,
                },
            },
            timeout=TIMEOUT_LLM,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        sel_id = d["routing"]["selected"]["id"]
        assert sel_id == "gemini-3-flash", (
            f"With cost-heavy weights expected gemini-3-flash, got {sel_id}. "
            f"Weights applied: {d['routing']['weights']}"
        )
        # Ensure weights_override was actually merged
        w = d["routing"]["weights"]
        assert abs(w["cost"] - 0.8) < 1e-6
        assert abs(w["capability"] - 0.1) < 1e-6
        # LLM should still work
        assert not d["result"].startswith("[Errore inference"), d["result"]

    def test_default_weights_still_prefer_gpt52_for_reasoning(self, api_client):
        """Sanity: without override, code intent still routes to gpt-5.2."""
        r = api_client.post(
            f"{API}/orchestrate",
            json={"prompt": "Scrivi funzione python per calcolare fibonacci."},
            timeout=TIMEOUT_LLM,
        )
        assert r.status_code == 200
        d = r.json()
        assert d["routing"]["selected"]["id"] == "gpt-5.2"


# --------------------------- Stream weights_override ---------------------------
class TestStreamWeights:
    def _consume_sse(self, resp) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        buf = ""
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            if not chunk:
                continue
            buf += chunk
            while "\n\n" in buf:
                frame, buf = buf.split("\n\n", 1)
                for line in frame.splitlines():
                    if line.startswith("data:"):
                        try:
                            evt = json.loads(line[5:].strip())
                        except Exception:
                            continue
                        events.append(evt)
        return events

    def test_stream_meta_reflects_weights_override(self, api_client):
        sid = str(uuid.uuid4())
        with api_client.post(
            f"{API}/orchestrate/stream",
            json={
                "prompt": "Ciao, breve saluto.",
                "session_id": sid,
                "weights_override": {
                    "cost": 0.8, "capability": 0.1, "latency": 0.05, "context_bonus": 0.05,
                },
            },
            stream=True,
            timeout=TIMEOUT_LLM,
        ) as r:
            assert r.status_code == 200, r.text
            events = self._consume_sse(r)

        metas = [e for e in events if e.get("type") == "meta"]
        assert metas, "No meta event received"
        meta = metas[0]
        w = meta["routing"]["weights"]
        assert abs(w["cost"] - 0.8) < 1e-6, f"Weights not merged in stream meta: {w}"
        assert meta["routing"]["selected"]["id"] == "gemini-3-flash"


# --------------------------- Image persistence ---------------------------
class TestImagePersistence:
    def test_image_stored_inline_and_retrievable_via_messages(self, api_client):
        """image_generation intent -> full data_url in images[] persisted -> GET session messages returns it."""
        sid = str(uuid.uuid4())
        r = api_client.post(
            f"{API}/orchestrate",
            json={
                "prompt": "genera immagine minimalista di una foglia verde",
                "session_id": sid,
            },
            timeout=TIMEOUT_IMG,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        # Confirms intent bug-fix at the routing level too
        assert d["intent"]["intent_id"] == "image_generation"
        assert d["routing"]["selected"]["type"] == "image"
        imgs = d.get("images") or []
        if not imgs:
            pytest.fail(f"No images returned. result={d.get('result')!r}")
        assert imgs[0]["data_url"].startswith("data:image/")

        # Now fetch messages and ensure full data_url is present (not just has_images flag)
        r2 = api_client.get(f"{API}/sessions/{sid}/messages", timeout=TIMEOUT_SHORT)
        assert r2.status_code == 200
        msgs = r2.json()["messages"]
        assert len(msgs) == 1, f"Expected 1 message, got {len(msgs)}"
        m = msgs[0]
        assert m.get("has_images") is True
        assert m.get("num_images", 0) >= 1
        assert "images" in m
        assert isinstance(m["images"], list)
        assert len(m["images"]) >= 1
        stored = m["images"][0]
        assert "data_url" in stored, f"Stored image missing data_url: {stored}"
        assert stored["data_url"].startswith("data:image/")
        # Decode & verify real bytes
        header, _, b64 = stored["data_url"].partition(",")
        raw = base64.b64decode(b64)
        assert len(raw) > 1024, f"Persisted image too small: {len(raw)} bytes"


# --------------------------- Regression ---------------------------
class TestRegression:
    def test_orchestrate_still_400_on_empty(self, api_client):
        r = api_client.post(f"{API}/orchestrate", json={"prompt": "", "files": []},
                            timeout=TIMEOUT_SHORT)
        assert r.status_code == 400

    def test_sessions_endpoint(self, api_client):
        r = api_client.get(f"{API}/sessions", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        assert "sessions" in r.json()

    def test_models_still_5(self, api_client):
        r = api_client.get(f"{API}/models", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        assert len(r.json()["models"]) == 5

    def test_compare_still_ok(self, api_client):
        r = api_client.post(
            f"{API}/compare",
            json={
                "prompt": "Ciao in italiano una parola.",
                "model_ids": ["gpt-5.2", "gemini-3-flash"],
            },
            timeout=TIMEOUT_LLM,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["results"]) == 2
        for c in d["results"]:
            assert c["ok"] is True, c
