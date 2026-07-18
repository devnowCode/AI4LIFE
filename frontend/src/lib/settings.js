const KEY_WEIGHTS = "ai4life_weights_v1";
const KEY_STYLES = "ai4life_active_styles_v1";

export const DEFAULT_WEIGHTS = {
  capability: 0.55,
  latency: 0.20,
  cost: 0.15,
  context_bonus: 0.10,
};

export function getWeights() {
  try {
    const raw = localStorage.getItem(KEY_WEIGHTS);
    if (!raw) return { ...DEFAULT_WEIGHTS };
    return { ...DEFAULT_WEIGHTS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_WEIGHTS };
  }
}

export function setWeights(w) {
  localStorage.setItem(KEY_WEIGHTS, JSON.stringify(w));
}

export function resetWeights() {
  localStorage.removeItem(KEY_WEIGHTS);
  return { ...DEFAULT_WEIGHTS };
}

// Normalize so all four sum to 1.0
export function normalizeWeights(w) {
  const sum = (w.capability + w.latency + w.cost + w.context_bonus) || 1;
  return {
    capability: +(w.capability / sum).toFixed(3),
    latency: +(w.latency / sum).toFixed(3),
    cost: +(w.cost / sum).toFixed(3),
    context_bonus: +(w.context_bonus / sum).toFixed(3),
  };
}

// -------- Style presets --------
export function getActiveStyles() {
  try { return JSON.parse(localStorage.getItem(KEY_STYLES) || "[]"); }
  catch { return []; }
}

export function setActiveStyles(list) {
  localStorage.setItem(KEY_STYLES, JSON.stringify(list));
}
