"""MongoDB persistence for orchestrator sessions and messages.
Large images are offloaded to GridFS to keep message documents lean."""
from __future__ import annotations
import base64
import uuid
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from .db import messages, sessions, images_bucket


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _store_image_gridfs(data_url: str, mime_type: str) -> str:
    """Upload a data-url image to GridFS. Returns the object id as string."""
    if data_url.startswith("data:"):
        b64 = data_url.split(",", 1)[1]
    else:
        b64 = data_url
    raw = base64.b64decode(b64)
    file_id = await images_bucket.upload_from_stream(
        f"img_{uuid.uuid4().hex}",
        raw,
        metadata={"mime_type": mime_type, "created_at": _now_iso()},
    )
    return str(file_id)


async def _read_image_gridfs(gridfs_id: str, mime_type: str) -> str:
    """Fetch a GridFS image and return its data_url."""
    stream = await images_bucket.open_download_stream(ObjectId(gridfs_id))
    raw = await stream.read()
    return f"data:{mime_type};base64,{base64.b64encode(raw).decode('utf-8')}"


async def save_turn(
    session_id: str,
    prompt: str,
    result: str,
    intent: dict[str, Any],
    routing_selected: dict[str, Any],
    insight: str,
    images: list[dict[str, Any]] | None = None,
    cost_estimate_eur: float = 0.0,
    latency_ms: int = 0,
) -> str:
    """Persist one turn; store images in GridFS, keep only references in the doc."""
    mid = str(uuid.uuid4())

    stored_images: list[dict[str, Any]] = []
    for img in (images or []):
        try:
            gid = await _store_image_gridfs(img["data_url"], img.get("mime_type", "image/png"))
            stored_images.append({"gridfs_id": gid, "mime_type": img.get("mime_type", "image/png")})
        except Exception:
            # If GridFS fails, skip that image rather than crash the whole turn
            continue

    doc = {
        "id": mid,
        "session_id": session_id,
        "prompt": prompt,
        "result": result,
        "intent": intent,
        "routing_selected": routing_selected,
        "insight": insight,
        "images": stored_images,
        "has_images": bool(stored_images),
        "num_images": len(stored_images),
        "cost_estimate_eur": round(cost_estimate_eur, 6),
        "latency_ms": latency_ms,
        "created_at": _now_iso(),
    }
    await messages.insert_one(doc)

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
            "$inc": {"turn_count": 1, "total_cost_eur": round(cost_estimate_eur, 6)},
        },
        upsert=True,
    )
    return mid


async def list_sessions(limit: int = 50) -> list[dict[str, Any]]:
    return await sessions.find({}, {"_id": 0}).sort("updated_at", -1).to_list(limit)


async def _hydrate_message(doc: dict[str, Any]) -> dict[str, Any]:
    """Resolve GridFS image refs into data_urls for client consumption."""
    hydrated_images = []
    for img in doc.get("images", []):
        gid = img.get("gridfs_id")
        if gid:
            try:
                du = await _read_image_gridfs(gid, img.get("mime_type", "image/png"))
                hydrated_images.append({"mime_type": img.get("mime_type", "image/png"), "data_url": du})
            except Exception:
                continue
        elif "data_url" in img:
            # Backward compat with legacy inline-stored images
            hydrated_images.append(img)
    doc["images"] = hydrated_images
    return doc


async def get_session_history(session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    docs = await messages.find(
        {"session_id": session_id},
        {"_id": 0},
    ).sort("created_at", 1).to_list(limit)
    return [await _hydrate_message(d) for d in docs]


async def delete_session(session_id: str) -> int:
    # Delete GridFS blobs for this session's messages
    async for doc in messages.find({"session_id": session_id}, {"images": 1, "_id": 0}):
        for img in doc.get("images", []):
            gid = img.get("gridfs_id")
            if gid:
                try:
                    await images_bucket.delete(ObjectId(gid))
                except Exception:
                    pass
    r1 = await messages.delete_many({"session_id": session_id})
    await sessions.delete_one({"id": session_id})
    return r1.deleted_count


async def get_recent_turns_for_context(session_id: str, k: int = 4) -> list[dict[str, Any]]:
    docs = await messages.find(
        {"session_id": session_id},
        {"_id": 0, "prompt": 1, "result": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(k)
    return list(reversed(docs))
