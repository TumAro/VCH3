// localStorage access that never throws (private mode, blocked storage).
// read() returns: string when set, null when never set, undefined when storage is unavailable.

export function read(key) {
  try { return localStorage.getItem(key); } catch (e) { return undefined; }
}

export function write(key, value) {
  try { localStorage.setItem(key, value); return true; } catch (e) { return false; }
}

export function readJson(key, fallback) {
  const raw = read(key);
  if (raw === null || raw === undefined) return fallback;
  try { return JSON.parse(raw); } catch (e) { return fallback; }
}

export function writeJson(key, value) {
  return write(key, JSON.stringify(value));
}
