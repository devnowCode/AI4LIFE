import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Request timeout budgets (ms) — named for clarity
const DEFAULT_TIMEOUT_MS = 180_000;         // 3 min default axios timeout
const ORCHESTRATE_TIMEOUT_MS = 240_000;     // 4 min for /orchestrate + /compare (multi-model)
const TRANSCRIBE_TIMEOUT_MS = 120_000;      // 2 min for Whisper STT

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
  timeout: DEFAULT_TIMEOUT_MS,
});

export async function fetchModels() {
  const { data } = await api.get("/models");
  return data;
}

export async function orchestrate(payload) {
  const { data } = await api.post("/orchestrate", payload, { timeout: ORCHESTRATE_TIMEOUT_MS });
  return data;
}

export async function transcribe(audioBlob, language = "it") {
  const form = new FormData();
  form.append("audio", audioBlob, "recording.webm");
  form.append("language", language);
  const { data } = await axios.post(`${API}/transcribe`, form, {
    timeout: TRANSCRIBE_TIMEOUT_MS,
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function compare(payload) {
  const { data } = await api.post("/compare", payload, { timeout: ORCHESTRATE_TIMEOUT_MS });
  return data;
}

export async function listSessions() {
  const { data } = await api.get("/sessions");
  return data.sessions;
}

export async function getSessionMessages(sessionId) {
  const { data } = await api.get(`/sessions/${sessionId}/messages`);
  return data.messages;
}

export async function deleteSession(sessionId) {
  const { data } = await api.delete(`/sessions/${sessionId}`);
  return data;
}

export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const b64 = String(reader.result).split(",")[1];
      resolve({ name: file.name, content_b64: b64, mime: file.type });
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Stream tokens from /api/orchestrate/stream via fetch + ReadableStream.
 * @param {Object} payload - { prompt, files, force_model_id, session_id }
 * @param {Object} handlers - { onMeta, onToken, onImages, onDone, onError }
 */
export async function orchestrateStream(payload, handlers) {
  const { onMeta, onToken, onImages, onDone, onError } = handlers || {};
  const res = await fetch(`${API}/orchestrate/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(payload),
  });
  if (!res.ok || !res.body) {
    onError?.(new Error(`HTTP ${res.status}`));
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    let idx;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const frame = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const line = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const raw = line.slice(5).trim();
      if (!raw) continue;
      let evt;
      try { evt = JSON.parse(raw); } catch { continue; }
      if (evt.type === "meta") onMeta?.(evt);
      else if (evt.type === "token") onToken?.(evt.delta);
      else if (evt.type === "images") onImages?.(evt.images);
      else if (evt.type === "done") onDone?.(evt);
      else if (evt.type === "error") onError?.(new Error(evt.message));
    }
  }
}
