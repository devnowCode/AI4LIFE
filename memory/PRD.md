# AI4LIFE — Product Requirements Document

## Original Problem Statement
Enterprise-grade AI orchestrator with intelligent semantic routing. Config-driven model registry, weight matrix routing, three-phase pipeline, dual output (Risultato + Insight), Clarity-First glassmorphism UI. Italian language.

## Architecture (v1.3.0)
- **Backend (FastAPI + emergentintegrations + MongoDB + GridFS)**:
  - Config: `/api/models`, `/api/intent`, `/api/route`, `/api/recipes`
  - Orchestration: `/api/orchestrate` (+ cost/latency), `/api/orchestrate/stream` (SSE), `/api/compare`
  - Sessions (Mongo + GridFS): `/api/sessions*`
  - FinOps: `/api/telemetry`
  - Voice: `/api/transcribe` (Whisper)
- **Single shared `services/db.py`** — one AsyncIOMotorClient, GridFS bucket, lifespan-managed close
- **FastAPI lifespan** (asynccontextmanager, no deprecated on_event)
- **Frontend (React 19 + Tailwind + shadcn)**: Sidebar (nav + sessions) · Chat with SSE stream · Compare · Model Registry · Weights · Telemetry · Archive · Recipes · Style Presets · Voice input · Cost badges

## Personas
- Enterprise Power User (control + transparency)
- Professionista Multimodale (PDF/image ingestion + voice)
- AI Benchmarker (Compare Mode)
- Creativo Visuale (Style Presets + image gen)
- **FinOps Manager** (Telemetry dashboard)
- **Knowledge Worker** (Prompt Recipes)

## Core Requirements (static)
- Config-driven model registry (with explicit pricing per model)
- Weighted intent detection (multi-word phrases score higher)
- Weight-matrix router (user-tunable + per-recipe hints)
- Multimodal ingestion (PDF/image/text + voice via Whisper)
- Dual output: Risultato + Insight + Cost badge
- SSE streaming, multi-turn context, compare mode
- Image persistence via GridFS
- Cost/latency telemetry (FinOps-ready)
- Prompt Recipe library
- Glassmorphism dark UI, Italian language

## Implemented
### v1.0.0 (2026-02) — MVP
- ✅ 5-model registry, weight-matrix router, rule-based intent detection
- ✅ 3-phase orchestrator, Context Injection prompt templates
- ✅ PDF/image/text ingestion, Dashboard + Prompt Dock + Response Card
- ✅ localStorage archive · Nano Banana image gen

### v1.1.0 — Streaming + Sessions + Compare
- ✅ SSE token streaming, Mongo multi-turn persistence
- ✅ GPT-image-1 real generation
- ✅ Compare Mode (2-4 models in parallel)

### v1.2.0 — Voice + Styles + Custom Weights
- ✅ Image persistence in Mongo (initially inline)
- ✅ 6 Style Presets chips
- ✅ Voice input via Whisper STT
- ✅ Custom weight tuning UI (4 sliders, localStorage, `weights_override`)
- ✅ Intent scoring bug fix (multi-word phrase weighting)

### v1.3.0 — FinOps + Productivity
- ✅ **Cost estimate badge** (⚡€X.XXXX + latency) in RouterPill / Response Card / Compare Card
- ✅ **Telemetry dashboard** with KPI cards, per-model distribution, recent requests (auto-refresh 5s)
- ✅ **Prompt Recipe library** — 8 curated recipes (Analizza contratto, Riassumi paper, Moodboard cyberpunk, Code Review, Traduzione professionale, Brainstorm creativo, Product shot luxury, Verbale meeting). Each recipe applies template + styles + weights_hint
- ✅ **GridFS migration** for image storage (lean message docs, backward-compat hydration)
- ✅ **Consolidated MongoDB client** in `services/db.py`
- ✅ **FastAPI lifespan** replacing deprecated `on_event`
- ✅ **MediaRecorder capability sniffing** (Safari mp4 fallback)
- ✅ Explicit pricing (`cost_per_1k_output_tokens_eur` + `cost_per_image_eur`) on all 5 models
- ✅ **Tests**: 60/60 (14 + 15 + 13 + 18)

## Backlog
- **P3** Cost budget alerting (email/webhook when session cost > threshold)
- **P3** Recipe editor UI (user-created recipes persisted in Mongo)
- **P3** Historical charts (cost/latency over time, not just aggregates)
- **P3** Model comparison scorecard (compare mode → save winning model per intent)
- **P3** Export session as Markdown / PDF
