# AI4LIFE — Product Requirements Document

## Original Problem Statement
Enterprise-grade AI orchestrator with intelligent semantic routing across multiple LLMs (GPT-5.2, Claude Sonnet 4.5, Gemini 3 Flash, Nano Banana, GPT-image-1). Router selects the optimal model by cross-referencing user intent with a JSON-driven model registry (capability_score, latency_index, cost_efficiency, best_use_case, weight_matrix). Three-phase pipeline: Ingestion (multimodal — text/PDF/image) → Inference (Context Injection) → Delivery (dual output: Risultato + Insight). Italian language. Clarity-First glassmorphism UI (Midnight Blue / Slate Grey / Electric Blue).

## Architecture
- **Backend (FastAPI + emergentintegrations)**: `/api/models`, `/api/intent`, `/api/route`, `/api/orchestrate`. Config-driven — `config/models_registry.json` is hot-swappable, adding a model requires no code changes.
- **Router**: pure Python, weight-matrix scoring, hard-filters image-gen intent to image-type models.
- **Frontend (React 19 + Tailwind + shadcn)**: Dashboard shell with sidebar (Orchestratore / Model Registry / Archivio). Prompt dock at the bottom (multimodal, force-model dropdown). Response card with Risultato/Insight tabs + Quick-Action bar (Copia, Salva, Rielabora, Condividi).
- **Persistence**: localStorage (`ai4life_archive_v1`). No auth.

## User Personas
- **Enterprise Power User**: wants control + transparency (why THIS model was chosen).
- **Professionista Multimodale**: uploads PDFs/images, expects fast, accurate answers.

## Core Requirements (static)
- Config-driven model registry (no code change to add model).
- Intent detection (rule-based, low latency).
- Semantic routing (weight matrix).
- Multimodal ingestion (PDF via pypdf, images/text via base64 → Gemini FileContent).
- Dual output: Risultato + Insight (technical routing log).
- Quick-Action bar on every output.
- Glassmorphism dark UI, Italian language.

## Implemented (2026-02)
- ✅ 5-model registry (GPT-5.2, Claude Sonnet 4.5, Gemini 3 Flash, Nano Banana, GPT-image-1)
- ✅ Semantic router with weight matrix + intent-to-model scoring
- ✅ Intent detection (9 intents, keyword scorer)
- ✅ Orchestrator with 3-phase pipeline + Context Injection prompt templates
- ✅ PDF/image/text ingestion via base64 + Gemini FileContentWithMimeType
- ✅ Endpoints: `/api/`, `/api/models`, `/api/intent`, `/api/route`, `/api/orchestrate`
- ✅ Dashboard UI with Sidebar / Chat / Model Registry / Archive
- ✅ Prompt Dock (attach, force-model override, ⌘+↵ send)
- ✅ Response Card with Risultato + Insight tabs + Quick-Action bar
- ✅ localStorage archive with clear/remove/copy actions
- ✅ Italian localization, Outfit/Manrope/JetBrains Mono typography, Midnight Blue palette
- ✅ E2E tested: 14/14 backend tests pass, all frontend flows verified

## Backlog (P0 → P2)
- **P0** — Real image generation (Nano Banana + GPT-image-1) — currently returns placeholder
- **P1** — SSE streaming of LLM tokens (playbook recommends stream_message)
- **P1** — Session history persistence (Mongo) beyond localStorage
- **P2** — Chat context (multi-turn same-session memory beyond current session_id)
- **P2** — Cost/latency telemetry dashboard
- **P2** — Custom weight tuning UI (adjust routing_weights from settings)
- **P2** — Voice input (Whisper)
