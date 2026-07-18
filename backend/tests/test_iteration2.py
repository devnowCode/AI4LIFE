"""AI4LIFE iteration 2 tests: SSE streaming, MongoDB sessions, Compare,
GPT-image-1 real image, multi-turn context injection.

All tests hit the public preview URL via REACT_APP_BACKEND_URL.
"""
from __future__ import annotations

import base64
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
TIMEOUT_LLM = 180  # LLM calls
TIMEOUT_IMG = 180  # image generation can take 60s+


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --------------------------- Version / root ---------------------------
class TestVersion:
    def test_root_version_is_1_1_0(self, api_client):
        r = api_client.get(f"{API}/", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        assert d["version"] == "1.1.0", f"Expected 1.1.0 got {d.get('version')}"


# --------------------------- SSE streaming ---------------------------
class TestSSEStream:
    def _consume_sse(self, resp) -> list[dict[str, Any]]:
        """Consume SSE stream and return decoded events list."""
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

    def test_stream_emits_meta_tokens_done(self, api_client):
        """Verify SSE emits: meta first, N token frames, then done with result."""
        sid = str(uuid.uuid4())
        with api_client.post(
            f"{API}/orchestrate/stream",
            json={"prompt": "Rispondi in italiano: cosa è FastAPI? Massimo 2 frasi.",
                  "session_id": sid},
            stream=True,
            timeout=TIMEOUT_LLM,
        ) as r:
            assert r.status_code == 200, r.text
            assert "text/event-stream" in r.headers.get("content-type", "")
            events = self._consume_sse(r)

        assert len(events) >= 3, f"Expected >=3 events got {len(events)}"
        assert events[0]["type"] == "meta", f"First event should be meta, got {events[0]}"
        assert "session_id" in events[0]
        assert "routing" in events[0]

        token_events = [e for e in events if e["type"] == "token"]
        done_events = [e for e in events if e["type"] == "done"]
        error_events = [e for e in events if e["type"] == "error"]

        assert not error_events, f"Stream had errors: {error_events}"
        assert len(token_events) >= 1, "No token events streamed"
        assert len(done_events) == 1, f"Expected exactly 1 done event, got {len(done_events)}"

        # Ensure meta arrived before first token (real streaming ordering)
        assert events.index(events[0]) < events.index(token_events[0])

        final = done_events[0]
        assert "result" in final
        assert isinstance(final["result"], str)
        assert len(final["result"]) > 10, f"Result too short: {final['result']!r}"
        assert not final["result"].startswith("[Errore"), f"LLM error: {final['result']}"

        # Concatenated tokens should approximately equal final result
        concat = "".join(e.get("delta", "") for e in token_events)
        assert len(concat) > 0

    def test_stream_persists_to_mongo(self, api_client):
        """After streaming, session must appear in /api/sessions with turn_count>=1."""
        sid = str(uuid.uuid4())
        with api_client.post(
            f"{API}/orchestrate/stream",
            json={"prompt": "Ciao in una parola", "session_id": sid},
            stream=True,
            timeout=TIMEOUT_LLM,
        ) as r:
            assert r.status_code == 200
            # drain
            for _ in r.iter_content(chunk_size=None):
                pass

        # Give Mongo a brief moment
        time.sleep(0.5)
        r2 = api_client.get(f"{API}/sessions", timeout=TIMEOUT_SHORT)
        assert r2.status_code == 200
        sessions = r2.json()["sessions"]
        match = next((s for s in sessions if s["id"] == sid), None)
        assert match is not None, f"Session {sid} not persisted"
        assert match["turn_count"] >= 1
        assert match.get("last_model")


# --------------------------- Non-streaming still works + persistence ---------------------------
class TestOrchestratePersistence:
    def test_orchestrate_creates_message_row(self, api_client):
        sid = str(uuid.uuid4())
        r = api_client.post(
            f"{API}/orchestrate",
            json={"prompt": "Dimmi 'ciao' in italiano.", "session_id": sid},
            timeout=TIMEOUT_LLM,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["session_id"] == sid
        assert not d["result"].startswith("[Errore"), d["result"]

        # Verify Mongo row via /messages endpoint
        r2 = api_client.get(f"{API}/sessions/{sid}/messages", timeout=TIMEOUT_SHORT)
        assert r2.status_code == 200
        msgs = r2.json()["messages"]
        assert len(msgs) >= 1
        assert msgs[0]["session_id"] == sid
        assert msgs[0]["prompt"] == "Dimmi 'ciao' in italiano."
        assert "result" in msgs[0]
        assert "intent" in msgs[0]
        # Must not leak Mongo _id
        assert "_id" not in msgs[0]


# --------------------------- Sessions endpoints ---------------------------
class TestSessions:
    @pytest.fixture(scope="class")
    def seeded_session(self, api_client):
        sid = str(uuid.uuid4())
        r = api_client.post(
            f"{API}/orchestrate",
            json={"prompt": "Test sessione: dimmi 1+1 in italiano.", "session_id": sid},
            timeout=TIMEOUT_LLM,
        )
        assert r.status_code == 200
        return sid

    def test_list_sessions_shape(self, api_client, seeded_session):
        r = api_client.get(f"{API}/sessions", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        assert "sessions" in d
        sessions = d["sessions"]
        assert isinstance(sessions, list)
        our = next((s for s in sessions if s["id"] == seeded_session), None)
        assert our is not None
        assert "turn_count" in our
        assert "last_model" in our
        assert "updated_at" in our
        assert "title" in our
        assert "_id" not in our

    def test_get_session_history(self, api_client, seeded_session):
        r = api_client.get(f"{API}/sessions/{seeded_session}/messages",
                           timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        assert d["session_id"] == seeded_session
        msgs = d["messages"]
        assert len(msgs) >= 1
        m = msgs[0]
        for key in ("id", "session_id", "prompt", "result", "intent",
                    "routing_selected", "created_at"):
            assert key in m
        assert "_id" not in m

    def test_delete_session(self, api_client):
        # Create a disposable session
        sid = str(uuid.uuid4())
        r = api_client.post(
            f"{API}/orchestrate",
            json={"prompt": "temp session for delete", "session_id": sid},
            timeout=TIMEOUT_LLM,
        )
        assert r.status_code == 200

        d = api_client.delete(f"{API}/sessions/{sid}", timeout=TIMEOUT_SHORT)
        assert d.status_code == 200
        payload = d.json()
        assert payload["session_id"] == sid
        assert payload["deleted_messages"] >= 1

        # Confirm gone
        r2 = api_client.get(f"{API}/sessions/{sid}/messages", timeout=TIMEOUT_SHORT)
        assert r2.status_code == 200
        assert r2.json()["messages"] == []

        r3 = api_client.get(f"{API}/sessions", timeout=TIMEOUT_SHORT)
        assert not any(s["id"] == sid for s in r3.json()["sessions"])


# --------------------------- Multi-turn context injection ---------------------------
class TestMultiTurn:
    def test_multi_turn_context_reference(self, api_client):
        """Send two prompts in same session; second must be able to reference first."""
        sid = str(uuid.uuid4())
        # Turn 1 - establish context
        r1 = api_client.post(
            f"{API}/orchestrate",
            json={"prompt": "Ricorda questo numero: 4242. Ripetimelo.", "session_id": sid},
            timeout=TIMEOUT_LLM,
        )
        assert r1.status_code == 200
        first = r1.json()["result"]
        assert not first.startswith("[Errore"), first

        # Turn 2 - reference context
        r2 = api_client.post(
            f"{API}/orchestrate",
            json={"prompt": "Qual è il numero che ti avevo appena chiesto di ricordare? Rispondi solo con il numero.",
                  "session_id": sid},
            timeout=TIMEOUT_LLM,
        )
        assert r2.status_code == 200
        second = r2.json()["result"]
        assert not second.startswith("[Errore"), second

        # Verify context propagated (either LLM recall or by inspecting prior_turns in DB)
        r3 = api_client.get(f"{API}/sessions/{sid}/messages", timeout=TIMEOUT_SHORT)
        msgs = r3.json()["messages"]
        assert len(msgs) == 2

        # LLM should recall "4242" in second reply (this is real semantic check)
        assert "4242" in second, f"Multi-turn context missing. Got: {second!r}"


# --------------------------- Compare mode ---------------------------
class TestCompare:
    def test_compare_rejects_less_than_2_models(self, api_client):
        r = api_client.post(
            f"{API}/compare",
            json={"prompt": "ciao", "model_ids": ["gpt-5.2"]},
            timeout=TIMEOUT_SHORT,
        )
        assert r.status_code == 400

    def test_compare_rejects_more_than_4(self, api_client):
        r = api_client.post(
            f"{API}/compare",
            json={"prompt": "ciao",
                  "model_ids": ["gpt-5.2", "claude-sonnet-4.5", "gemini-3-flash",
                                "nano-banana", "gpt-image-1"]},
            timeout=TIMEOUT_SHORT,
        )
        assert r.status_code == 400

    def test_compare_3_models_parallel_all_ok(self, api_client):
        payload = {
            "prompt": "Dimmi in italiano: cosa è un LLM in una frase.",
            "model_ids": ["gpt-5.2", "claude-sonnet-4.5", "gemini-3-flash"],
        }
        t0 = time.time()
        r = api_client.post(f"{API}/compare", json=payload, timeout=TIMEOUT_LLM)
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text
        d = r.json()
        assert "results" in d
        results = d["results"]
        assert len(results) == 3
        for cell in results:
            assert cell["ok"] is True, f"Model {cell.get('model_id')} failed: {cell.get('error')}"
            resp = cell["response"]
            assert "result" in resp
            assert len(resp["result"]) > 5
            assert not resp["result"].startswith("[Errore"), \
                f"Inference error for {cell['model_id']}: {resp['result']}"
            assert resp["routing"]["selected"]["id"] == cell["model_id"]

        # Parallelism smoke check: 3 real LLMs in <3x single latency
        # Not strict; log for insight.
        print(f"[compare] 3-model parallel took {elapsed:.1f}s")


# --------------------------- Image generation (real bytes) ---------------------------
class TestImageGeneration:
    def _decode_data_url(self, data_url: str) -> bytes:
        assert data_url.startswith("data:"), f"Not a data URL: {data_url[:60]}"
        header, _, b64 = data_url.partition(",")
        assert "base64" in header
        return base64.b64decode(b64)

    def test_gpt_image_1_real_bytes(self, api_client):
        """Force gpt-image-1 for image_generation and verify real PNG bytes."""
        r = api_client.post(
            f"{API}/orchestrate",
            json={
                "prompt": "genera immagine di un piccolo logo blu quadrato",
                "force_model_id": "gpt-image-1",
            },
            timeout=TIMEOUT_IMG,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["routing"]["selected"]["id"] == "gpt-image-1"

        result_txt = d.get("result", "")
        if result_txt.startswith("[Errore image gen"):
            pytest.fail(f"GPT-image-1 error: {result_txt}")

        imgs = d.get("images") or []
        assert len(imgs) >= 1, f"No images returned. result={result_txt!r}"
        img = imgs[0]
        assert "data_url" in img
        raw = self._decode_data_url(img["data_url"])
        assert len(raw) > 1024, f"Image too small ({len(raw)} bytes) - probably not real"
        # PNG magic
        assert raw[:8] == b"\x89PNG\r\n\x1a\n", \
            f"Not a PNG (magic={raw[:8]!r})"

    def test_nano_banana_auto_route(self, api_client):
        """Auto-route image_generation intent should pick Nano Banana."""
        r = api_client.post(
            f"{API}/orchestrate",
            json={"prompt": "genera immagine di un gatto minimal"},
            timeout=TIMEOUT_IMG,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["intent"]["intent_id"] == "image_generation"
        assert d["routing"]["selected"]["type"] == "image"
        # Router should prefer nano-banana (score for image_generation: 0.96 > 0.80)
        assert d["routing"]["selected"]["id"] == "nano-banana"

        result_txt = d.get("result", "")
        imgs = d.get("images") or []
        if result_txt.startswith("[Errore image gen"):
            pytest.fail(f"Nano Banana error: {result_txt}")
        assert len(imgs) >= 1, f"Nano Banana returned no images. result={result_txt!r}"
        # Real image bytes
        raw = self._decode_data_url(imgs[0]["data_url"])
        assert len(raw) > 1024


# --------------------------- Regression: existing endpoints ---------------------------
class TestRegression:
    def test_models_endpoint_still_5(self, api_client):
        r = api_client.get(f"{API}/models", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        assert len(r.json()["models"]) == 5

    def test_orchestrate_400_on_empty(self, api_client):
        r = api_client.post(f"{API}/orchestrate", json={"prompt": "", "files": []},
                            timeout=TIMEOUT_SHORT)
        assert r.status_code == 400
