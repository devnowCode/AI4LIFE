const KEY = "ai4life_archive_v1";

export function getArchive() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function saveToArchive(entry) {
  const list = getArchive();
  list.unshift({ ...entry, id: crypto.randomUUID(), saved_at: new Date().toISOString() });
  localStorage.setItem(KEY, JSON.stringify(list.slice(0, 200)));
  return list;
}

export function removeFromArchive(id) {
  const list = getArchive().filter((e) => e.id !== id);
  localStorage.setItem(KEY, JSON.stringify(list));
  return list;
}

export function clearArchive() {
  localStorage.removeItem(KEY);
}
