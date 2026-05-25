"use client";

import type { CategorySpec, Status } from "@/lib/industry-news";

type ToolbarProps = {
  categories: CategorySpec[];
  statuses: Status[];
  selectedCats: Set<string>;
  selectedStatuses: Set<Status>;
  newOnly: boolean;
  windowDays: number | "all";
  search: string;
  catCounts: Record<string, number>;
  statusCounts: Record<Status, number>;
  onToggleCat: (slug: string) => void;
  onToggleStatus: (status: Status) => void;
  onToggleNewOnly: () => void;
  onWindowChange: (window: number | "all") => void;
  onSearchChange: (query: string) => void;
};

function statusLabel(status: Status): string {
  return status === "Public Preview" ? "Preview" : status;
}

function chip(
  label: React.ReactNode,
  count: number | null,
  active: boolean,
  onClick: () => void,
) {
  return (
    <button
      type="button"
      className="news-chip"
      data-active={active ? "true" : "false"}
      onClick={onClick}
    >
      {label}
      {typeof count === "number" ? <span className="news-chip-count">{count}</span> : null}
    </button>
  );
}

export function Toolbar(props: ToolbarProps) {
  return (
    <section className="news-toolbar">
      <div className="news-toolbar-row">
        <span className="news-muted">Category</span>
        {props.categories.map((category) =>
          chip(
            category.label,
            props.catCounts[category.slug] ?? 0,
            props.selectedCats.has(category.slug),
            () => props.onToggleCat(category.slug),
          ),
        )}
      </div>

      <div className="news-toolbar-row">
        <span className="news-muted">Status</span>
        {props.statuses.map((status) =>
          chip(
            statusLabel(status),
            props.statusCounts[status] ?? 0,
            props.selectedStatuses.has(status),
            () => props.onToggleStatus(status),
          ),
        )}
        {chip("New only", null, props.newOnly, props.onToggleNewOnly)}
        <span style={{ flex: 1 }} />
        <select
          className="news-chip"
          value={String(props.windowDays)}
          onChange={(event) => {
            const value = event.target.value;
            props.onWindowChange(value === "all" ? "all" : Number(value));
          }}
        >
          <option value="30">L30 days</option>
          <option value="90">L90 days</option>
          <option value="180">L180 days</option>
          <option value="all">All time</option>
        </select>
        <input
          className="news-search"
          type="search"
          placeholder="Search..."
          value={props.search}
          onChange={(event) => props.onSearchChange(event.target.value)}
        />
      </div>
    </section>
  );
}
