'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { BarChart2, FileText, Home, MoonStar, Sun } from 'lucide-react'
import { BOOK_DEMO_URL } from '@/lib/app-urls'

type Direction = 'A' | 'B'

export default function Header() {
  const pathname = usePathname()
  const [direction, setDirection] = useState<Direction>('A')

  useEffect(() => {
    const storedDirection = localStorage.getItem('ace.direction')
    setDirection(storedDirection === 'B' ? 'B' : 'A')
  }, [])

  const applyDirection = (nextDirection: Direction) => {
    setDirection(nextDirection)
    localStorage.setItem('ace.direction', nextDirection)
    window.dispatchEvent(
      new CustomEvent('ace-direction-change', {
        detail: { direction: nextDirection },
      }),
    )
  }

  return (
    <header className="workspace-header">
      <div className="workspace-header-wrap">
        <Link href="/" className="workspace-brand">
          <span className="workspace-brand-mark" />
          <span className="workspace-brand-copy">
            <span className="workspace-brand-title">Ace Analytics</span>
            <span className="workspace-brand-sub">Aperture Workspace</span>
          </span>
        </Link>

        <nav className="workspace-nav">
          <Link href="/" className={`workspace-nav-link ${pathname === '/' ? 'on' : ''}`}>
            <Home className="h-4 w-4" />
            Home
          </Link>
          <Link
            href="/dashboard"
            className={`workspace-nav-link ${pathname === '/dashboard' ? 'on' : ''}`}
          >
            <BarChart2 className="h-4 w-4" />
            Dashboard
          </Link>
          <Link
            href="/workspace"
            className={`workspace-nav-link ${pathname === '/workspace' ? 'on' : ''}`}
          >
            <FileText className="h-4 w-4" />
            Workspace
          </Link>
        </nav>

        <div className="workspace-header-controls">
          <div className="workspace-theme-toggle" role="group" aria-label="Theme mode">
            <button
              type="button"
              onClick={() => applyDirection('A')}
              className={direction === 'A' ? 'on' : ''}
              title="Aperture light mode"
              aria-label="Switch to light mode"
            >
              <Sun className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => applyDirection('B')}
              className={direction === 'B' ? 'on' : ''}
              title="Aperture dark mode"
              aria-label="Switch to dark mode"
            >
              <MoonStar className="h-4 w-4" />
            </button>
          </div>

          <Link href="/product/cfin" className="workspace-header-pill">
            OP_APRT
          </Link>
          <a href={BOOK_DEMO_URL} className="workspace-header-pill filled">
            Book Demo
          </a>
        </div>
      </div>
    </header>
  )
}