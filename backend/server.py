from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any

from services.router import load_registry, route
from services.intent import detect_intent
from services.orchestrator import orchestrate


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


class IntentRequest(BaseModel):
    prompt: str
    has_files: bool = False
    has_images: bool = False


@api_router.get("/")
async def root() -> dict[str, Any]:
    return {"app": "AI4LIFE", "status": "online", "version": "1.0.0"}


@api_router.get("/models")
async def get_models() -> dict[str, Any]:
    """Return the full model registry — used to render the Model Registry UI."""
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
    result = await orchestrate(
        prompt=req.prompt,
        files=files_payload,
        force_model_id=req.force_model_id,
        session_id=req.session_id,
    )
    return result


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ai4life")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
