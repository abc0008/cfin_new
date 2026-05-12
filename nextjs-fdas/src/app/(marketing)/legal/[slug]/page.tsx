import fs from 'node:fs/promises'
import path from 'node:path'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { MarketingFooter } from '@/components/marketing/shared'

const LEGAL_DOCS = {
  privacy: { title: 'Privacy', filename: 'privacy.md' },
  terms: { title: 'Terms of Use', filename: 'terms.md' },
  'soc2-status': { title: 'SOC 2 Type II Status', filename: 'soc2-status.md' },
} as const

type LegalSlug = keyof typeof LEGAL_DOCS

function isLegalSlug(value: string): value is LegalSlug {
  return value in LEGAL_DOCS
}

async function readLegalMarkdown(slug: LegalSlug): Promise<string> {
  const filePath = path.join(process.cwd(), 'src', 'content', 'legal', LEGAL_DOCS[slug].filename)
  return fs.readFile(filePath, 'utf8')
}

export function generateStaticParams() {
  return Object.keys(LEGAL_DOCS).map((slug) => ({ slug }))
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string }
}): Promise<Metadata> {
  if (!isLegalSlug(params.slug)) {
    return {}
  }

  return {
    title: `${LEGAL_DOCS[params.slug].title} | ACE Analytics`,
  }
}

export default async function LegalPage({ params }: { params: { slug: string } }) {
  if (!isLegalSlug(params.slug)) {
    notFound()
  }

  const markdown = await readLegalMarkdown(params.slug)

  return (
    <>
      <main className="legal-page">
        <section className="wrap legal-wrap">
          <div className="legal-head">
            <div className="eyebrow plain">
              <span>OP_LEGAL</span>
              <span style={{ opacity: 0.4 }}>·</span>
              <span>{LEGAL_DOCS[params.slug].title}</span>
            </div>
            <Link href="/" className="legal-back">
              Back to home
            </Link>
          </div>
          <article className="legal-article">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
          </article>
        </section>
      </main>
      <MarketingFooter />
    </>
  )
}
