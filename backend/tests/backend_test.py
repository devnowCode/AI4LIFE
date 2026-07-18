"""AI4LIFE backend integration tests.
Covers: /api/, /api/models, /api/intent, /api/route, /api/orchestrate.
Uses REACT_APP_BACKEND_URL for hitting the preview endpoint."""
import base64
import io
import os
import pytest
import requests

# Load frontend .env explicitly for the public preview URL used in tests
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
TIMEOUT = 120  # LLM calls can take ~30-60s


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --------------------------- /api/ ---------------------------
class TestRoot:
    def test_root_returns_app_info(self, api):
        r = api.get(f"{BASE_URL}/api/", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("app") == "AI4LIFE"
        assert d.get("status") == "online"
        assert "version" in d


# --------------------------- /api/models ---------------------------
class TestModels:
    def test_models_registry_returns_5_models(self, api):
        r = api.get(f"{BASE_URL}/api/models", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "models" in d
        assert len(d["models"]) == 5
        ids = {m["id"] for m in d["models"]}
        assert ids == {"gpt-5.2", "claude-sonnet-4.5", "gemini-3-flash", "nano-banana", "gpt-image-1"}
        # routing_weights
        assert "routing_weights" in d
        rw = d["routing_weights"]
        for k in ("capability", "latency", "cost", "context_bonus"):
            assert k in rw
            assert isinstance(rw[k], (int, float))


# --------------------------- /api/intent ---------------------------
class TestIntent:
    def test_intent_code_python(self, api):
        r = api.post(f"{BASE_URL}/api/intent", json={"prompt": "scrivi codice python"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["intent_id"] == "code", f"Expected code intent, got {d}"
        assert "codice" in d["matched_keywords"] or "python" in d["matched_keywords"]

    def test_intent_summarization(self, api):
        r = api.post(f"{BASE_URL}/api/intent", json={"prompt": "riassumi questo testo"}, timeout=30)
        assert r.status_code == 200
        assert r.json()["intent_id"] == "summarization"

    def test_intent_image_generation(self, api):
        r = api.post(f"{BASE_URL}/api/intent", json={"prompt": "genera immagine di un tramonto"}, timeout=30)
        assert r.status_code == 200
        assert r.json()["intent_id"] == "image_generation"

    def test_intent_quick_qa_fallback(self, api):
        r = api.post(f"{BASE_URL}/api/intent", json={"prompt": "ciao come stai oggi"}, timeout=30)
        assert r.status_code == 200
        # Should fallback to quick_qa when nothing matches
        assert r.json()["intent_id"] in ("quick_qa", "creative")  # tolerant


# --------------------------- /api/route ---------------------------
class TestRoute:
    def test_route_returns_intent_and_selected(self, api):
        r = api.post(f"{BASE_URL}/api/route", json={"prompt": "scrivi codice python"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "intent" in d and "routing" in d
        assert d["intent"]["intent_id"] == "code"
        sel = d["routing"]["selected"]
        assert sel["id"] in ("gpt-5.2", "claude-sonnet-4.5")  # code -> GPT-5.2 top
        assert "score" in sel
        assert isinstance(d["routing"]["candidates"], list)
        assert len(d["routing"]["candidates"]) >= 1

    def test_route_image_generation_selects_image_model(self, api):
        r = api.post(f"{BASE_URL}/api/route", json={"prompt": "genera immagine di un gatto"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["intent"]["intent_id"] == "image_generation"
        assert d["routing"]["selected"]["type"] == "image"
        assert d["routing"]["selected"]["id"] in ("nano-banana", "gpt-image-1")

    def test_route_multimodal_with_files_selects_gemini(self, api):
        r = api.post(f"{BASE_URL}/api/route",
                     json={"prompt": "analizza questo documento", "has_files": True}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        # Gemini should win because it supports files natively
        assert d["routing"]["selected"]["id"] == "gemini-3-flash"


# --------------------------- /api/orchestrate ---------------------------
class TestOrchestrate:
    def test_orchestrate_rejects_empty(self, api):
        r = api.post(f"{BASE_URL}/api/orchestrate", json={"prompt": "", "files": []}, timeout=30)
        assert r.status_code == 400

    def test_orchestrate_simple_prompt_real_llm(self, api):
        """Real LLM call - must produce non-trivial Italian response."""
        r = api.post(
            f"{BASE_URL}/api/orchestrate",
            json={"prompt": "ciao dimmi in italiano cosa è python in una frase"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "result" in d
        result = d["result"]
        assert isinstance(result, str)
        assert len(result) > 20, f"Result too short: {result!r}"
        # Should not be an error message
        assert not result.startswith("[Errore inference"), f"LLM error: {result}"
        # Routing metadata present
        assert "routing" in d and "selected" in d["routing"]
        assert "intent" in d
        assert "insight" in d and "Routing Decision" in d["insight"]

    def test_orchestrate_force_claude(self, api):
        r = api.post(
            f"{BASE_URL}/api/orchestrate",
            json={
                "prompt": "dammi un saluto breve in italiano",
                "force_model_id": "claude-sonnet-4.5",
            },
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["routing"]["selected"]["id"] == "claude-sonnet-4.5"
        assert d["routing"]["selected"]["provider"] == "anthropic"
        # Real LLM call
        assert len(d["result"]) > 10
        assert not d["result"].startswith("[Errore inference"), f"Claude error: {d['result']}"

    def test_orchestrate_image_generation_placeholder(self, api):
        r = api.post(
            f"{BASE_URL}/api/orchestrate",
            json={"prompt": "genera immagine di un tramonto sul mare"},
            timeout=30,
        )
        assert r.status_code == 200
        d = r.json()
        # Routed to an image-type model
        assert d["routing"]["selected"]["type"] == "image"
        assert d["routing"]["selected"]["id"] in ("nano-banana", "gpt-image-1")
        # Graceful placeholder
        assert "Modello selezionato" in d["result"]
        assert d["intent"]["intent_id"] == "image_generation"

    def test_orchestrate_pdf_routes_to_gemini(self, api):
        """Attach a tiny real PDF and confirm routing goes to Gemini."""
        pdf_path = "/app/test_fixtures/sample.pdf"
        if not os.path.exists(pdf_path):
            # Generate minimal valid PDF via reportlab-free approach: use pypdf
            from pypdf import PdfWriter
            w = PdfWriter()
            w.add_blank_page(width=200, height=200)
            with open(pdf_path, "wb") as f:
                w.write(f)
        with open(pdf_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        r = api.post(
            f"{BASE_URL}/api/orchestrate",
            json={
                "prompt": "Riassumi questo documento",
                "files": [{"name": "sample.pdf", "content_b64": b64, "mime": "application/pdf"}],
            },
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        # Gemini should be selected because supports_files=true and files attached
        assert d["routing"]["selected"]["id"] == "gemini-3-flash", f"Expected gemini, got {d['routing']['selected']}"
        # LLM produced a response (may be short since PDF is blank)
        assert "result" in d
        assert not d["result"].startswith("[Errore inference"), f"Gemini error: {d['result']}"
