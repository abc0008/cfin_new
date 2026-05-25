"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  fmtRelative,
  loadSeen,
  saveSeen,
  withinDays,
  type CategorySpec,
  type FeedPayload,
  type Status,
} from "@/lib/industry-news";

import { Cover } from "./Cover";
import { EmptyState } from "./EmptyState";
import { FeedItem } from "./FeedItem";
import { NewsEyebrow } from "./NewsEyebrow";
import { Toolbar } from "./Toolbar";

type FeedViewProps = {
  initial: FeedPayload;
};

export function FeedView({ initial }: FeedViewProps) {
  const { meta, items, last_refreshed_at, source_errors } = initial;

  const [priorSeen, setPriorSeen] = useState<Set<string>>(() => new Set());
  const [selectedCats, setSelectedCats] = useState<Set<string>>(new Set());
  const [selectedStatuses, setSelectedStatuses] = useState<Set<Status>>(new Set());
  const [newOnly, setNewOnly] = useState(false);
  const [windowDays, setWindowDays] = useState<number | "all">(90);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const seen = loadSeen(meta.slug);
    setPriorSeen(seen);

    const next = new Set(seen);
    for (const item of items) next.add(item.id);
    saveSeen(meta.slug, next);
  }, [meta.slug, items]);

  const categoryLookup = useMemo<Record<string, CategorySpec>>(
    () => Object.fromEntries(meta.categories.map((category) => [category.slug, category])),
    [meta.categories],
  );

  const isNew = useCallback((id: string) => !priorSeen.has(id), [priorSeen]);

  const countingPool = useMemo(() => {
    const query = search.trim().toLowerCase();
    return items.filter((item) => {
      if (!withinDays(item.date, windowDays)) return false;
      if (!query) return true;
      const haystack = `${item.title} ${item.summary} ${item.why}`.toLowerCase();
      return haystack.includes(query);
    });
  }, [items, windowDays, search]);

  const catCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const category of meta.categories) counts[category.slug] = 0;
    for (const item of countingPool) {
      for (const category of item.categories) {
        counts[category] = (counts[category] ?? 0) + 1;
      }
    }
    return counts;
  }, [countingPool, meta.categories]);

  const statusCounts = useMemo(() => {
    const counts = {
      GA: 0,
      "Public Preview": 0,
      Beta: 0,
      Upcoming: 0,
    } as Record<Status, number>;
    for (const item of countingPool) {
      counts[item.status] = (counts[item.status] ?? 0) + 1;
    }
    return counts;
  }, [countingPool]);

  const filtered = useMemo(() => {
    const results = countingPool.filter((item) => {
      if (newOnly && !isNew(item.id)) return false;
      if (selectedCats.size > 0 && !item.categories.some((category) => selectedCats.has(category))) {
        return false;
      }
      if (selectedStatuses.size > 0 && !selectedStatuses.has(item.status)) return false;
      return true;
    });

    return results.sort((left, right) => right.date.localeCompare(left.date));
  }, [countingPool, isNew, newOnly, selectedCats, selectedStatuses]);

  const grouped = useMemo(() => {
    const order = meta.categories.map((category) => category.slug);
    const byCategory: Record<string, typeof filtered> = Object.fromEntries(
      order.map((slug) => [slug, []]),
    );

    for (const item of filtered) {
      const primary = order.find((slug) => item.categories.includes(slug));
      if (primary) byCategory[primary].push(item);
    }

    return order
      .filter((slug) => byCategory[slug].length > 0)
      .map((slug) => ({ slug, items: byCategory[slug] }));
  }, [filtered, meta.categories]);

  const total = items.length;
  const newCount = items.filter((item) => isNew(item.id)).length;

  return (
    <main className="news-page">
      <div className="news-shell">
        <div className="news-back-row">
          <Link className="news-back-link news-console-back-link" href="/news">
            ← Back to Industry News Console
          </Link>
        </div>

        <NewsEyebrow feedName={meta.name} opCode={meta.op_code} />

        <Cover
          description={meta.description}
          headline={meta.tagline}
          italicPhrase={meta.italic_phrase}
          newCount={newCount}
          total={total}
        />

        <div className="news-header-row">
          <span className="news-muted">
            {last_refreshed_at ? `Last refresh ${fmtRelative(last_refreshed_at)}` : "Never refreshed"}
          </span>
          {source_errors.length > 0 ? (
            <span className="news-error">
              {source_errors.length} source error{source_errors.length === 1 ? "" : "s"}
            </span>
          ) : null}
        </div>

        <Toolbar
          categories={meta.categories}
          catCounts={catCounts}
          newOnly={newOnly}
          onSearchChange={setSearch}
          onToggleCat={(slug) =>
            setSelectedCats((previous) => {
              const next = new Set(previous);
              if (next.has(slug)) next.delete(slug);
              else next.add(slug);
              return next;
            })
          }
          onToggleNewOnly={() => setNewOnly((value) => !value)}
          onToggleStatus={(status) =>
            setSelectedStatuses((previous) => {
              const next = new Set(previous);
              if (next.has(status)) next.delete(status);
              else next.add(status);
              return next;
            })
          }
          onWindowChange={setWindowDays}
          search={search}
          selectedCats={selectedCats}
          selectedStatuses={selectedStatuses}
          statusCounts={statusCounts}
          statuses={meta.statuses}
          windowDays={windowDays}
        />

        {grouped.length === 0 ? (
          <EmptyState>No items match your filters.</EmptyState>
        ) : (
          <div className="news-items">
            {grouped.map((group) => (
              <section key={group.slug}>
                <h2 className="news-header-row">
                  <span>{categoryLookup[group.slug]?.label ?? group.slug}</span>
                  <span className="news-muted">{String(group.items.length).padStart(2, "0")} ITEMS</span>
                </h2>
                {group.items.map((item) => (
                  <FeedItem
                    categoryLookup={categoryLookup}
                    isNew={isNew(item.id)}
                    item={item}
                    key={item.id}
                  />
                ))}
              </section>
            ))}
          </div>
        )}

        <footer className="news-item-why" style={{ marginTop: 40 }}>
          <span className="news-muted">Sources</span>
          <span>
            Re-queried on the server every hour:{" "}
            {meta.sources.map((source, index) => (
              <span key={source}>
                {index > 0 ? " · " : ""}
                <a
                  className="news-source-link"
                  href={source}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  {new URL(source).hostname}
                </a>
              </span>
            ))}
                . &quot;Why it matters&quot; lines are generated per item via Claude Haiku with a role-specific
            system prompt. Seen-item state lives in your browser, while refresh scheduling and
            dedupe are server-side.
          </span>
        </footer>
      </div>
    </main>
  );
}
