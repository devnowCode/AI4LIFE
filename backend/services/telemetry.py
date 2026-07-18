"""Cost estimation + telemetry logging. Cost is symbolic but derived from the
model registry pricing fields for FinOps transparency."""
from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Any

from .db import telemetry


def estimate_cost_eur(model: dict[str, Any], output_text: str, num_images: int = 0) -> float:
    """Rough cost estimate:
       text: chars/4 tokens * price_per_1k_output_tokens_eur
       image: num_images * price_per_image_eur
       Falls back to derived pricing from cost_efficiency score if fields missing.
    """
    price_txt = model.get("cost_per_1k_output_tokens_eur")
    price_img = model.get("cost_per_image_eur")

    if price_txt is None:
        # Derive: cost_efficiency 95 → cheap, 65 → expensive
        ce = max(1, model.get("cost_efficiency", 70))
        price_txt = round(0.02 * (100 - ce) / 100, 5)  # 0 to 0.02 EUR / 1K tokens
    if price_img is None:
        ce = max(1, model.get("cost_efficiency", 70))
        price_img = round(0.03 * (100 - ce) / 100, 4)

    tokens = max(1, len(output_text or "")) / 4.0
    cost = (tokens / 1000.0) * float(price_txt) + num_images * float(price_img)
    return round(cost, 6)


async def log_turn(
    session_id: str,
    model_id: str,
    model_display: str,
    intent_id: str,
    latency_ms: int,
    cost_eur: float,
    num_images: int = 0,
    output_len: int = 0,
) -> None:
    doc = {
        "session_id": session_id,
        "model_id": model_id,
        "model_display": model_display,
        "intent_id": intent_id,
        "latency_ms": latency_ms,
        "cost_eur": round(cost_eur, 6),
        "num_images": num_images,
        "output_len": output_len,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_at_ts": time.time(),
    }
    try:
        await telemetry.insert_one(doc)
    except Exception:
        pass  # never break the request path over telemetry


async def get_summary() -> dict[str, Any]:
    """Aggregate metrics: per-model totals + overall counters."""
    pipeline = [
        {
            "$group": {
                "_id": "$model_display",
                "requests": {"$sum": 1},
                "total_cost": {"$sum": "$cost_eur"},
                "avg_latency": {"$avg": "$latency_ms"},
                "total_images": {"$sum": "$num_images"},
                "last_used": {"$max": "$created_at"},
            }
        },
        {"$sort": {"total_cost": -1}},
    ]
    by_model = [
        {
            "model": r["_id"],
            "requests": r["requests"],
            "total_cost_eur": round(r["total_cost"], 6),
            "avg_latency_ms": int(r["avg_latency"] or 0),
            "total_images": r["total_images"],
            "last_used": r["last_used"],
        }
        async for r in telemetry.aggregate(pipeline)
    ]

    totals = {"requests": 0, "total_cost_eur": 0.0, "avg_latency_ms": 0}
    if by_model:
        totals["requests"] = sum(m["requests"] for m in by_model)
        totals["total_cost_eur"] = round(sum(m["total_cost_eur"] for m in by_model), 6)
        totals["avg_latency_ms"] = int(
            sum(m["avg_latency_ms"] * m["requests"] for m in by_model) / max(totals["requests"], 1)
        )

    recent = await telemetry.find({}, {"_id": 0}).sort("created_at_ts", -1).to_list(20)

    return {"by_model": by_model, "totals": totals, "recent": recent}
