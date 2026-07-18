"""Intent detection layer. Rule-based, low-latency pre-processing."""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.json"


def _load_intents() -> list[dict[str, Any]]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["intents"]


def detect_intent(prompt: str, has_files: bool = False, has_images: bool = False) -> dict[str, Any]:
    """Return the best-matching intent with confidence and matched keywords."""
    intents = _load_intents()
    text = (prompt or "").lower()
    scores: dict[str, dict[str, Any]] = {}

    for intent in intents:
        matched = [kw for kw in intent["keywords"] if re.search(rf"\b{re.escape(kw)}\b", text)]
        score = len(matched) / max(len(intent["keywords"]), 1) if intent["keywords"] else 0.0
        scores[intent["id"]] = {
            "label": intent["label"],
            "score": score,
            "matched_keywords": matched,
        }

    # Multimodal boost when files/images are attached
    if has_files or has_images:
        scores["multimodal"]["score"] = max(scores["multimodal"]["score"], 0.85)

    # Pick best. Fallback to quick_qa.
    best_id = max(scores, key=lambda k: scores[k]["score"])
    if scores[best_id]["score"] == 0.0:
        best_id = "quick_qa"

    top3 = sorted(scores.items(), key=lambda kv: kv[1]["score"], reverse=True)[:3]

    return {
        "intent_id": best_id,
        "intent_label": scores[best_id]["label"],
        "confidence": round(scores[best_id]["score"], 3),
        "matched_keywords": scores[best_id]["matched_keywords"],
        "top_candidates": [
            {"id": k, "label": v["label"], "score": round(v["score"], 3)} for k, v in top3
        ],
        "has_files": has_files,
        "has_images": has_images,
    }
