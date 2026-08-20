# AI4LIFE — The Intelligent Orchestrator

> Enterprise-grade AI orchestrator. Un input, il modello ottimale, zero attriti.

AI4LIFE è un'applicazione full-stack che analizza semanticamente ogni richiesta e la instrada dinamicamente al modello AI più adatto (GPT-5.2, Claude Sonnet 4.5, Gemini 3 Flash, Nano Banana, GPT-image-1) tramite una matrice di pesi configurabile. L'utente vede sia il **Risultato** che l'**Insight tecnico** del routing, con badge di costo e latenza in tempo reale.

**Live demo**: <https://clarity-first-57.emergent.host>

---

## ✨ Feature principali

| Categoria | Feature |
|---|---|
| 🧠 **Orchestrazione** | Intent recognition, semantic router (weight matrix), model registry JSON hot-swappable |
| ⚡ **Streaming** | SSE token streaming, multi-turn context injection, fallback graceful |
| 🖼️ **Multimodale** | Ingestion PDF · Immagini · Testo · Voce (Whisper STT); image generation con Nano Banana + GPT-image-1 |
| 🔬 **Compare Mode** | Stessa query su 2-4 modelli in parallelo, side-by-side |
| 💰 **FinOps** | Cost badge ⚡€X.XXXX per risposta, Telemetry dashboard live (KPI + distribuzione + timeline) |
| 🎨 **Style Presets** | 6 stili applicabili (Fotorealistico, Cyberpunk, Watercolor, Luxury…) |
| 📖 **Prompt Recipes** | 8 template one-click (Code Review, Analizza contratto, Moodboard cyberpunk…) con weights hint |
| ⚙️ **Custom Weights** | Slider UI per personalizzare capability/latency/cost/context bonus |
| 💾 **Persistenza** | MongoDB sessions + GridFS per immagini, localStorage per preferenze |
| 📱 **Mobile-ready** | Layout responsive con toggle compatto per scorciatoie |

## 🏗️ Architettura

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React 19 + Tailwind + shadcn)                │
│  Dashboard · Sidebar (nav+sessions) · Chat · Compare   │
│  Model Registry · Weights · Telemetry · Archive         │
└──────────────────┬──────────────────────────────────────┘
                   │  REST + SSE  (/api/*)
┌──────────────────▼──────────────────────────────────────┐
│  Backend (FastAPI, lifespan-managed)                    │
│  ┌────────────┐ ┌──────────┐ ┌─────────┐ ┌───────────┐ │
│  │  Intent    │→│  Router  │→│ Orchestr.│→│  Delivery │ │
│  │ Recognition│ │ (matrix) │ │(LlmChat) │ │ (SSE/JSON)│ │
│  └────────────┘ └──────────┘ └─────────┘ └───────────┘ │
│         │             │             │           │       │
│  models_registry.json (external, hot-swap)              │
│  recipes.json (recipe library)                          │
└──────────────────┬───────────────┬──────────────────────┘
                   │               │
       ┌───────────▼───┐  ┌────────▼─────────┐
       │   MongoDB     │  │  emergentintegr. │
       │  sessions +   │  │  Universal Key   │
       │  messages +   │  │  → OpenAI /      │
       │  telemetry +  │  │  Anthropic /     │
       │  GridFS       │  │  Gemini / Whisper│
       └───────────────┘  └──────────────────┘
```

## 📦 Stack

- **Frontend**: React 19, React Router v6, Tailwind CSS, shadcn/ui, lucide-react, sonner (toasts), axios
- **Backend**: FastAPI, Motor (async MongoDB), `emergentintegrations` (single SDK per OpenAI / Anthropic / Gemini via Emergent Universal Key), pypdf
- **Database**: MongoDB + GridFS bucket (`ai4life_images`)
- **Deployment**: Kubernetes-ready (supervisord), Emergent-hosted

## 🚀 Quick start

### Prerequisiti
- Python 3.11+
- Node 18+ / Yarn
- MongoDB in esecuzione (locale su `mongodb://localhost:27017`)
- Chiave `EMERGENT_LLM_KEY` (fornita dalla piattaforma Emergent)

### Backend

```bash
cd backend
pip install -r requirements.txt

# .env
cat > .env <<EOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
CORS_ORIGINS=*
EMERGENT_LLM_KEY=sk-emergent-XXXXXXXXXXXX
EOF

uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

```bash
cd frontend
yarn install

# .env
cat > .env <<EOF
REACT_APP_BACKEND_URL=http://localhost:8001
EOF

yarn start
```

Apri <http://localhost:3000>.

## 🧩 Aggiungere un nuovo modello (zero codice)

Basta aggiungere un record a `backend/config/models_registry.json`:

```json
{
  "id": "my-new-model",
  "display_name": "My New Model",
  "provider": "openai",
  "model_name": "gpt-6-mini",
  "type": "text",
  "capability_score": 90,
  "latency_index": 88,
  "cost_efficiency": 80,
  "cost_per_1k_output_tokens_eur": 0.005,
  "context_window": 128000,
  "best_use_case": ["reasoning", "code"],
  "tagline": "Il tuo nuovo modello",
  "weight_matrix": {
    "reasoning": 0.94, "code": 0.95, "creative": 0.80,
    "summarization": 0.90, "translation": 0.88,
    "multimodal": 0.70, "quick_qa": 0.85, "image_generation": 0.0
  }
}
```

Il router lo scopre automaticamente al prossimo restart.

## 📚 API principali

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/api/` | GET | Health check + versione |
| `/api/models` | GET | Model registry |
| `/api/recipes` | GET | Prompt Recipe library |
| `/api/intent` | POST | Solo intent detection |
| `/api/route` | POST | Intent + selezione modello (dry-run) |
| `/api/orchestrate` | POST | Pipeline completa (non-streaming) |
| `/api/orchestrate/stream` | POST | Pipeline completa SSE (`meta` → `token*` → `done`) |
| `/api/compare` | POST | 2-4 modelli in parallelo |
| `/api/sessions` | GET | Lista sessioni multi-turno |
| `/api/sessions/{id}/messages` | GET | Storico sessione (immagini hydrated da GridFS) |
| `/api/sessions/{id}` | DELETE | Elimina sessione + GridFS blobs |
| `/api/telemetry` | GET | Aggregazione cost/latency per modello |
| `/api/transcribe` | POST | Whisper STT (multipart audio) |

## 🧪 Testing

```bash
# Backend regression suite (60 test, ~30s)
cd backend
pytest tests/ -v

# Frontend lint
cd frontend
yarn lint
```

## 📊 Struttura del progetto

```
/app
├── backend/
│   ├── server.py              # FastAPI app + lifespan + all endpoints
│   ├── config/
│   │   ├── models_registry.json    # 5 modelli con pricing + weight matrix
│   │   ├── recipes.json            # 8 Prompt Recipes
│   │   └── config.json             # Intent keywords + system message
│   ├── services/
│   │   ├── db.py              # Shared Mongo client + GridFS bucket
│   │   ├── intent.py          # Rule-based weighted intent detection
│   │   ├── router.py          # Semantic router (weight matrix)
│   │   ├── parser.py          # PDF/image/text ingestion
│   │   ├── orchestrator.py    # 3-phase pipeline (Ingest→Inference→Delivery)
│   │   ├── history.py         # Session persistence + GridFS hydration
│   │   └── telemetry.py       # Cost estimation + aggregation
│   └── tests/                 # 60 pytest tests (iter1-4)
└── frontend/
    ├── src/
    │   ├── App.js
    │   ├── pages/Dashboard.jsx        # Main app shell
    │   ├── components/
    │   │   ├── Sidebar.jsx            # Nav + sessions
    │   │   ├── PromptDock.jsx         # Multimodal input + voice + compare
    │   │   ├── ResponseCard.jsx       # Risultato/Insight tabs + Quick Actions
    │   │   ├── CompareCard.jsx        # Side-by-side compare view
    │   │   ├── RouterPill.jsx         # Model + cost badge
    │   │   ├── CostBadge.jsx          # ⚡€X.XXXX FinOps badge
    │   │   ├── RecipesStrip.jsx       # 8 prompt recipes
    │   │   ├── StylePresets.jsx       # 6 style presets
    │   │   ├── VoiceButton.jsx        # Whisper STT
    │   │   ├── ModelRegistry.jsx      # Table view
    │   │   ├── Settings.jsx           # Weight sliders
    │   │   ├── Telemetry.jsx          # KPI + charts + timeline
    │   │   ├── Archive.jsx            # localStorage
    │   │   └── SessionsPanel.jsx      # Session list in sidebar
    │   └── lib/
    │       ├── api.js                 # axios + SSE streaming client
    │       ├── settings.js            # localStorage preferences
    │       └── storage.js             # Archive persistence
    └── public/
```

## 🎨 Design system

- **Aesthetic**: Clarity-First glassmorphism
- **Palette**: Midnight Blue (`#030712`) · Slate Grey (`#1e293b`) · Electric Blue (`#38bdf8`)
- **Typography**: Outfit (display) · Manrope (body) · JetBrains Mono (code/insight)
- **Layout**: Sidebar 256px desktop · Mobile nav bar · Sticky bottom dock con gradient blur

## 🗺️ Roadmap

- [ ] Cost Budget Sentinel (progress bar in sidebar, warning ≥80%)
- [ ] Recipe editor UI (utente crea/modifica ricette)
- [ ] Historical charts cost/latency
- [ ] Export sessione come Markdown/PDF
- [ ] Model comparison scorecard con winner-per-intent

## 📝 Licenza

MIT © 2026 — AI4LIFE
