"""MongoDB persistence for orchestrator sessions and messages."""
from __future__ import annotations
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent.parent / ".env")

_mongo_url = os.environ["MONGO_URL"]
_client = AsyncIOMotorClient(_mongo_url)
_db = _client[os.environ["DB_NAME"]]
messages = _db["ai4life_messages"]
sessions = _db["ai4life_sessions"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def save_turn(
    session_id: str,
    prompt: str,
    result: str,
    intent: dict[str, Any],
    routing_selected: dict[str, Any],
    insight: str,
    images: list[dict[str, Any]] | None = None,
) -> str:
    """Persist a single turn. Returns the message id."""
    mid = str(uuid.uuid4())
    # Store the full image payloads inline (data URLs). Under Mongo 16MB doc limit
    # for typical 1-3 images per turn.
    doc = {
        "id": mid,
        "session_id": session_id,
        "prompt": prompt,
        "result": result,
        "intent": intent,
        "routing_selected": routing_selected,
        "insight": insight,
        "images": images or [],
        "has_images": bool(images),
        "num_images": len(images or []),
        "created_at": _now_iso(),
    }
    await messages.insert_one(doc)

    # Upsert session summary
    await sessions.update_one(
        {"id": session_id},
        {
            "$setOnInsert": {
                "id": session_id,
                "created_at": _now_iso(),
                "title": (prompt or "Nuova sessione")[:80],
            },
            "$set": {
                "updated_at": _now_iso(),
                "last_model": routing_selected.get("display_name"),
            },
            "$inc": {"turn_count": 1},
        },
        upsert=True,
    )
    return mid


async def list_sessions(limit: int = 50) -> list[dict[str, Any]]:
    docs = await sessions.find({}, {"_id": 0}).sort("updated_at", -1).to_list(limit)
    return docs


async def get_session_history(session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    docs = await messages.find(
        {"session_id": session_id},
        {"_id": 0},
    ).sort("created_at", 1).to_list(limit)
    return docs


async def delete_session(session_id: str) -> int:
    r1 = await messages.delete_many({"session_id": session_id})
    await sessions.delete_one({"id": session_id})
    return r1.deleted_count


async def get_recent_turns_for_context(session_id: str, k: int = 4) -> list[dict[str, Any]]:
    """Fetch last k turns to inject as multi-turn context."""
    docs = await messages.find(
        {"session_id": session_id},
        {"_id": 0, "prompt": 1, "result": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(k)
    return list(reversed(docs))
