import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
  timeout: 120000,
});

export async function fetchModels() {
  const { data } = await api.get("/models");
  return data;
}

export async function detectRoute(prompt, hasFiles, hasImages) {
  const { data } = await api.post("/route", {
    prompt,
    has_files: hasFiles,
    has_images: hasImages,
  });
  return data;
}

export async function orchestrate(payload) {
  const { data } = await api.post("/orchestrate", payload, { timeout: 180000 });
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
