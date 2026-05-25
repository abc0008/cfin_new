/** Per-feed localStorage tracker for item ids the user has already seen. */

const seenKey = (slug: string) => `ace-news-seen:${slug}:v1`;

export function loadSeen(slug: string): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(seenKey(slug));
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

export function saveSeen(slug: string, ids: Set<string>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(seenKey(slug), JSON.stringify(Array.from(ids)));
  } catch {
    /* non-fatal storage failure */
  }
}
