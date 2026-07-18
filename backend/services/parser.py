"""Intelligent file ingestion. Converts PDFs/images/text into AI-readable
formats and returns a summary + saved file path for multimodal LLM calls."""
from __future__ import annotations
import base64
import os
import tempfile
from pathlib import Path
from typing import Any

from pypdf import PdfReader

UPLOAD_DIR = Path(tempfile.gettempdir()) / "ai4life_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def _guess_mime(filename: str, provided: str | None) -> str:
    if provided:
        return provided
    ext = filename.lower().rsplit(".", 1)[-1]
    return {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "txt": "text/plain",
    }.get(ext, "application/octet-stream")


def parse_file(filename: str, content_b64: str, provided_mime: str | None = None) -> dict[str, Any]:
    """Decode a base64-encoded file, persist it, and return metadata.

    Returns a dict with: name, mime, path, preview (str), kind ('pdf'|'image'|'text')
    """
    mime = _guess_mime(filename, provided_mime)
    raw = base64.b64decode(content_b64)

    safe_name = filename.replace("/", "_").replace("\\", "_")
    path = UPLOAD_DIR / f"{os.getpid()}_{os.urandom(4).hex()}_{safe_name}"
    path.write_bytes(raw)

    preview = ""
    kind = "text"

    if mime == "application/pdf":
        kind = "pdf"
        try:
            reader = PdfReader(str(path))
            pages_text = []
            for i, page in enumerate(reader.pages[:20]):  # cap 20 pages
                pages_text.append(page.extract_text() or "")
            preview = "\n\n".join(pages_text).strip()[:8000]
        except Exception as e:
            preview = f"[Impossibile estrarre testo dal PDF: {e}]"
    elif mime.startswith("image/"):
        kind = "image"
        preview = f"[Immagine allegata: {safe_name}, {len(raw)} bytes]"
    elif mime.startswith("text/"):
        kind = "text"
        try:
            preview = raw.decode("utf-8", errors="ignore")[:8000]
        except Exception:
            preview = "[File testo non decodificabile]"

    return {
        "name": safe_name,
        "mime": mime,
        "path": str(path),
        "preview": preview,
        "kind": kind,
        "size_bytes": len(raw),
    }
