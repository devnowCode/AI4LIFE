import json
import os
import logging
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from emergentintegrations.llm.openai import OpenAISpeechToText

from services.router import load_registry, route
from services.intent import detect_intent
from services.orchestrator import (
    orchestrate,
    orchestrate_stream,
    orchestrate_compare,
)
from services import history


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="AI4LIFE Orchestrator API")
api_router = APIRouter(prefix="/api")


class FileInput(BaseModel):
    name: str
    content_b64: str
    mime: str | None = None


class OrchestrateRequest(BaseModel):
    prompt: str = Field(default="")
    files: list[FileInput] = Field(default_factory=list)
    force_model_id: str | None = None
    session_id: str | None = None
    weights_override: dict[str, float] | None = None


class IntentRequest(BaseModel):
    prompt: str
    has_files: bool = False
    has_images: bool = False


class CompareRequest(BaseModel):
    prompt: str
    model_ids: list[str] = Field(default_factory=list)
    files: list[FileInput] = Field(default_factory=list)
    session_id: str | None = None


@api_router.get("/")
async def root() -> dict[str, Any]:
    return {"app": "AI4LIFE", "status": "online", "version": "1.2.0"}


@api_router.get("/models")
async def get_models() -> dict[str, Any]:
    return load_registry()


@api_router.post("/intent")
async def api_detect_intent(req: IntentRequest) -> dict[str, Any]:
    return detect_intent(req.prompt, has_files=req.has_files, has_images=req.has_images)


@api_router.post("/route")
async def api_route(req: IntentRequest) -> dict[str, Any]:
    intent = detect_intent(req.prompt, has_files=req.has_files, has_images=req.has_images)
    routing = route(intent["intent_id"], has_files=req.has_files, has_images=req.has_images)
    return {"intent": intent, "routing": routing}


@api_router.post("/orchestrate")
async def api_orchestrate(req: OrchestrateRequest) -> dict[str, Any]:
    if not req.prompt and not req.files:
        raise HTTPException(status_code=400, detail="Prompt o file obbligatori")
    files_payload = [f.model_dump() for f in req.files]
    return await orchestrate(
        prompt=req.prompt,
        files=files_payload,
        force_model_id=req.force_model_id,
        session_id=req.session_id,
        weights_override=req.weights_override,
    )


@api_router.post("/orchestrate/stream")
async def api_orchestrate_stream(req: OrchestrateRequest):
    if not req.prompt and not req.files:
        raise HTTPException(status_code=400, detail="Prompt o file obbligatori")
    files_payload = [f.model_dump() for f in req.files]

    async def event_gen() -> AsyncGenerator[bytes, None]:
        async for evt in orchestrate_stream(
            prompt=req.prompt,
            files=files_payload,
            force_model_id=req.force_model_id,
            session_id=req.session_id,
            weights_override=req.weights_override,
        ):
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n".encode("utf-8")

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@api_router.post("/compare")
async def api_compare(req: CompareRequest) -> dict[str, Any]:
    if not req.prompt:
        raise HTTPException(status_code=400, detail="Prompt obbligatorio")
    if len(req.model_ids) < 2:
        raise HTTPException(status_code=400, detail="Almeno 2 modelli richiesti")
    if len(req.model_ids) > 4:
        raise HTTPException(status_code=400, detail="Massimo 4 modelli")
    files_payload = [f.model_dump() for f in req.files]
    return await orchestrate_compare(
        prompt=req.prompt,
        model_ids=req.model_ids,
        files=files_payload,
        session_id=req.session_id,
    )


# -------- Sessions --------

@api_router.get("/sessions")
async def api_list_sessions() -> dict[str, Any]:
    return {"sessions": await history.list_sessions()}


@api_router.get("/sessions/{session_id}/messages")
async def api_session_messages(session_id: str) -> dict[str, Any]:
    return {"session_id": session_id, "messages": await history.get_session_history(session_id)}


@api_router.delete("/sessions/{session_id}")
async def api_delete_session(session_id: str) -> dict[str, Any]:
    deleted = await history.delete_session(session_id)
    return {"session_id": session_id, "deleted_messages": deleted}


# -------- Voice / Whisper --------

@api_router.post("/transcribe")
async def api_transcribe(
    audio: UploadFile = File(...),
    language: str = Form(default="it"),
) -> dict[str, Any]:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY non configurata")

    # Persist to a tmp file so the SDK can read from disk
    suffix = "." + (audio.filename or "audio.webm").rsplit(".", 1)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Audio troppo grande (max 25MB)")
        tmp.write(content)
        tmp_path = tmp.name

    try:
        stt = OpenAISpeechToText(api_key=api_key)
        with open(tmp_path, "rb") as fh:
            response = await stt.transcribe(
                file=fh,
                model="whisper-1",
                response_format="json",
                language=language or "it",
            )
        text = getattr(response, "text", None) or ""
        return {"text": text, "language": language}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Whisper error: {e}") from e
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ai4life")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
