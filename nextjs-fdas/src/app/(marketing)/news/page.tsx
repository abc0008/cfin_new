import Link from "next/link";

import { Eyebrow } from "@/components/marketing/shared";
import { fmtRelative, listFeeds } from "@/lib/industry-news";

export const revalidate = 300;

export default async function MarketingNewsIndexPage() {
  let feeds: Awaited<ReturnType<typeof listFeeds>> = [];
  let error: string | null = null;

  try {
    feeds = await listFeeds();
  } catch (caughtError) {
    error = caughtError instanceof Error ? caughtError.message : String(caughtError);
  }

  return (
    <main className="news-page">
      <div className="news-shell">
        <div className="news-header-row">
          <Eyebrow op="OP_00" plain>
            Ace Analytics · News Desk
          </Eyebrow>
          <span className="news-tag">LIVE</span>
        </div>

        <header className="news-cover" style={{ borderBottom: "none", paddingBottom: 0 }}>
          <div>
            <h1>
              The signal,
              <br />
              <i>read between the noise.</i>
            </h1>
            <p>
              A working operator&apos;s news desk for bank-finance and BI. Each feed pulls its source
              on a schedule, filters to the things a regional-bank analyst actually cares about, and
              ships a one-line &quot;why it matters.&quot;
            </p>
          </div>
        </header>

        <section style={{ marginTop: 48 }}>
          <div className="news-header-row">
            <h2 style={{ margin: 0 }}>Feeds</h2>
            <span className="news-muted">{String(feeds.length).padStart(2, "0")} ACTIVE</span>
          </div>

          {error ? <p className="news-error">Feed index unavailable — {error}</p> : null}

          <div className="news-feed-list">
            {feeds.map((feed) => (
              <Link className="news-feed-link" href={`/news/${feed.slug}`} key={feed.slug}>
                <span className="news-feed-tag">{feed.slug}</span>
                <div>
                  <h2>{feed.name}</h2>
                  <p className="news-feed-tagline">{feed.tagline}</p>
                </div>
                <div className="news-feed-meta">
                  <span>{feed.item_count} items</span>
                  <span>
                    {feed.last_refreshed_at
                      ? `Refreshed ${fmtRelative(feed.last_refreshed_at)}`
                      : "Never refreshed"}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
