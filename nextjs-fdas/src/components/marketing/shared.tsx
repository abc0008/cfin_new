'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  createContext,
  type MutableRefObject,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import { BOOK_DEMO_URL } from '@/lib/app-urls'

type Direction = 'A' | 'B'
type HeroVariant = 'cinematic' | 'split' | 'typographic'

type MarketingSettingsContextType = {
  direction: Direction
  setDirection: (direction: Direction) => void
  heroVariant: HeroVariant
  setHeroVariant: (variant: HeroVariant) => void
}

const MarketingSettingsContext = createContext<MarketingSettingsContextType | null>(null)

const HERO_LAYOUT_OPTIONS: Array<{ id: HeroVariant; label: string }> = [
  { id: 'cinematic', label: 'Cinema' },
  { id: 'split', label: 'Split' },
  { id: 'typographic', label: 'Typo' },
]

export function useMarketingSettings() {
  const context = useContext(MarketingSettingsContext)
  if (!context) {
    throw new Error('useMarketingSettings must be used within MarketingChrome')
  }
  return context
}

export function MarketingChrome({ children }: { children: ReactNode }) {
  const [direction, setDirection] = useState<Direction>('B')
  const [heroVariant, setHeroVariant] = useState<HeroVariant>('cinematic')
  const [settingsLoaded, setSettingsLoaded] = useState(false)

  useEffect(() => {
    const savedDirection = localStorage.getItem('ace.direction')
    const savedHero = localStorage.getItem('ace.heroVariant')
    if (savedDirection === 'A' || savedDirection === 'B') {
      setDirection(savedDirection)
    }
    if (savedHero === 'cinematic' || savedHero === 'split' || savedHero === 'typographic') {
      setHeroVariant(savedHero)
    }
    setSettingsLoaded(true)
  }, [])

  useEffect(() => {
    if (!settingsLoaded) return
    localStorage.setItem('ace.direction', direction)
  }, [direction, settingsLoaded])

  useEffect(() => {
    if (!settingsLoaded) return
    localStorage.setItem('ace.heroVariant', heroVariant)
  }, [heroVariant, settingsLoaded])

  const contextValue = useMemo(
    () => ({
      direction,
      setDirection,
      heroVariant,
      setHeroVariant,
    }),
    [direction, heroVariant],
  )

  return (
    <MarketingSettingsContext.Provider value={contextValue}>
      <div className="ace-marketing" data-direction={direction}>
        <MarketingNav />
        {children}
      </div>
    </MarketingSettingsContext.Provider>
  )
}

export function MarketingNav() {
  const pathname = usePathname()
  const { direction, setDirection, heroVariant, setHeroVariant } = useMarketingSettings()
  const [layoutOpen, setLayoutOpen] = useState(false)
  const layoutRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!layoutOpen) return
    const onPointerDown = (event: MouseEvent) => {
      if (layoutRef.current && !layoutRef.current.contains(event.target as Node)) {
        setLayoutOpen(false)
      }
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [layoutOpen])

  const applyLayout = (variant: HeroVariant) => {
    setHeroVariant(variant)
    setLayoutOpen(false)
  }

  return (
    <nav className="nav">
      <Link href="/" className="brand">
        <span className="mark" />
        <span>Ace Analytics</span>
      </Link>
      <div className="links">
        <Link href="/" aria-current={pathname === '/' ? 'page' : undefined}>
          Home
        </Link>
        <Link href="/product" aria-current={pathname.startsWith('/product') ? 'page' : undefined}>
          Products
        </Link>
        <Link href="/news" aria-current={pathname.startsWith('/news') ? 'page' : undefined}>
          Industry News
        </Link>
        <Link href="/about" aria-current={pathname === '/about' ? 'page' : undefined}>
          About Me
        </Link>
      </div>
      <div className="cta">
        <div className="nav-controls">
          <div className="theme-toggle" role="group" aria-label="Theme mode">
            <button
              type="button"
              className={direction === 'A' ? 'on' : ''}
              onClick={() => setDirection('A')}
              title="Meadow theme"
              aria-label="Switch to Meadow (light)"
            >
              <SunIcon />
            </button>
            <button
              type="button"
              className={direction === 'B' ? 'on' : ''}
              onClick={() => setDirection('B')}
              title="Cove theme"
              aria-label="Switch to Cove (dark)"
            >
              <MoonStarIcon />
            </button>
          </div>
          <div className={`layout-pill${layoutOpen ? ' open' : ''}`} ref={layoutRef}>
            <button
              type="button"
              className="layout-trigger"
              onClick={() => setLayoutOpen((open) => !open)}
              aria-label="Hero layout"
              aria-expanded={layoutOpen}
              aria-haspopup="true"
              title="Hero layout"
            >
              <LayoutIcon />
            </button>
            <div className="layout-options">
              {HERO_LAYOUT_OPTIONS.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={`layout-option${heroVariant === option.id ? ' on' : ''}`}
                  onClick={() => applyLayout(option.id)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </div>
        <span className="nav-pill">
          <span className="live" />
          Status · All systems
        </span>
        <a href={BOOK_DEMO_URL} className="nav-pill filled">
          Book a demo
        </a>
      </div>
    </nav>
  )
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="4.2" fill="currentColor" />
      <path
        d="M12 2.8v2.3M12 18.9v2.3M21.2 12h-2.3M5.1 12H2.8M18.4 5.6l-1.6 1.6M7.2 16.8l-1.6 1.6M18.4 18.4l-1.6-1.6M7.2 7.2 5.6 5.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  )
}

function MoonStarIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M15.9 3.2a8.9 8.9 0 1 0 4.8 15.8A8.2 8.2 0 1 1 15.9 3.2Z"
        fill="currentColor"
      />
      <path
        d="m17.9 5.5.5 1.2 1.2.5-1.2.5-.5 1.2-.5-1.2-1.2-.5 1.2-.5.5-1.2Z"
        fill="currentColor"
      />
    </svg>
  )
}

function LayoutIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3.5" y="4.5" width="17" height="15" rx="2.4" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <path d="M11.7 4.5v15M3.5 10.4h8.2M11.7 14.3h8.8" fill="none" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  )
}

export function Eyebrow({
  op,
  children,
  plain = false,
}: {
  op?: string
  children: ReactNode
  plain?: boolean
}) {
  return (
    <div className={`eyebrow${plain ? ' plain' : ''}`}>
      {op ? <span style={{ color: 'var(--ink-2)' }}>{op}</span> : null}
      {op ? <span style={{ opacity: 0.4 }}>·</span> : null}
      <span>{children}</span>
    </div>
  )
}

export function Ribbon() {
  const tags = [
    'PDF FINANCIAL ANALYSIS',
    'OCR · CREDIT SPREADING',
    'BREAKEVEN + FORECASTING',
    'TEXT-TO-SQL',
    'AUDIT TRAILS',
    'SOC 2 TYPE II',
    'TEN-K / TEN-Q READY',
    'COVENANT TRACKING',
    'WAREHOUSE NATIVE',
    'EXCEL BRIDGE',
    'P50 340MS',
    'HUMAN-IN-THE-LOOP',
  ]
  const palette = [
    'var(--accent)',
    'var(--accent-orange)',
    'var(--accent-2)',
    'var(--accent-olive)',
    'var(--accent-slate)',
  ]
  const doubled = [...tags, ...tags]

  return (
    <div className="ribbon">
      <div className="track">
        {doubled.map((tag, index) => (
          <span
            className="tag"
            key={`${tag}-${index}`}
            style={{ '--tag-dot': palette[index % palette.length] } as React.CSSProperties}
          >
            {tag}
          </span>
        ))}
      </div>
    </div>
  )
}

export function ClosingCTA() {
  return (
    <section className="closing">
      <div className="wrap">
        <div>
          <Eyebrow op="OP_05">Start</Eyebrow>
          <h2 style={{ marginTop: 24 }}>
            Bring your <br />
            filings, warehouses,
            <br />
            <span className="ital" style={{ color: '#7A8579' }}>
              and questions.
            </span>
          </h2>
        </div>
        <div>
          <p>
            Thirty-minute demo. I walk you through each tool on your own data. No sales engineer,
            no slides.
          </p>
          <div className="actions">
            <a className="btn btn-accent" href={BOOK_DEMO_URL}>
              Book a demo <span className="arr" />
            </a>
            <a className="btn btn-ghost" href="mailto:hello@aceanalytics.dev">
              Email me directly
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}

export function MarketingFooter() {
  return (
    <footer className="footer">
      <div className="wrap">
        <div className="mono" style={{ color: 'var(--ink-2)' }}>
          V4.2.0 · FY26Q1 · UPDATED 04.19.26
        </div>
        <div className="mega">
          <span className="ac">Ace</span>
          <span className="an">Analytics</span>
          <span className="dev">.dev</span>
        </div>
        <div className="grid4">
          <div>
            <h4>Built in</h4>
            <ul>
              <li>Birmingham, AL</li>
              <li>33.519°N 86.810°W</li>
              <li>Independent</li>
            </ul>
          </div>
          <div>
            <h4>Product</h4>
            <ul>
              <li>
                <Link href="/product/lattice">Lattice</Link>
              </li>
              <li>
                <Link href="/product/text2sql">Dialect</Link>
              </li>
              <li>
                <Link href="/product/cfin">Aperture</Link>
              </li>
              <li>
                <Link href="/product/credit-spread">Parallax</Link>
              </li>
            </ul>
          </div>
          <div>
            <h4>Company</h4>
            <ul>
              <li>
                <Link href="/about">About</Link>
              </li>
              <li>
                <a href={BOOK_DEMO_URL}>Book a demo</a>
              </li>
              <li>
                <a href="mailto:press@aceanalytics.dev">Press</a>
              </li>
            </ul>
          </div>
          <div>
            <h4>Legal</h4>
            <ul>
              <li>
                <Link href="/legal/privacy">Privacy</Link>
              </li>
              <li>
                <Link href="/legal/terms">Terms</Link>
              </li>
              <li>
                <Link href="/legal/soc2-status">SOC 2 Type II Status</Link>
              </li>
            </ul>
          </div>
        </div>
        <div className="legal">
          <span>© 2026 Ace Analytics · All rights reserved</span>
          <span>● Status · All systems · 99.98% / 90d</span>
        </div>
      </div>
    </footer>
  )
}

export function useReveal(ref: MutableRefObject<HTMLElement | null>) {
  useEffect(() => {
    if (!ref.current) return
    const elements = ref.current.querySelectorAll('[data-reveal]')
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.setAttribute('data-revealed', 'true')
          }
        })
      },
      { threshold: 0.15 },
    )
    elements.forEach((element) => observer.observe(element))
    return () => observer.disconnect()
  }, [ref])
}

export function ProductSubnav() {
  const pathname = usePathname()

  const items = [
    { href: '/product/lattice', label: 'Breakeven + Forecasting', sub: 'Lattice', color: 'var(--accent-2)' },
    { href: '/product/text2sql', label: 'Text2SQL', sub: 'Dialect', color: 'var(--accent-slate)' },
    { href: '/product/cfin', label: 'CFIN Workspace', sub: 'Aperture', color: 'var(--accent)' },
    { href: '/product/credit-spread', label: 'Credit Spreading', sub: 'Parallax', color: 'var(--accent-orange)' },
  ]

  return (
    <div className="pp-subnav">
      <div className="wrap">
        <Link className="pp-back" href="/product">
          <span className="arrow">←</span> All tools
        </Link>
        <div className="pp-tabs">
          {items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`pp-tab${pathname === item.href ? ' on' : ''}`}
              style={{ '--tab-accent': item.color } as React.CSSProperties}
            >
              <span className="l">{item.label}</span>
              <span className="s">{item.sub}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
