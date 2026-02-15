import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'

export const metadata: Metadata = {
  title: 'ACEAnalytics | AI Project Hub',
  description: 'Launch and manage ACEAnalytics applications for financial analysis and automation.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link 
          href="https://fonts.googleapis.com/css2?family=Avenir:wght@300;400;600;700&display=swap" 
          rel="stylesheet" 
        />
      </head>
      <body className="font-avenir antialiased">
        <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-end px-4 py-2">
            <Link
              href="https://aceanalytics.dev"
              className="inline-flex items-center rounded-md border border-border px-3 py-1 text-xs font-avenir-pro-demi text-foreground transition-colors hover:bg-brand-white-smoke"
            >
              Home
            </Link>
          </div>
        </header>
        {children}
      </body>
    </html>
  )
}