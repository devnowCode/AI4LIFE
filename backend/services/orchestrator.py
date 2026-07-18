"""Orchestrator: 3-phase pipeline with streaming, multi-turn history,
image generation (Nano Banana + GPT-image-1), parallel compare mode,
and per-turn cost/latency telemetry."""
from __future__ import annotations
import asyncio
import base64
import os
import time
import uuid
from typing import Any, AsyncGenerator

from emergentintegrations.llm.chat import (
    LlmChat,
    UserMessage,
    FileContentWithMimeType,
    ImageContent,
    TextDelta,
    StreamDone,
)
from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration

from .intent import detect_intent
from .router import route, build_insight, load_registry
from .parser import parse_file
from . import history
from . import telemetry

SYSTEM_MESSAGE = (
    "Sei un assistente AI professionale integrato in AI4LIFE, un orchestratore "
    "intelligente di modelli. Rispondi in italiano con precisione e chiarezza "
    "enterprise. Formatta le risposte in markdown quando utile. Sii conciso, "
    "diretto, e mostra padronanza tecnica."
)


# -------- Ingestion + Router helpers --------

def _parse_all(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parsed = []
    for f in files:
        try:
            parsed.append(parse_file(f["name"], f["content_b64"], f.get("mime")))
        except Exception as e:
            parsed.append({"name": f.get("name"), "error": str(e), "kind": "error", "preview": "", "mime": "", "path": None})
    return parsed


def _flags(parsed_files: list[dict[str, Any]]) -> tuple[bool, bool]:
    has_files = any(pf.get("kind") in ("pdf", "text") for pf in parsed_files)
    has_images = any(pf.get("kind") == "image" for pf in parsed_files)
    return has_files, has_images


def _intent_framing(intent_id: str) -> str:
    return {
        "code": "L'utente richiede assistenza sul codice. Fornisci codice pulito, commentato e testabile.",
        "reasoning": "L'utente vuole ragionamento strutturato. Esponi ipotesi, passaggi logici e conclusione.",
        "creative": "L'utente cerca output creativo. Sii originale, evocativo e curato nel linguaggio.",
        "summarization": "L'utente vuole una sintesi. Estrai i 3-7 punti chiave, poi un TL;DR finale.",
        "translation": "L'utente richiede una traduzione. Mantieni tono e sfumature dell'originale.",
        "analysis": "L'utente richiede analisi. Presenta findings, evidenze e implicazioni.",
        "multimodal": "L'utente ha allegato file. Analizza il contenuto e rispondi in modo mirato.",
        "image_generation": "L'utente richiede la generazione di un'immagine.",
        "quick_qa": "Rispondi in modo diretto e conciso.",
    }.get(intent_id, "")


def _build_prompt(
    intent_id: str,
    user_text: str,
    file_previews: list[dict[str, Any]],
    prior_turns: list[dict[str, Any]] | None = None,
) -> str:
    """Context Injection: intent framing + prior turns + file context + user request."""
    parts: list[str] = [f"[CONTEXT-INJECTION | intent={intent_id}]", _intent_framing(intent_id)]

    if prior_turns:
        parts.append("\n[PRIOR-CONTEXT]")
        for t in prior_turns:
            parts.append(f"\nUtente: {t.get('prompt', '')[:600]}")
            parts.append(f"Assistente: {(t.get('result') or '')[:800]}")

    text_files = [f for f in file_previews if f["kind"] in ("pdf", "text") and f.get("preview")]
    if text_files:
        parts.append("\n[FILE-CONTEXT]")
        for f in text_files:
            parts.append(f"\n--- {f['name']} ({f['mime']}) ---\n{f['preview']}")

    parts.append("\n[USER-REQUEST]")
    parts.append(user_text or "(nessun testo, valutare solo gli allegati)")
    return "\n".join(parts)


def _gemini_file_contents(parsed_files: list[dict[str, Any]]) -> list[FileContentWithMimeType]:
    out = []
    for pf in parsed_files:
        if pf.get("path") and pf.get("kind") in ("pdf", "image", "text"):
            try:
                out.append(FileContentWithMimeType(file_path=pf["path"], mime_type=pf["mime"]))
            except Exception:
                pass
    return out


# -------- Image generation branch --------

async def _run_image_gen(selected: dict[str, Any], prompt: str, parsed_files: list[dict[str, Any]],
                        session_id: str) -> tuple[str, list[dict[str, Any]]]:
    """Return (text, images[]). Handles both Nano Banana and GPT-image-1."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY non configurata")

    provider = selected.get("provider")

    if provider == "openai":
        # Use OpenAIImageGeneration
        try:
            gen = OpenAIImageGeneration(api_key=api_key)
            imgs = await gen.generate_images(
                prompt=prompt or "Genera un'immagine.",
                model=selected["model_name"],
                number_of_images=1,
            )
            payload = []
            for img_bytes in (imgs or []):
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                payload.append({
                    "mime_type": "image/png",
                    "data_url": f"data:image/png;base64,{b64}",
                })
            return ("Immagine generata.", payload)
        except Exception as e:
            return (f"[Errore image gen ({selected['display_name']}): {e}]", [])

    # Default: Gemini Nano Banana
    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message="You generate high quality images.",
    ).with_model("gemini", selected["model_name"]).with_params(modalities=["image", "text"])

    ref_images = []
    for pf in parsed_files:
        if pf.get("kind") == "image" and pf.get("path"):
            try:
                with open(pf["path"], "rb") as fh:
                    ref_images.append(ImageContent(base64.b64encode(fh.read()).decode("utf-8")))
            except Exception:
                pass

    msg = UserMessage(text=prompt or "Genera un'immagine.", file_contents=ref_images or None)
    try:
        text_out, images_out = await chat.send_message_multimodal_response(msg)
    except Exception as e:
        return (f"[Errore image gen: {e}]", [])

    payload = []
    for img in (images_out or []):
        payload.append({
            "mime_type": img.get("mime_type", "image/png"),
            "data_url": f"data:{img.get('mime_type', 'image/png')};base64,{img.get('data', '')}",
        })
    return (text_out or "Immagine generata.", payload)


# -------- Non-streaming orchestrate (used by /api/orchestrate + /api/compare) --------

async def orchestrate(
    prompt: str,
    files: list[dict[str, Any]] | None = None,
    force_model_id: str | None = None,
    session_id: str | None = None,
    use_history: bool = True,
    persist: bool = True,
    weights_override: dict[str, float] | None = None,
) -> dict[str, Any]:
    files = files or []
    session_id = session_id or str(uuid.uuid4())

    parsed_files = _parse_all(files)
    has_files, has_images = _flags(parsed_files)

    intent = detect_intent(prompt, has_files=has_files, has_images=has_images)
    routing = route(intent["intent_id"], has_files=has_files, has_images=has_images,
                    force_model_id=force_model_id, weights_override=weights_override)
    selected = routing["selected"]
    insight = build_insight(intent, routing)

    # Look up the full registry entry to get pricing (weight_matrix section only has scores)
    registry = load_registry()
    full_model = next((m for m in registry["models"] if m["id"] == selected["id"]), selected)

    # Image gen branch
    if selected["type"] == "image":
        t0 = time.perf_counter()
        text_out, images = await _run_image_gen(selected, prompt, parsed_files, session_id)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        cost = telemetry.estimate_cost_eur(full_model, text_out, num_images=len(images))
        payload = {
            "session_id": session_id,
            "intent": intent,
            "routing": routing,
            "result": text_out,
            "images": images,
            "insight": insight,
            "cost_estimate_eur": cost,
            "latency_ms": latency_ms,
            "files": [{"name": pf.get("name"), "kind": pf.get("kind"), "size_bytes": pf.get("size_bytes", 0)} for pf in parsed_files],
        }
        if persist:
            await history.save_turn(session_id, prompt, text_out, intent, selected, insight, images,
                                    cost_estimate_eur=cost, latency_ms=latency_ms)
            await telemetry.log_turn(session_id, selected["id"], selected["display_name"],
                                     intent["intent_id"], latency_ms, cost, num_images=len(images),
                                     output_len=len(text_out))
        return payload

    # Text branch
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY non configurata")

    prior_turns = await history.get_recent_turns_for_context(session_id, k=4) if use_history else []

    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=SYSTEM_MESSAGE,
    ).with_model(selected["provider"], selected["model_name"])

    prompt_final = _build_prompt(intent["intent_id"], prompt, parsed_files, prior_turns)
    file_contents = _gemini_file_contents(parsed_files) if selected["provider"] == "gemini" else []
    user_message = UserMessage(text=prompt_final, file_contents=file_contents or None)

    try:
        t0 = time.perf_counter()
        response_text = await chat.send_message(user_message)
        latency_ms = int((time.perf_counter() - t0) * 1000)
    except Exception as e:
        response_text = f"[Errore inference: {e}]"
        latency_ms = 0

    cost = telemetry.estimate_cost_eur(full_model, response_text)

    payload = {
        "session_id": session_id,
        "intent": intent,
        "routing": routing,
        "result": response_text,
        "images": [],
        "insight": insight,
        "cost_estimate_eur": cost,
        "latency_ms": latency_ms,
        "files": [{"name": pf.get("name"), "kind": pf.get("kind"), "size_bytes": pf.get("size_bytes", 0)} for pf in parsed_files],
    }
    if persist:
        await history.save_turn(session_id, prompt, response_text, intent, selected, insight, [],
                                cost_estimate_eur=cost, latency_ms=latency_ms)
        await telemetry.log_turn(session_id, selected["id"], selected["display_name"],
                                 intent["intent_id"], latency_ms, cost,
                                 output_len=len(response_text))
    return payload


# -------- Streaming orchestrate (SSE) --------

async def orchestrate_stream(
    prompt: str,
    files: list[dict[str, Any]] | None = None,
    force_model_id: str | None = None,
    session_id: str | None = None,
    weights_override: dict[str, float] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Yield SSE-friendly events. Contract:
       {"type": "meta", ...}  -> initial routing metadata
       {"type": "token", "delta": "..."} -> streamed text token
       {"type": "images", "images": [...]} -> generated images (for image intents)
       {"type": "done", "result": "...full text..."} -> final marker
       {"type": "error", "message": "..."} -> error
    """
    files = files or []
    session_id = session_id or str(uuid.uuid4())

    parsed_files = _parse_all(files)
    has_files, has_images = _flags(parsed_files)
    intent = detect_intent(prompt, has_files=has_files, has_images=has_images)
    routing = route(intent["intent_id"], has_files=has_files, has_images=has_images,
                    force_model_id=force_model_id, weights_override=weights_override)
    selected = routing["selected"]
    insight = build_insight(intent, routing)
    registry = load_registry()
    full_model = next((m for m in registry["models"] if m["id"] == selected["id"]), selected)

    yield {
        "type": "meta",
        "session_id": session_id,
        "intent": intent,
        "routing": routing,
        "insight": insight,
    }

    # Image branch: non-streaming, deliver as one event
    if selected["type"] == "image":
        t0 = time.perf_counter()
        text_out, images = await _run_image_gen(selected, prompt, parsed_files, session_id)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        cost = telemetry.estimate_cost_eur(full_model, text_out, num_images=len(images))
        yield {"type": "images", "images": images}
        if text_out:
            yield {"type": "token", "delta": text_out}
        await history.save_turn(session_id, prompt, text_out, intent, selected, insight, images,
                                cost_estimate_eur=cost, latency_ms=latency_ms)
        await telemetry.log_turn(session_id, selected["id"], selected["display_name"],
                                 intent["intent_id"], latency_ms, cost, num_images=len(images),
                                 output_len=len(text_out))
        yield {"type": "done", "result": text_out, "cost_estimate_eur": cost, "latency_ms": latency_ms}
        return

    # Text streaming branch
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        yield {"type": "error", "message": "EMERGENT_LLM_KEY non configurata"}
        return

    prior_turns = await history.get_recent_turns_for_context(session_id, k=4)
    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=SYSTEM_MESSAGE,
    ).with_model(selected["provider"], selected["model_name"])

    prompt_final = _build_prompt(intent["intent_id"], prompt, parsed_files, prior_turns)
    file_contents = _gemini_file_contents(parsed_files) if selected["provider"] == "gemini" else []
    user_message = UserMessage(text=prompt_final, file_contents=file_contents or None)

    full = []
    t0 = time.perf_counter()
    try:
        async for ev in chat.stream_message(user_message):
            if isinstance(ev, TextDelta):
                full.append(ev.content)
                yield {"type": "token", "delta": ev.content}
            elif isinstance(ev, StreamDone):
                break
    except Exception as e:
        yield {"type": "error", "message": str(e)}
        return
    latency_ms = int((time.perf_counter() - t0) * 1000)

    result_text = "".join(full)
    cost = telemetry.estimate_cost_eur(full_model, result_text)
    await history.save_turn(session_id, prompt, result_text, intent, selected, insight, [],
                            cost_estimate_eur=cost, latency_ms=latency_ms)
    await telemetry.log_turn(session_id, selected["id"], selected["display_name"],
                             intent["intent_id"], latency_ms, cost, output_len=len(result_text))
    yield {"type": "done", "result": result_text, "cost_estimate_eur": cost, "latency_ms": latency_ms}


# -------- Compare mode --------

async def orchestrate_compare(
    prompt: str,
    model_ids: list[str],
    files: list[dict[str, Any]] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Run the same prompt through N models in parallel. Not persisted per-model."""
    session_id = session_id or str(uuid.uuid4())

    async def one(mid: str) -> dict[str, Any]:
        try:
            r = await orchestrate(
                prompt=prompt,
                files=files or [],
                force_model_id=mid,
                session_id=f"{session_id}::{mid}",
                use_history=False,
                persist=False,
            )
            return {"model_id": mid, "ok": True, "response": r}
        except Exception as e:
            return {"model_id": mid, "ok": False, "error": str(e)}

    tasks = [asyncio.create_task(one(m)) for m in model_ids]
    results = await asyncio.gather(*tasks)
    return {"session_id": session_id, "results": results}
