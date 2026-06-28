import type { Status } from "@/lib/industry-news";

export function StatusBadge({ status }: { status: Status }) {
  if (status === "GA") {
    return <span className="news-status-badge news-status-ga">{status}</span>;
  }

  if (status === "Public Preview") {
    return <span className="news-status-badge news-status-preview">Preview</span>;
  }

  if (status === "Beta") {
    return <span className="news-status-badge news-status-beta">{status}</span>;
  }

  return <span className="news-status-badge news-status-upcoming">{status}</span>;
}
