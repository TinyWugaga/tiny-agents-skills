/** @deprecated 改用 httpClient */
export async function legacyFetch(path: string) {
  return fetch(path).then((r) => r.json());
}
export async function httpClient(path: string, init?: RequestInit) {
  const r = await fetch(path, init);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
