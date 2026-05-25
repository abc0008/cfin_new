import type { CategorySpec, Item } from "@/lib/industry-news";
import { fmtMonoDate } from "@/lib/industry-news";
import { StatusBadge } from "./StatusBadge";

type FeedItemProps = {
  item: Item;
  isNew: boolean;
  categoryLookup: Record<string, CategorySpec>;
};

export function FeedItem({ item, isNew, categoryLookup }: FeedItemProps) {
  return (
    <article className="news-item">
      <div className="news-item-rail">
        <span>{fmtMonoDate(item.date)}</span>
        <StatusBadge status={item.status} />
        {isNew ? <span className="news-new-pill">New</span> : null}
        <a
          className="news-source-link"
          href={item.link}
          rel="noopener noreferrer"
          target="_blank"
        >
          Source ↗
        </a>
      </div>

      <div className="news-item-main">
        <h3 className="news-item-title">
          <a href={item.link} rel="noopener noreferrer" target="_blank">
            {item.title}
          </a>
        </h3>
        {item.summary ? <p className="news-item-summary">{item.summary}</p> : null}
        {item.categories.length > 0 ? (
          <div className="news-categories">
            {item.categories.map((slug) => (
              <span className="news-tag" key={slug}>
                {categoryLookup[slug]?.label ?? slug}
              </span>
            ))}
          </div>
        ) : null}

        <div className="news-item-why">
          <span className="news-muted news-item-why-label">Why it matters</span>
          <span className="news-item-why-copy">{item.why || "...will generate on next refresh"}</span>
        </div>
      </div>
    </article>
  );
}
