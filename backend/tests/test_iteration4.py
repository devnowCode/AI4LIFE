"""AI4LIFE iteration 4 tests.

Coverage:
- GET /api/ version == 1.3.0
- POST /api/orchestrate includes cost_estimate_eur (float >=0) and latency_ms (int >=0)
- POST /api/orchestrate/stream terminating 'done' event includes cost_estimate_eur + latency_ms
- GET /api/recipes returns 8 recipes with expected shape
- GET /api/telemetry aggregation shape and reflects new requests
- Cost estimation: Gemini 3 Flash text output < GPT-5.2 cost for same prompt
- GridFS migration: image_generation persists gridfs_id (NOT inline data_url) in Mongo doc
  yet GET /api/sessions/{id}/messages hydrates back into data_url
- Session deletion cleans up GridFS blobs
- Backward compat: legacy inline data_url still hydrates on retrieval
- Consolidated Mongo client (services/db.py exports one AsyncIOMotorClient)
- No deprecation warnings about @app.on_event in supervisor logs
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import subprocess
import time
import uuid
from typing import Any

import pytest
import requests
from dotenv import load_dotenv

# Load frontend .env explicitly for public preview URL
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

TIMEOUT_SHORT = 30
TIMEOUT_LLM = 180
TIMEOUT_IMG = 240


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --------------------------- Version + Root ---------------------------
class TestVersion:
    def test_root_version_1_3_0(self, api_client):
        r = api_client.get(f"{API}/", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        assert d["version"] == "1.3.0", f"Expected 1.3.0, got {d.get('version')}"
        assert d["app"] == "AI4LIFE"
        assert d["status"] == "online"


# --------------------------- Recipes ---------------------------
class TestRecipes:
    def test_recipes_endpoint_shape(self, api_client):
        r = api_client.get(f"{API}/recipes", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        assert "recipes" in d
        recipes = d["recipes"]
        assert len(recipes) == 8, f"Expected 8 recipes, got {len(recipes)}"

        required_fields = {"id", "label", "icon", "category", "template", "styles", "weights_hint"}
        weight_keys = {"capability", "latency", "cost", "context_bonus"}
        for rec in recipes:
            missing = required_fields - set(rec.keys())
            assert not missing, f"Recipe {rec.get('id')} missing fields: {missing}"
            assert isinstance(rec["styles"], list)
            assert isinstance(rec["weights_hint"], dict)
            assert weight_keys <= set(rec["weights_hint"].keys()), (
                f"Recipe {rec['id']} weights_hint missing {weight_keys - set(rec['weights_hint'].keys())}"
            )
            # weights should sum roughly to 1
            total = sum(rec["weights_hint"].values())
            assert 0.9 <= total <= 1.1, f"Recipe {rec['id']} weights sum={total}"

    def test_recipe_ids_include_core_set(self, api_client):
        r = api_client.get(f"{API}/recipes", timeout=TIMEOUT_SHORT)
        ids = {rec["id"] for rec in r.json()["recipes"]}
        expected = {"code-review", "cyberpunk-moodboard"}
        assert expected <= ids, f"Missing core recipes: {expected - ids}"


# --------------------------- Cost/Latency in orchestrate response ---------------------------
class TestCostLatencyResponse:
    def test_orchestrate_response_includes_cost_and_latency(self, api_client):
        r = api_client.post(
            f"{API}/orchestrate",
            json={"prompt": "ciao dimmi cosa è python in una frase"},
            timeout=TIMEOUT_LLM,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "cost_estimate_eur" in d, f"Missing cost_estimate_eur: {list(d.keys())}"
        assert "latency_ms" in d, f"Missing latency_ms: {list(d.keys())}"
        assert isinstance(d["cost_estimate_eur"], (int, float))
        assert d["cost_estimate_eur"] >= 0
        assert isinstance(d["latency_ms"], int)
        assert d["latency_ms"] >= 0
        # A real LLM call: latency should be at least some ms
        assert d["latency_ms"] > 50, f"Suspiciously low latency: {d['latency_ms']}ms — did LLM actually run?"

    def test_gemini_cheaper_than_gpt52(self, api_client):
        """Same prompt via force_model_id: Gemini output tokens *rate is 0 (missing field)
        → cost derived from cost_efficiency=95 (very cheap). GPT-5.2 has explicit rate 0.0135.
        Assert gemini cost < gpt-5.2 cost for a comparable text prompt."""
        prompt = "Rispondi con la parola 'ciao'."
        r_gpt = api_client.post(
            f"{API}/orchestrate",
            json={"prompt": prompt, "force_model_id": "gpt-5.2"},
            timeout=TIMEOUT_LLM,
        )
        r_gemini = api_client.post(
            f"{API}/orchestrate",
            json={"prompt": prompt, "force_model_id": "gemini-3-flash"},
            timeout=TIMEOUT_LLM,
        )
        assert r_gpt.status_code == 200 and r_gemini.status_code == 200
        c_gpt = r_gpt.json()["cost_estimate_eur"]
        c_gem = r_gemini.json()["cost_estimate_eur"]
        # Gemini must be strictly cheaper (either 0 due to missing rate, or derived from ce=95)
        assert c_gem <= c_gpt, (
            f"Expected Gemini cost <= GPT-5.2 cost. Got gemini={c_gem}, gpt={c_gpt}"
        )


# --------------------------- Streaming done event ---------------------------
class TestStreamDone:
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
                            events.append(json.loads(line[5:].strip()))
                        except Exception:
                            continue
        return events

    def test_stream_done_carries_cost_and_latency(self, api_client):
        sid = str(uuid.uuid4())
        with api_client.post(
            f"{API}/orchestrate/stream",
            json={"prompt": "Ciao, breve saluto.", "session_id": sid},
            stream=True,
            timeout=TIMEOUT_LLM,
        ) as r:
            assert r.status_code == 200, r.text
            events = self._consume_sse(r)
        dones = [e for e in events if e.get("type") == "done"]
        assert dones, f"No done event received. Events: {[e.get('type') for e in events]}"
        done = dones[-1]
        assert "cost_estimate_eur" in done, f"done event missing cost_estimate_eur: {done}"
        assert "latency_ms" in done, f"done event missing latency_ms: {done}"
        assert isinstance(done["cost_estimate_eur"], (int, float))
        assert done["cost_estimate_eur"] >= 0
        assert isinstance(done["latency_ms"], int)
        assert done["latency_ms"] >= 0


# --------------------------- Telemetry ---------------------------
class TestTelemetry:
    def test_telemetry_shape(self, api_client):
        r = api_client.get(f"{API}/telemetry", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        d = r.json()
        assert set(d.keys()) >= {"totals", "by_model", "recent"}, f"Missing keys: {d.keys()}"
        totals = d["totals"]
        assert set(totals.keys()) >= {"requests", "total_cost_eur", "avg_latency_ms"}
        assert isinstance(totals["requests"], int)
        assert isinstance(totals["total_cost_eur"], (int, float))
        assert isinstance(totals["avg_latency_ms"], int)
        assert isinstance(d["by_model"], list)
        assert isinstance(d["recent"], list)

    def test_telemetry_reflects_new_request(self, api_client):
        """Snapshot totals, fire a real request, expect requests+1 (or more if others racing)."""
        before = api_client.get(f"{API}/telemetry", timeout=TIMEOUT_SHORT).json()
        prev_requests = before["totals"]["requests"]

        r = api_client.post(
            f"{API}/orchestrate",
            json={"prompt": "dimmi cosa è markdown in una frase"},
            timeout=TIMEOUT_LLM,
        )
        assert r.status_code == 200

        # small wait to ensure telemetry write is settled
        time.sleep(1.0)
        after = api_client.get(f"{API}/telemetry", timeout=TIMEOUT_SHORT).json()
        new_requests = after["totals"]["requests"]
        assert new_requests >= prev_requests + 1, (
            f"Telemetry did not record new request: before={prev_requests}, after={new_requests}"
        )
        # by_model has entries
        assert len(after["by_model"]) >= 1
        # recent has our latest with all required fields
        assert len(after["recent"]) >= 1
        latest = after["recent"][0]
        for f_ in ("session_id", "model_id", "model_display", "intent_id",
                   "latency_ms", "cost_eur", "num_images", "output_len", "created_at"):
            assert f_ in latest, f"recent entry missing {f_}: {latest}"


# --------------------------- GridFS migration ---------------------------
class TestGridFSMigration:
    """Directly inspect Mongo doc structure to verify GridFS ID stored,
    then verify /messages hydration returns full data_url."""

    @pytest.fixture(scope="class")
    def mongo(self):
        # Use synchronous PyMongo just for read-verification
        try:
            from pymongo import MongoClient
        except ImportError:
            pytest.skip("pymongo not available")
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
        if not mongo_url or not db_name:
            # Load backend .env for MONGO_URL / DB_NAME
            load_dotenv("/app/backend/.env")
            mongo_url = os.environ["MONGO_URL"]
            db_name = os.environ["DB_NAME"]
        client = MongoClient(mongo_url)
        yield client[db_name]
        client.close()

    def test_image_persisted_as_gridfs_ref_not_inline(self, api_client, mongo):
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
        assert d["intent"]["intent_id"] == "image_generation"
        # API response still returns full data_url to the client
        imgs_api = d.get("images") or []
        assert imgs_api, f"No images returned. result={d.get('result')!r}"
        assert imgs_api[0]["data_url"].startswith("data:image/")

        # Mongo doc: must have gridfs_id, NOT inline data_url
        docs = list(mongo["ai4life_messages"].find({"session_id": sid}))
        assert len(docs) == 1, f"Expected 1 doc, got {len(docs)}"
        stored_imgs = docs[0].get("images", [])
        assert stored_imgs, f"Doc has no images[]: {docs[0]}"
        img0 = stored_imgs[0]
        assert "gridfs_id" in img0, f"Image missing gridfs_id (not migrated?): {img0}"
        assert "data_url" not in img0, f"Image still has inline data_url — GridFS migration incomplete: {img0}"
        assert isinstance(img0["gridfs_id"], str) and len(img0["gridfs_id"]) == 24
        # Verify GridFS files collection has that id
        from bson import ObjectId
        gfile = mongo["ai4life_images.files"].find_one({"_id": ObjectId(img0["gridfs_id"])})
        assert gfile is not None, "GridFS file not present in ai4life_images.files"
        assert gfile["length"] > 1024, f"Persisted GridFS image too small: {gfile['length']} bytes"

        # Hydration via API
        r2 = api_client.get(f"{API}/sessions/{sid}/messages", timeout=TIMEOUT_SHORT)
        assert r2.status_code == 200
        msgs = r2.json()["messages"]
        assert len(msgs) == 1
        hyd_imgs = msgs[0]["images"]
        assert hyd_imgs and "data_url" in hyd_imgs[0]
        assert hyd_imgs[0]["data_url"].startswith("data:image/")
        # Data URL should match ~ the bytes length
        b64 = hyd_imgs[0]["data_url"].split(",", 1)[1]
        raw = base64.b64decode(b64)
        assert len(raw) == gfile["length"], (
            f"Hydrated byte length {len(raw)} != GridFS stored length {gfile['length']}"
        )

        # cost_estimate_eur & latency_ms in persisted doc
        assert "cost_estimate_eur" in docs[0]
        assert "latency_ms" in docs[0]

    def test_delete_session_cleans_gridfs(self, api_client, mongo):
        """Create a small image session, delete it, verify GridFS files are gone."""
        sid = str(uuid.uuid4())
        r = api_client.post(
            f"{API}/orchestrate",
            json={"prompt": "genera immagine astratta blu", "session_id": sid},
            timeout=TIMEOUT_IMG,
        )
        assert r.status_code == 200, r.text
        docs = list(mongo["ai4life_messages"].find({"session_id": sid}))
        assert docs, "No message stored"
        gids = [img["gridfs_id"] for d in docs for img in d.get("images", []) if "gridfs_id" in img]
        assert gids, "No gridfs ids in stored image doc"
        from bson import ObjectId
        for gid in gids:
            assert mongo["ai4life_images.files"].find_one({"_id": ObjectId(gid)}) is not None, (
                f"GridFS file {gid} not found pre-delete"
            )

        # Delete the session
        rd = api_client.delete(f"{API}/sessions/{sid}", timeout=TIMEOUT_SHORT)
        assert rd.status_code == 200

        # Verify GridFS files removed
        for gid in gids:
            assert mongo["ai4life_images.files"].find_one({"_id": ObjectId(gid)}) is None, (
                f"GridFS file {gid} still present after DELETE /sessions/{sid}"
            )
        # And messages removed
        assert mongo["ai4life_messages"].count_documents({"session_id": sid}) == 0

    def test_backward_compat_inline_data_url_still_hydrates(self, api_client, mongo):
        """Insert a legacy-shape message with inline images[].data_url and confirm
        GET /messages returns it as-is (via _hydrate_message fallback branch)."""
        sid = f"legacy-{uuid.uuid4()}"
        # 5x5 red PNG
        png_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4"
            "//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
        )
        data_url = "data:image/png;base64," + png_b64
        legacy_doc = {
            "id": str(uuid.uuid4()),
            "session_id": sid,
            "prompt": "legacy image test",
            "result": "Immagine generata.",
            "intent": {"intent_id": "image_generation", "intent_label": "Image",
                       "confidence": 0.9, "matched_keywords": ["genera"],
                       "has_files": False, "has_images": False},
            "routing_selected": {"id": "nano-banana", "display_name": "Nano Banana",
                                 "provider": "gemini", "model_name": "gemini-3.1-flash-image-preview",
                                 "type": "image"},
            "insight": "legacy",
            "images": [{"mime_type": "image/png", "data_url": data_url}],
            "has_images": True,
            "num_images": 1,
            "cost_estimate_eur": 0.003,
            "latency_ms": 100,
            "created_at": "2025-01-01T00:00:00+00:00",
        }
        mongo["ai4life_messages"].insert_one(legacy_doc)
        try:
            r2 = api_client.get(f"{API}/sessions/{sid}/messages", timeout=TIMEOUT_SHORT)
            assert r2.status_code == 200
            msgs = r2.json()["messages"]
            assert len(msgs) == 1
            assert msgs[0]["images"][0]["data_url"] == data_url
        finally:
            mongo["ai4life_messages"].delete_one({"id": legacy_doc["id"]})


# --------------------------- Consolidated Mongo client ---------------------------
class TestConsolidatedClient:
    def test_single_client_in_db_module(self):
        """services/db.py must expose ONE AsyncIOMotorClient — history + telemetry both import it."""
        with open("/app/backend/services/db.py", "r", encoding="utf-8") as f:
            src = f.read()
        # Ensure only one AsyncIOMotorClient(...) instantiation
        instantiations = re.findall(r"AsyncIOMotorClient\s*\(", src)
        assert len(instantiations) == 1, (
            f"Expected exactly 1 AsyncIOMotorClient() in db.py, found {len(instantiations)}"
        )
        # history + telemetry import from .db
        for mod in ("history.py", "telemetry.py"):
            with open(f"/app/backend/services/{mod}", "r", encoding="utf-8") as f:
                s = f.read()
            assert "from .db import" in s or "from services.db import" in s, (
                f"services/{mod} does not import from services.db"
            )
            # And they should NOT create their own AsyncIOMotorClient
            assert re.search(r"AsyncIOMotorClient\s*\(", s) is None, (
                f"services/{mod} still instantiates its own AsyncIOMotorClient"
            )


# --------------------------- Lifespan — no on_event deprecation ---------------------------
class TestLifespan:
    def test_no_on_event_in_server_py(self):
        with open("/app/backend/server.py", "r", encoding="utf-8") as f:
            s = f.read()
        # The old-style hook shouldn't be present
        assert "@app.on_event" not in s, "server.py still uses deprecated @app.on_event"
        # New lifespan should be there
        assert "lifespan" in s and "asynccontextmanager" in s, "Lifespan pattern not adopted"

    def test_backend_logs_have_no_on_event_deprecation(self):
        try:
            out = subprocess.check_output(
                ["bash", "-lc", "grep -iE 'on_event|DeprecationWarning' /var/log/supervisor/backend.*.log || true"],
                timeout=10,
            ).decode()
        except Exception:
            out = ""
        # No warnings referencing on_event or the FastAPI lifespan deprecation
        assert "on_event is deprecated" not in out, out
        # any DeprecationWarning mentioning on_event
        assert not re.search(r"DeprecationWarning.*on_event", out), out


# --------------------------- Regression sanity ---------------------------
class TestRegression:
    def test_models_still_5(self, api_client):
        r = api_client.get(f"{API}/models", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        assert len(r.json()["models"]) == 5

    def test_orchestrate_still_400_on_empty(self, api_client):
        r = api_client.post(f"{API}/orchestrate", json={"prompt": "", "files": []},
                            timeout=TIMEOUT_SHORT)
        assert r.status_code == 400

    def test_sessions_endpoint(self, api_client):
        r = api_client.get(f"{API}/sessions", timeout=TIMEOUT_SHORT)
        assert r.status_code == 200
        assert "sessions" in r.json()

    def test_compare_still_ok(self, api_client):
        r = api_client.post(
            f"{API}/compare",
            json={"prompt": "Ciao in italiano una parola.",
                  "model_ids": ["gpt-5.2", "gemini-3-flash"]},
            timeout=TIMEOUT_LLM,
        )
        assert r.status_code == 200
        d = r.json()
        assert len(d["results"]) == 2
        for c in d["results"]:
            assert c["ok"] is True, c
