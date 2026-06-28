/** Server-side fetch helpers for Industry News routes. */

import type { FeedPayload, FeedSummary } from "@/lib/industry-news/types";

const trimTrailingSlash = (value: string) => value.replace(/\/+$/, "");

const NEWS_API_BASE = trimTrailingSlash(
  process.env.NEXT_PUBLIC_ACE_NEWS_API_BASE?.trim() ||
    process.env.ACE_NEWS_API_BASE?.trim() ||
    "http://localhost:8000"
);

/** Cache responses for 5 minutes; backend refreshes feed snapshots hourly. */
const FETCH_OPTIONS: RequestInit = {
  next: { revalidate: 300 },
  headers: { Accept: "application/json" },
};

const endpointUrl = (path: string): string => `${NEWS_API_BASE}${path}`;

export async function listFeeds(): Promise<FeedSummary[]> {
  const response = await fetch(endpointUrl("/feeds"), FETCH_OPTIONS);
  if (!response.ok) {
    throw new Error(`listFeeds: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function getFeed(slug: string): Promise<FeedPayload> {
  const response = await fetch(endpointUrl(`/feeds/${encodeURIComponent(slug)}`), FETCH_OPTIONS);
  if (!response.ok) {
    throw new Error(`getFeed(${slug}): ${response.status} ${response.statusText}`);
  }
  return response.json();
}
