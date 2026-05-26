import type { Metadata } from 'next'
import './globals.css'

const ICON_VERSION = '20260526d'

export const metadata: Metadata = {
  title: 'ACEAnalytics | AI Project Hub',
  description: 'Launch and manage ACEAnalytics applications for financial analysis and automation.',
  icons: {
    icon: [
      { url: `/favicon.ico?v=${ICON_VERSION}`, type: 'image/x-icon', sizes: 'any' },
      { url: `/icon.png?v=${ICON_VERSION}`, type: 'image/png', sizes: '512x512' },
    ],
    shortcut: [{ url: `/favicon.ico?v=${ICON_VERSION}`, type: 'image/x-icon' }],
    apple: [{ url: `/apple-icon.png?v=${ICON_VERSION}`, sizes: '180x180', type: 'image/png' }],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href={`/favicon.ico?v=${ICON_VERSION}`} sizes="any" />
        <link rel="shortcut icon" href={`/favicon.ico?v=${ICON_VERSION}`} />
        <link rel="apple-touch-icon" href={`/apple-icon.png?v=${ICON_VERSION}`} sizes="180x180" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link 
          href="https://fonts.googleapis.com/css2?family=Avenir:wght@300;400;600;700&display=swap" 
          rel="stylesheet" 
        />
      </head>
      <body className="font-avenir antialiased">
        {children}
      </body>
    </html>
  )
}