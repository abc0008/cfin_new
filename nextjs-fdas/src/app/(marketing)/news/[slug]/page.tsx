import { notFound } from "next/navigation";

import { FeedView } from "@/components/marketing/news";
import { getFeed } from "@/lib/industry-news";

export const revalidate = 300;

type FeedPageProps = {
  params: {
    slug: string;
  };
};

export default async function MarketingFeedPage({ params }: FeedPageProps) {
  try {
    const payload = await getFeed(params.slug);
    return <FeedView initial={payload} />;
  } catch {
    notFound();
  }
}

export async function generateMetadata({ params }: FeedPageProps) {
  return {
    title: `${params.slug} · Ace Analytics News`,
  };
}
