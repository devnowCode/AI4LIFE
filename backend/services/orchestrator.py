"""Orchestrator: glue between intent, router, parser, and the LlmChat SDK.
Implements the 3-phase pipeline: Ingestion -> Inference -> Delivery."""
from __future__ import annotations
import os
import uuid
from typing import Any

from emergentintegrations.llm.chat import (
    LlmChat,
    UserMessage,
    FileContentWithMimeType,
)

from .intent import detect_intent
from .router import route, build_insight
from .parser import parse_file

SYSTEM_MESSAGE = (
    "Sei un assistente AI professionale integrato in AI4LIFE, un orchestratore "
    "intelligente di modelli. Rispondi in italiano con precisione e chiarezza "
    "enterprise. Formatta le risposte in markdown quando utile. Sii conciso, "
    "diretto, e mostra padronanza tecnica."
)


def _build_prompt_template(intent_id: str, user_text: str, file_previews: list[dict[str, Any]]) -> str:
    """Context Injection: wrap user text with intent-aware framing + file context."""
    parts: list[str] = []

    intent_framing = {
        "code": "L'utente richiede assistenza sul codice. Fornisci codice pulito, commentato e testabile.",
        "reasoning": "L'utente vuole ragionamento strutturato. Esponi ipotesi, passaggi logici e conclusione.",
        "creative": "L'utente cerca output creativo. Sii originale, evocativo e curato nel linguaggio.",
        "summarization": "L'utente vuole una sintesi. Estrai i 3-7 punti chiave, poi un TL;DR finale.",
        "translation": "L'utente richiede una traduzione. Mantieni tono e sfumature dell'originale.",
        "analysis": "L'utente richiede analisi. Presenta findings, evidenze e implicazioni.",
        "multimodal": "L'utente ha allegato file. Analizza il contenuto e rispondi in modo mirato.",
        "image_generation": "L'utente richiede la generazione di un'immagine.",
        "quick_qa": "Rispondi in modo diretto e conciso.",
    }
    parts.append(f"[CONTEXT-INJECTION | intent={intent_id}]")
    parts.append(intent_framing.get(intent_id, ""))

    # Text-only preview injection for PDFs / text files (images handled as attachments)
    text_files = [f for f in file_previews if f["kind"] in ("pdf", "text") and f.get("preview")]
    if text_files:
        parts.append("\n[FILE-CONTEXT]")
        for f in text_files:
            parts.append(f"\n--- {f['name']} ({f['mime']}) ---\n{f['preview']}")

    parts.append("\n[USER-REQUEST]")
    parts.append(user_text or "(nessun testo, valutare solo gli allegati)")
    return "\n".join(parts)


async def orchestrate(prompt: str, files: list[dict[str, Any]] | None = None,
                      force_model_id: str | None = None,
                      session_id: str | None = None) -> dict[str, Any]:
    """Run the full 3-phase pipeline and return a structured result."""
    files = files or []
    session_id = session_id or str(uuid.uuid4())

    # Phase 1: Ingestion
    parsed_files = []
    for f in files:
        try:
            parsed_files.append(parse_file(f["name"], f["content_b64"], f.get("mime")))
        except Exception as e:
            parsed_files.append({"name": f.get("name"), "error": str(e), "kind": "error", "preview": "", "mime": "", "path": None})

    has_files = any(pf.get("kind") == "pdf" or pf.get("kind") == "text" for pf in parsed_files)
    has_images = any(pf.get("kind") == "image" for pf in parsed_files)

    # Intent + Routing
    intent = detect_intent(prompt, has_files=has_files, has_images=has_images)
    routing = route(intent["intent_id"], has_files=has_files, has_images=has_images,
                    force_model_id=force_model_id)
    selected = routing["selected"]

    # Guardrail: MVP does not generate images yet — inform the user gracefully
    if selected["type"] == "image":
        insight = build_insight(intent, routing)
        return {
            "session_id": session_id,
            "intent": intent,
            "routing": routing,
            "result": (
                f"**Modello selezionato: {selected['display_name']}**  \n"
                f"Il routing ha identificato una richiesta di generazione immagine. "
                f"L'orchestratore ha instradato correttamente la richiesta al modello ottimale.  \n\n"
                f"> ⚡ La generazione immagini via *{selected['display_name']}* sarà attivata "
                f"nel prossimo iteration. Il routing engine funziona correttamente."
            ),
            "insight": insight,
            "files": [{"name": pf.get("name"), "kind": pf.get("kind"), "size_bytes": pf.get("size_bytes", 0)} for pf in parsed_files],
        }

    # Phase 2: Inference
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY non configurata")

    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=SYSTEM_MESSAGE,
    ).with_model(selected["provider"], selected["model_name"])

    prompt_final = _build_prompt_template(intent["intent_id"], prompt, parsed_files)

    # Attach files ONLY when using Gemini (SDK constraint per playbook)
    file_contents = []
    if selected["provider"] == "gemini":
        for pf in parsed_files:
            if pf.get("path") and pf.get("kind") in ("pdf", "image", "text"):
                try:
                    file_contents.append(FileContentWithMimeType(
                        file_path=pf["path"], mime_type=pf["mime"],
                    ))
                except Exception:
                    pass

    user_message = UserMessage(text=prompt_final, file_contents=file_contents or None)

    try:
        response_text = await chat.send_message(user_message)
    except Exception as e:
        response_text = f"[Errore inference: {e}]"

    # Phase 3: Delivery
    insight = build_insight(intent, routing)

    return {
        "session_id": session_id,
        "intent": intent,
        "routing": routing,
        "result": response_text,
        "insight": insight,
        "files": [{"name": pf.get("name"), "kind": pf.get("kind"), "size_bytes": pf.get("size_bytes", 0)} for pf in parsed_files],
    }
