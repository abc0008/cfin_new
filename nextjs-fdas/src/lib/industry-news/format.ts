/** Shared formatters used in both server and client components. */

export function fmtMonoDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const month = date.toLocaleDateString("en-US", { month: "short" }).toUpperCase();
  return `${month} ${String(date.getDate()).padStart(2, "0")} · ${date.getFullYear()}`;
}

export function fmtRelative(iso: string | null | undefined): string {
  if (!iso) return "never";
  const elapsedMs = Date.now() - new Date(iso).getTime();
  const elapsedMinutes = Math.floor(elapsedMs / 60_000);
  if (elapsedMinutes < 1) return "just now";
  if (elapsedMinutes < 60) return `${elapsedMinutes}m ago`;
  const elapsedHours = Math.floor(elapsedMinutes / 60);
  if (elapsedHours < 24) return `${elapsedHours}h ago`;
  const elapsedDays = Math.floor(elapsedHours / 24);
  return `${elapsedDays}d ago`;
}

export function isoWeek(date: Date): number {
  const utcDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNumber = utcDate.getUTCDay() || 7;
  utcDate.setUTCDate(utcDate.getUTCDate() + 4 - dayNumber);
  const yearStart = new Date(Date.UTC(utcDate.getUTCFullYear(), 0, 1));
  return Math.ceil((((utcDate.getTime() - yearStart.getTime()) / 86_400_000) + 1) / 7);
}

export function withinDays(iso: string, days: number | "all"): boolean {
  if (days === "all") return true;
  if (!iso) return true;
  const ageMs = Date.now() - new Date(iso).getTime();
  return ageMs <= days * 86_400_000;
}
