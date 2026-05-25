/** Mirror of the Pydantic schemas in Website Assets/Industry News/backend/app/models.py. */

export type Status = "GA" | "Public Preview" | "Beta" | "Upcoming";

export type CategorySpec = {
  slug: string;
  label: string;
  description?: string;
};

export type FeedMeta = {
  slug: string;
  name: string;
  tagline: string;
  italic_phrase: string;
  description: string;
  audience_role: string;
  categories: CategorySpec[];
  statuses: Status[];
  sources: string[];
  op_code: string;
};

export type Item = {
  id: string;
  title: string;
  date: string;
  status: Status;
  categories: string[];
  link: string;
  summary: string;
  why: string;
  first_seen_at: string;
};

export type FeedPayload = {
  meta: FeedMeta;
  items: Item[];
  last_refreshed_at: string | null;
  source_errors: string[];
};

export type FeedSummary = {
  slug: string;
  name: string;
  tagline: string;
  item_count: number;
  last_refreshed_at: string | null;
};
