type CoverProps = {
  headline: string;
  italicPhrase: string;
  description: string;
  total: number;
  newCount: number;
};

export function Cover({
  headline,
  italicPhrase,
  description,
  total,
  newCount,
}: CoverProps) {
  return (
    <header className="news-cover">
      <div>
        <h1>
          {headline}
          <br />
          <i>{italicPhrase}</i>
        </h1>
        <p>{description}</p>
      </div>
      <div className="news-cover-stats" aria-label="Feed totals">
        <div className="news-cover-stat">
          <div className="news-cover-stat-label">Tracked</div>
          <div className="news-cover-stat-value">{total}</div>
        </div>
        <div className="news-cover-stat">
          <div className="news-cover-stat-label">New</div>
          <div className="news-cover-stat-value">{newCount}</div>
        </div>
      </div>
    </header>
  );
}
