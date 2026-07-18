"""Semantic Router. Selects the optimal model by cross-referencing intent
with the models_registry weight matrix. Fully driven by external JSON:
adding a new model to models_registry.json is enough — no code changes."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).parent.parent / "config" / "models_registry.json"


def load_registry() -> dict[str, Any]:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize(value: float) -> float:
    return max(0.0, min(1.0, value / 100.0))


def score_model(model: dict[str, Any], intent_id: str, weights: dict[str, float],
                has_files: bool, has_images: bool) -> float:
    matrix = model.get("weight_matrix", {})
    intent_fit = matrix.get(intent_id, 0.5)

    capability = _normalize(model["capability_score"])
    latency = _normalize(model["latency_index"])
    cost = _normalize(model["cost_efficiency"])

    context_bonus = 1.0 if model.get("context_window", 0) >= 200000 else 0.5

    base = (
        intent_fit * (
            weights["capability"] * capability
            + weights["latency"] * latency
            + weights["cost"] * cost
            + weights["context_bonus"] * context_bonus
        )
    )

    # Hard filter: image generation requires image-type models
    if intent_id == "image_generation" and model.get("type") != "image":
        base = 0.0
    if intent_id != "image_generation" and model.get("type") == "image":
        base = 0.0

    # Files / multimodal: prefer models that natively support files
    if has_files and not model.get("supports_files", False) and model.get("type") == "text":
        base *= 0.35  # penalize but don't exclude

    return round(base, 4)


def route(intent_id: str, has_files: bool = False, has_images: bool = False,
          force_model_id: str | None = None,
          weights_override: dict[str, float] | None = None) -> dict[str, Any]:
    """Return the selected model and full scoring breakdown."""
    registry = load_registry()
    weights = {**registry["routing_weights"], **(weights_override or {})}
    candidates = []

    for model in registry["models"]:
        s = score_model(model, intent_id, weights, has_files, has_images)
        candidates.append({
            "id": model["id"],
            "display_name": model["display_name"],
            "provider": model["provider"],
            "model_name": model["model_name"],
            "type": model["type"],
            "score": s,
            "capability_score": model["capability_score"],
            "latency_index": model["latency_index"],
            "cost_efficiency": model["cost_efficiency"],
            "tagline": model["tagline"],
            "supports_files": model.get("supports_files", False),
            "supports_images": model.get("supports_images", False),
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)

    if force_model_id:
        forced = next((c for c in candidates if c["id"] == force_model_id), None)
        if forced:
            selected = forced
        else:
            selected = candidates[0]
    else:
        selected = candidates[0]

    return {
        "selected": selected,
        "candidates": candidates[:5],
        "weights": weights,
    }


def build_insight(intent: dict[str, Any], routing: dict[str, Any]) -> str:
    """Generate the technical 'Insight' explanation shown to the user."""
    sel = routing["selected"]
    lines = [
        f"# Routing Decision",
        f"",
        f"intent            = {intent['intent_id']}  ({intent['intent_label']})",
        f"confidence        = {intent['confidence']}",
        f"matched_keywords  = {intent['matched_keywords'] or '—'}",
        f"has_files         = {intent['has_files']}",
        f"has_images        = {intent['has_images']}",
        f"",
        f"# Selected Model",
        f"",
        f"model             = {sel['display_name']}  ({sel['provider']}:{sel['model_name']})",
        f"score             = {sel['score']}",
        f"capability_score  = {sel['capability_score']}",
        f"latency_index     = {sel['latency_index']}",
        f"cost_efficiency   = {sel['cost_efficiency']}",
        f"",
        f"# Alternatives",
        f"",
    ]
    for c in routing["candidates"][1:4]:
        lines.append(f"  ~ {c['display_name']:<20} score={c['score']}  ({c['tagline']})")
    lines += [
        f"",
        f"# Weight Matrix (applied)",
        f"",
        f"capability  weight = {routing['weights']['capability']}",
        f"latency     weight = {routing['weights']['latency']}",
        f"cost        weight = {routing['weights']['cost']}",
        f"context     weight = {routing['weights']['context_bonus']}",
    ]
    return "\n".join(lines)
