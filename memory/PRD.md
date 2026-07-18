# AI4LIFE — Product Requirements Document

## Original Problem Statement
Enterprise-grade AI orchestrator with intelligent semantic routing across multiple LLMs. Router selects optimal model by cross-referencing user intent with a JSON-driven model registry (capability_score, latency_index, cost_efficiency, weight_matrix). Three-phase pipeline: Ingestion → Inference → Delivery (Risultato + Insight). Italian language. Clarity-First glassmorphism UI (Midnight Blue / Slate Grey / Electric Blue).

## Architecture (v1.1.0)
- **Backend (FastAPI + emergentintegrations)**:
  - `/api/models`, `/api/intent`, `/api/route` — config
  - `/api/orchestrate` — non-streaming
  - `/api/orchestrate/stream` — SSE streaming (meta → token* → done)
  - `/api/compare` — parallel N-model comparison (2-4 models)
  - `/api/sessions*` — Mongo-backed multi-turn session persistence
- **Config-driven**: `config/models_registry.json` hot-swappable
- **Frontend (React 19 + Tailwind + shadcn)**: Sidebar with Sessions panel · Chat with live streaming · Compare mode · Model Registry · Archive (localStorage)
- **Persistence**: MongoDB (`ai4life_sessions`, `ai4life_messages`) + localStorage archive

## User Personas
- **Enterprise Power User** — wants control + transparency (routing rationale)
- **Professionista Multimodale** — uploads PDFs/images, wants fast accurate answers
- **AI Benchmarker** — uses Compare Mode to evaluate model quality side-by-side

## Core Requirements (static)
- Config-driven model registry
- Intent detection (rule-based)
- Semantic routing (weight matrix)
- Multimodal ingestion (PDF/image/text)
- Dual output: Risultato + Insight
- Quick-Action bar (Copy/Save/Rework/Share)
- SSE streaming, multi-turn context, compare mode
- Glassmorphism dark UI, Italian language

## Implemented
### 2026-02 — v1.0.0 (MVP)
- ✅ 5-model registry + weight-matrix router + intent detection
- ✅ 3-phase orchestrator with Context Injection prompt templates
- ✅ PDF/image/text ingestion via base64
- ✅ Dashboard shell (Sidebar / Chat / Model Registry / Archive)
- ✅ Prompt Dock (attach, force-model, ⌘+↵)
- ✅ Response Card with Risultato/Insight tabs + Quick-Action bar
- ✅ localStorage archive
- ✅ Real Nano Banana image generation

### 2026-02 — v1.1.0
- ✅ **SSE token streaming** (`/api/orchestrate/stream` with fetch+ReadableStream client)
- ✅ **Multi-turn session persistence** (MongoDB; last 4 turns injected as context)
- ✅ **GPT-image-1 real generation** via `OpenAIImageGeneration.generate_images()`
- ✅ **Comparison Mode** — same query → 2-4 models in parallel, side-by-side view
- ✅ Sessions Panel in sidebar (list/load/delete)
- ✅ Compact RouterPill variant for narrow compare cells
- ✅ **Tests**: 29/29 pass (14 v1.0.0 + 15 v1.1.0 including real Gemini/Claude/GPT/image LLM calls)

## Backlog (P0 → P2)
- **P2** Voice input (Whisper STT)
- **P2** Cost/latency telemetry dashboard
- **P2** Custom weight tuning UI (adjust routing_weights from settings)
- **P2** Visual style presets (fotorealistico, illustration, cyberpunk…) as chips above prompt dock
- **P2** Persist generated images in Mongo (currently only in-memory during session)
- **P3** Migrate to FastAPI lifespan context (deprecated `on_event('shutdown')`)
- **P3** Consolidate two Mongo clients into a single shared module
