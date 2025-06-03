import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Financial Document Analysis System | FDAS',
  description: 'Professional AI-powered financial document analysis and insights platform',
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
        {children}
      </body>
    </html>
  )
}