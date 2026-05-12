'use client'

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import { MarketPanel } from '@/components/marketing/market-panel'
import { ApertureMock, DialectMock, LatticeMock, ParallaxMock } from '@/components/marketing/product-mocks'
import { EncryptedText } from '@/components/ui/encrypted-text'
import { BOOK_DEMO_URL } from '@/lib/app-urls'
import {
  ClosingCTA,
  Eyebrow,
  MarketingFooter,
  Ribbon,
  useMarketingSettings,
  useReveal,
} from '@/components/marketing/shared'

export const PROTOTYPE_TOOLS = [
  {
    op: 'OP_A1',
    code: 'LTTC',
    name: 'Lattice',
    tag: 'Breakeven + Forecasting',
    color: 'var(--accent-2)',
    desc: 'Model revenue curves, fixed and variable cost, and CAC payback. Flip between BASE, BULL, BEAR. Find the month you cross the line - and what it takes to move it left.',
    route: '/product/lattice',
    methodsRoute: '/product/lattice#methods',
    mock: (isActive?: boolean, shouldAnimate?: boolean) => (
      <LatticeMock isActive={isActive} shouldAnimate={shouldAnimate} />
    ),
  },
  {
    op: 'OP_A2',
    code: 'DLCT',
    name: 'Dialect',
    tag: 'Text-to-SQL for banks',
    color: 'var(--accent-olive)',
    desc: 'Ask a question in plain English. Get calibrated SQL against your warehouse - no prompt engineering. Fine-tuned on bank schemas, validated by the planner before anyone sees a row.',
    route: '/product/text2sql',
    methodsRoute: '/product/text2sql#methods',
    mock: (isActive?: boolean, shouldAnimate?: boolean) => (
      <DialectMock isActive={isActive} shouldAnimate={shouldAnimate} />
    ),
  },
  {
    op: 'OP_A3',
    code: 'APRT',
    name: 'Aperture',
    tag: 'PDF Financial Analysis',
    color: 'var(--accent-slate)',
    desc: 'Upload a 10-K, 10-Q, or S-1. Get a line-item model with OHLC-quality charts, in seconds. Confidence-scored, audit-logged, and tied back to the source page.',
    route: '/product/cfin',
    methodsRoute: '/product/cfin#methods',
    mock: (isActive?: boolean, _shouldAnimate?: boolean) => <ApertureMock isActive={isActive} />,
  },
  {
    op: 'OP_A4',
    code: 'PRLX',
    name: 'Parallax',
    tag: 'OCR · Credit Spreading',
    color: 'var(--accent-orange)',
    desc: "Drop a scanned borrower package - tax returns, K-1s, bank statements. Get a clean, committee-ready credit spread with covenants, DSCR, and a sensitivity table. OCR that reads handwriting and stamps.",
    route: '/product/credit-spread',
    methodsRoute: '/product/credit-spread#methods',
    mock: (isActive?: boolean, _shouldAnimate?: boolean) => <ParallaxMock isActive={isActive} />,
  },
]

export function HomePrototypePage() {
  const wrapRef = useRef<HTMLDivElement | null>(null)
  const { heroVariant } = useMarketingSettings()
  useReveal(wrapRef)

  return (
    <div className="route" ref={wrapRef} key={`home-${heroVariant}`}>
      {heroVariant === 'cinematic' ? <HeroCinematic /> : null}
      {heroVariant === 'split' ? <HeroSplit /> : null}
      {heroVariant === 'typographic' ? <HeroTypographic /> : null}
      <Ribbon />
      <ToolMorpher />
      <Philosophy />
      <NumbersStrip />
      <ClosingCTA />
      <MarketingFooter />
    </div>
  )
}

function HeroCinematic() {
  const heroRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const onScroll = () => {
      if (!heroRef.current) return
      const h = window.innerHeight
      const y = Math.min(window.scrollY, h * 0.85) / (h * 0.85)
      const scale = 1 - y * 0.06
      const translateY = -y * 40
      const opacity = 1 - y
      heroRef.current.style.transform = `translateY(${translateY}px) scale(${scale})`
      heroRef.current.style.opacity = `${opacity}`
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <section style={{ height: '100vh', position: 'sticky', top: 0, overflow: 'hidden' }}>
      <div
        ref={heroRef}
        style={{
          height: '100vh',
          display: 'flex',
          alignItems: 'center',
          willChange: 'transform, opacity',
        }}
      >
        <div className="wrap" style={{ width: '100%' }}>
          <div className="grid-2">
            <div>
              <Eyebrow op="OP_01">Financial intelligence · engineered</Eyebrow>
              <h1 className="display h1 hero-main-title" style={{ marginTop: 36 }}>
                Read between{' '}
                <span className="ital" style={{ color: 'var(--accent-orange)' }}>
                  the numbers.
                </span>
              </h1>
              <p className="lede hero-main-lede" style={{ marginTop: 36 }}>
                Four focused AI tools for financial analysts. Scenario to breakeven, natural
                language to SQL, filings to model, and borrower packages to credit spread. Calibrated on
                real filings, audited end to end.
              </p>
              <div style={{ display: 'flex', gap: 12, marginTop: 40, flexWrap: 'wrap' }}>
                <a className="btn btn-ink" href={BOOK_DEMO_URL}>
                  Book a demo <span className="arr" />
                </a>
                <Link className="btn btn-ghost" href="/product">
                  See the tools
                </Link>
              </div>
            </div>
            <div>
              <MarketPanel />
            </div>
          </div>
        </div>
      </div>
      <div className="scroll-hint">
        <span className="dash" /> Scroll to enter
      </div>
    </section>
  )
}

function HeroSplit() {
  return (
    <section className="hero-split">
      <div className="l">
        <div>
          <Eyebrow op="OP_01">Financial intelligence · engineered</Eyebrow>
          <h1 className="display h1 hero-main-title" style={{ marginTop: 28 }}>
            Read between{' '}
            <span className="ital" style={{ color: 'var(--accent-orange)' }}>
              the numbers.
            </span>
          </h1>
          <p className="lede hero-main-lede" style={{ marginTop: 28 }}>
            Four focused AI tools for financial analysts. Scenario to breakeven, natural language
            to SQL, filings to model, and scans to credit spread.
          </p>
          <div style={{ display: 'flex', gap: 12, marginTop: 32, flexWrap: 'wrap' }}>
            <a className="btn btn-ink" href={BOOK_DEMO_URL}>
              Book a demo <span className="arr" />
            </a>
            <Link className="btn btn-ghost" href="/product">
              See the tools
            </Link>
          </div>
        </div>
      </div>
      <div className="r">
        <MarketPanel />
      </div>
    </section>
  )
}

function HeroTypographic() {
  return (
    <section style={{ padding: '120px 0 80px' }}>
      <div className="wrap">
        <Eyebrow op="OP_01">Financial intelligence · engineered</Eyebrow>
        <h1 className="hero-typo" style={{ marginTop: 40 }}>
          <div className="big">Read between</div>
          <div className="big ital" style={{ color: 'var(--accent-orange)' }}>
            the numbers.
          </div>
        </h1>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1.2fr 1fr',
            gap: 48,
            marginTop: 60,
            alignItems: 'end',
          }}
        >
          <p className="lede" style={{ maxWidth: 600 }}>
            Four focused AI tools for financial analysts. Scenario to breakeven, natural language
            to SQL, filings to model, and scans to credit spread. Calibrated on real filings,
            audited end to end.
          </p>
          <div style={{ display: 'flex', gap: 12 }}>
            <a className="btn btn-ink" href={BOOK_DEMO_URL}>
              Book a demo <span className="arr" />
            </a>
            <Link className="btn btn-ghost" href="/product">
              See the tools
            </Link>
          </div>
        </div>
        <div style={{ marginTop: 64 }}>
          <MarketPanel />
        </div>
      </div>
    </section>
  )
}

function ToolMorpher() {
  const TAB_INDICATOR_TRANSITION_MS = 400
  const LATTICE_ANIMATION_OFFSET_MS = 40
  const wrapRef = useRef<HTMLDivElement | null>(null)
  const [active, setActive] = useState(0)
  const [activeSegmentProgress, setActiveSegmentProgress] = useState(0)
  const [tabIndicatorSettled, setTabIndicatorSettled] = useState(false)

  useEffect(() => {
    const onScroll = () => {
      if (!wrapRef.current) return
      const rect = wrapRef.current.getBoundingClientRect()
      const total = wrapRef.current.offsetHeight - window.innerHeight
      const progress = Math.max(0, Math.min(1, -rect.top / total))
      const raw = progress * PROTOTYPE_TOOLS.length
      const idx = Math.min(PROTOTYPE_TOOLS.length - 1, Math.floor(raw))
      const localProgress = Math.max(0, Math.min(1, raw - idx))
      setActive(idx)
      setActiveSegmentProgress(localProgress)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    setTabIndicatorSettled(false)
    const timeoutId = window.setTimeout(() => {
      setTabIndicatorSettled(true)
    }, TAB_INDICATOR_TRANSITION_MS + LATTICE_ANIMATION_OFFSET_MS)

    return () => window.clearTimeout(timeoutId)
  }, [active])

  return (
    <div className="tool-pin" ref={wrapRef}>
      <div className="stick">
        <div className="wrap" style={{ width: '100%' }}>
          <div className="content">
            <div>
              <div className="tabs">
                {PROTOTYPE_TOOLS.map((_, index) => (
                  <span key={index} className={`t${index === active ? ' on' : ''}`} />
                ))}
              </div>
              {PROTOTYPE_TOOLS.map((tool, index) => (
                <div
                  key={tool.code}
                  className="slide"
                  style={{
                    position: index === active ? 'relative' : 'absolute',
                    opacity: index === active ? 1 : 0,
                    transform: index === active ? 'translateY(0)' : 'translateY(20px)',
                    pointerEvents: index === active ? 'auto' : 'none',
                    maxWidth: 560,
                  }}
                >
                  <Eyebrow op={tool.op}>{tool.tag}</Eyebrow>
                  <div className="tool-name" style={{ marginTop: 28, color: tool.color }}>
                    {tool.name}
                  </div>
                  <p className="tool-desc">{tool.desc}</p>
                  <div className="actions">
                    <Link
                      className="btn btn-tool"
                      style={{ '--tool-accent': tool.color } as React.CSSProperties}
                      href={tool.route}
                    >
                      See {tool.name} <span className="arr" />
                    </Link>
                    <Link className="btn btn-ghost" href={tool.methodsRoute}>
                      Read the methods
                    </Link>
                  </div>
                </div>
              ))}
            </div>
            <div style={{ position: 'relative', minHeight: 420 }}>
              {PROTOTYPE_TOOLS.map((tool, index) => (
                <div
                  key={tool.code}
                  className="slide"
                  style={{
                    position: 'absolute',
                    inset: 0,
                    opacity: index === active ? 1 : 0,
                    transform: index === active ? 'translateY(0) scale(1)' : 'translateY(20px) scale(0.97)',
                    pointerEvents: index === active ? 'auto' : 'none',
                  }}
                >
                  {tool.mock(
                    index === active,
                    index === active &&
                      activeSegmentProgress >= 0.35 &&
                      (tool.code !== 'LTTC' || tabIndicatorSettled),
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Philosophy() {
  const wrapRef = useRef<HTMLDivElement | null>(null)
  const [active, setActive] = useState(0)

  useEffect(() => {
    const onScroll = () => {
      if (!wrapRef.current) return
      const rect = wrapRef.current.getBoundingClientRect()
      const total = wrapRef.current.offsetHeight - window.innerHeight
      const progress = Math.max(0, Math.min(1, -rect.top / total))
      setActive(progress < 0.33 ? 0 : progress < 0.66 ? 1 : 2)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const items = [
    {
      ix: '01',
      title: 'Tools.',
      body: 'Not a platform. Not a suite. Four tools, each doing one job at a level a senior analyst would accept.',
      color: 'var(--accent-slate)',
      panel: <PhilArtScalpel />,
    },
    {
      ix: '02',
      title: 'Calibrated.',
      body: 'Every answer is scored against a known-good benchmark of 120 filings and 6,400 queries. No hallucinated metrics. No silent failures.',
      color: 'var(--accent-olive)',
      panel: <PhilArtCalibrate />,
    },
    {
      ix: '03',
      title: 'Auditable.',
      body: 'Every output ties back to a page, a cell, a row. Every query ships with its plan and its validation trace. You can hand it to audit, unedited.',
      color: 'var(--accent-plum)',
      panel: <PhilArtAudit />,
    },
  ]

  const activeItem = items[active]

  return (
    <div className="philosophy-pin" ref={wrapRef}>
      <div className="stick">
        <div className="wrap" style={{ width: '100%' }}>
          <div className="phil-split">
            <div className="phil-left">
              <Eyebrow op="OP_03">Philosophy</Eyebrow>
              <div className="items" style={{ marginTop: 40 }}>
                {items.map((item, index) => (
                  <div key={item.ix} className={`item${index === active ? ' active' : ''}`}>
                    <div className="ix" style={{ color: item.color }}>
                      {item.ix}
                    </div>
                    <div>
                      <h3>{item.title}</h3>
                      <p>{item.body}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="phil-right" style={{ background: activeItem.color }}>
              <div className="phil-art-label">
                <span className="n">
                  {activeItem.ix} / 03
                </span>
                <span className="t">{activeItem.title.replace('.', '')}</span>
              </div>
              {items.map((item, index) => (
                <div key={item.ix} className="phil-art" style={{ opacity: index === active ? 1 : 0 }}>
                  {item.panel}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="progress">
        {[0, 1, 2].map((index) => (
          <span key={index} className={index <= active ? 'on' : ''} />
        ))}
      </div>
    </div>
  )
}

function PhilArtScalpel() {
  return (
    <svg viewBox="0 0 600 700" preserveAspectRatio="xMidYMid slice" style={{ width: '100%', height: '100%' }}>
      <defs>
        <pattern id="phil-grid-1" width="28" height="28" patternUnits="userSpaceOnUse">
          <path d="M 28 0 L 0 0 0 28" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="0.6" />
        </pattern>
      </defs>
      <rect width="600" height="700" fill="url(#phil-grid-1)" />
      {[
        { x: 90, y: 120, w: 56, h: 440, fill: '#FFAC03', label: 'APRT' },
        { x: 186, y: 180, w: 56, h: 380, fill: '#D95F3D', label: 'PRLX' },
        { x: 282, y: 240, w: 56, h: 320, fill: '#7A8579', label: 'LTTC' },
        { x: 378, y: 300, w: 56, h: 260, fill: '#EBEBEB', label: 'DLCT' },
      ].map((bar, index) => (
        <g key={index}>
          <rect x={bar.x} y={bar.y} width={bar.w} height={bar.h} fill={bar.fill} opacity="0.92" />
          <text
            x={bar.x + bar.w / 2}
            y={bar.y + bar.h + 24}
            fill="rgba(255,255,255,0.7)"
            fontSize="11"
            fontFamily="JetBrains Mono, monospace"
            letterSpacing="0.14em"
            textAnchor="middle"
          >
            {bar.label}
          </text>
          <circle cx={bar.x + bar.w / 2} cy={bar.y - 14} r="3" fill={bar.fill} />
        </g>
      ))}
      <line x1="60" y1="600" x2="540" y2="600" stroke="rgba(255,255,255,0.3)" strokeWidth="1" strokeDasharray="2 4" />
      <text x="60" y="660" fontFamily="JetBrains Mono, monospace" fontSize="10" fill="rgba(255,255,255,0.45)" letterSpacing="0.2em">
        ONE JOB · ONE TOOL
      </text>
    </svg>
  )
}

function PhilArtCalibrate() {
  const cells = []
  for (let row = 0; row < 14; row += 1) {
    for (let col = 0; col < 12; col += 1) {
      cells.push([col, row])
    }
  }
  const cx = 6
  const cy = 7
  return (
    <svg viewBox="0 0 600 700" preserveAspectRatio="xMidYMid slice" style={{ width: '100%', height: '100%' }}>
      <g transform="translate(40, 40)">
        {cells.map(([col, row], index) => {
          const d = Math.hypot(col - cx, row - cy)
          const confidence = Math.max(0, 1 - d / 8)
          const hit = d < 2.5
          return (
            <g key={index}>
              <rect
                x={col * 44}
                y={row * 44}
                width="34"
                height="34"
                fill={hit ? '#FFAC03' : 'rgba(255,255,255,0.12)'}
                opacity={0.15 + confidence * 0.75}
              />
              {hit ? <circle cx={col * 44 + 17} cy={row * 44 + 17} r="2" fill="#111" /> : null}
            </g>
          )
        })}
      </g>
      <circle cx={40 + cx * 44 + 17} cy={40 + cy * 44 + 17} r="70" fill="none" stroke="#FFAC03" strokeWidth="1.5" opacity="0.9" />
      <circle
        cx={40 + cx * 44 + 17}
        cy={40 + cy * 44 + 17}
        r="110"
        fill="none"
        stroke="rgba(255,255,255,0.3)"
        strokeWidth="1"
        strokeDasharray="4 6"
      />
      <text x="40" y="660" fontFamily="JetBrains Mono, monospace" fontSize="10" fill="rgba(255,255,255,0.55)" letterSpacing="0.2em">
        P · 99.4% · N · 6,400
      </text>
    </svg>
  )
}

function PhilArtAudit() {
  return (
    <svg viewBox="0 0 600 700" preserveAspectRatio="xMidYMid slice" style={{ width: '100%', height: '100%' }}>
      {[0, 1, 2, 3, 4].map((index) => (
        <g key={index} transform={`translate(${60 + index * 6}, ${90 + index * 8})`}>
          <rect width="240" height="340" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.35)" strokeWidth="1" />
          {[...Array(10)].map((_, j) => (
            <rect key={j} x="20" y={30 + j * 28} width={180 - ((j % 3) * 30)} height="4" fill="rgba(255,255,255,0.18)" />
          ))}
        </g>
      ))}
      <rect x={60 + 4 * 6 + 20} y={90 + 4 * 8 + 170} width="180" height="16" fill="#FFAC03" opacity="0.85" />
      <path
        d={`M ${60 + 4 * 6 + 200} ${90 + 4 * 8 + 178} C 400 180, 420 420, 500 440`}
        fill="none"
        stroke="#FFAC03"
        strokeWidth="1.5"
        strokeDasharray="3 4"
      />
      <g transform="translate(440, 400)">
        <rect width="130" height="90" fill="rgba(255,255,255,0.12)" stroke="#FFAC03" strokeWidth="2" />
        <text x="12" y="22" fontFamily="JetBrains Mono, monospace" fontSize="9" fill="rgba(255,255,255,0.55)" letterSpacing="0.12em">
          B14 · REVENUE_FY
        </text>
        <text x="12" y="60" fontFamily="Inter Tight, sans-serif" fontSize="28" fontWeight="600" fill="#FFAC03" letterSpacing="-0.02em">
          €84.7b
        </text>
      </g>
      <text x="60" y="660" fontFamily="JetBrains Mono, monospace" fontSize="10" fill="rgba(255,255,255,0.55)" letterSpacing="0.2em">
        PAGE · CELL · ROW · BOUNDING BOX
      </text>
    </svg>
  )
}

function NumbersStrip() {
  const metrics = [
    {
      value: '99.4%',
      color: '#FFAC03',
      revealDelayMs: 82,
      desc: 'Benchmark confidence on line-item extraction.',
      cap: 'Measured vs. 120 filings · manual analyst baseline',
    },
    {
      value: '47×',
      color: '#7A8579',
      revealDelayMs: 82,
      desc: 'Faster than an analyst hand-keying a filing into Excel.',
      cap: 'p50 340ms · p99 1.2s · end to end',
    },
    {
      value: '0',
      color: '#D95F3D',
      revealDelayMs: 170,
      desc: 'Hallucinated metrics shipped to production.',
      cap: 'Validation pass required · 18 months in the wild',
    },
  ] as const

  return (
    <section className="numbers">
      <div className="wrap grid3">
        {metrics.map((metric) => (
          <div key={metric.value} className="metric">
            <div className="n" style={{ color: metric.color }}>
              <EncryptedText
                text={metric.value}
                revealDelayMs={metric.revealDelayMs}
                flipDelayMs={60}
              />
            </div>
            <div className="desc">{metric.desc}</div>
            <div className="cap">{metric.cap}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
