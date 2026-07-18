# AI4LIFE — Product Requirements Document

## Original Problem Statement
Enterprise-grade AI orchestrator with intelligent semantic routing. Config-driven model registry, weight matrix routing, three-phase pipeline, dual output (Risultato + Insight), Clarity-First glassmorphism UI. Italian.

## Architecture (v1.2.0)
- **Backend (FastAPI + emergentintegrations + MongoDB)**:
  - `/api/models`, `/api/intent`, `/api/route` — router config
  - `/api/orchestrate`, `/api/orchestrate/stream` (SSE) — text + image with weights_override
  - `/api/compare` — 2-4 model parallel comparison
  - `/api/sessions*` — multi-turn session persistence (images inline in Mongo)
  - `/api/transcribe` — Whisper STT with 413 streaming size guard
- **Frontend (React 19 + Tailwind + shadcn)**: Sidebar (nav + sessions) · Chat with SSE stream · Compare · Model Registry · Settings (weights) · Archive · Style Presets · Voice input
- **Persistence**: MongoDB (`ai4life_sessions`, `ai4life_messages` w/ inline images) + localStorage (archive + weights + active styles)

## Personas
- Enterprise Power User (control + transparency)
- Professionista Multimodale (PDF/image ingestion + voice)
- AI Benchmarker (Compare Mode)
- Creativo Visuale (Style Presets + Nano Banana + GPT-image-1)

## Core Requirements (static)
- Config-driven model registry — add model = 1 JSON row
- Weighted intent detection (multi-word phrases score higher)
- Weight-matrix router (with user-tunable weights)
- Multimodal ingestion (PDF/image/text + voice via Whisper)
- Dual output: Risultato + Insight
- Quick-Action bar
- SSE streaming, multi-turn context, compare mode
- Image persistence
- Glassmorphism dark UI, Italian language

## Implemented
### 2026-02 — v1.0.0 (MVP)
- ✅ 5-model registry, weight-matrix router, rule-based intent detection
- ✅ 3-phase orchestrator, Context Injection prompt templates
- ✅ PDF/image/text ingestion
- ✅ Full Dashboard shell + Prompt Dock + Response Card + Quick-Action bar
- ✅ localStorage archive · Real Nano Banana image gen

### 2026-02 — v1.1.0
- ✅ SSE token streaming
- ✅ MongoDB multi-turn session persistence
- ✅ GPT-image-1 real generation
- ✅ Comparison Mode (2-4 models in parallel)

### 2026-02 — v1.2.0
- ✅ **Image persistence in Mongo** — images stored inline in message docs
- ✅ **Style Presets** — 6 chips above PromptDock (Fotorealistico / Flat / Cyberpunk / Watercolor / Isometrico / Luxury Editorial)
- ✅ **Voice input via Whisper** — MediaRecorder → `/api/transcribe` → onTranscribed
- ✅ **Custom weight tuning UI** — Settings view with 4 sliders, normalize+persist, sent as `weights_override` on every request
- ✅ **Intent bug fix** — multi-word phrases (e.g. "genera immagine") now correctly outweigh single-word matches
- ✅ **Fixes**: nested-button warning in SessionsPanel; streaming 413 size guard on Whisper
- ✅ **Tests**: 42/42 total (14 iter1 + 15 iter2 + 13 iter3), all real LLM calls

## Backlog (P2 → P3)
- **P2** GridFS or separate images collection when many turns saved per session
- **P2** Consolidate two Mongo clients into a single shared module
- **P2** MediaRecorder capability sniffing (older Safari)
- **P2** Settings "Reset" confirmation when there are unsaved slider changes
- **P3** Migrate to FastAPI lifespan (deprecated `on_event('shutdown')`)
- **P3** Cost/latency telemetry dashboard
- **P3** Dedupe "[Stile:" prefix when user re-submits
