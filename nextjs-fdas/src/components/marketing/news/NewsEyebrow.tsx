import { isoWeek } from "@/lib/industry-news";

type NewsEyebrowProps = {
  opCode: string;
  feedName: string;
  status?: "Live" | "Cached";
};

export function NewsEyebrow({
  opCode,
  feedName,
  status = "Live",
}: NewsEyebrowProps) {
  const week = String(isoWeek(new Date())).padStart(2, "0");

  return (
    <div className="news-header-row">
      <div className="eyebrow">
        <span>{opCode}</span>
        <span style={{ opacity: 0.45 }}>·</span>
        <span>{feedName} Tracker</span>
        <span style={{ opacity: 0.45 }}>·</span>
        <span>{status}</span>
      </div>
      <span className="news-tag">WK {week}</span>
    </div>
  );
}
