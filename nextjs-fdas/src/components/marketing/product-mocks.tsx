'use client'

import { useEffect, useRef, useState } from 'react'
import { EncryptedText } from '@/components/ui/encrypted-text'
import { SqlTerminal } from '@/components/ui/sql-terminal'
import { TypewriterEffect } from '@/components/ui/typewriter-effect'

function Chrome({ url, children }: { url: string; children: React.ReactNode }) {
  return (
    <div className="chrome">
      <div className="bar">
        <div className="tl">
          <span className="d1" />
          <span className="d2" />
          <span className="d3" />
        </div>
        <div className="url">{url}</div>
      </div>
      {children}
    </div>
  )
}

export function ApertureMock({ isActive = true }: { isActive?: boolean } = {}) {
  const items = [
    ['Revenue', '€84.7b'],
    ['Operating income', '€21.0b'],
    ['Gross profit', '€58.3b'],
    ['R&D', '€5.2b'],
    ['CapEx', '€4.8b'],
    ['Cash & equiv.', '€12.1b'],
    ['Net debt / EBITDA', '0.8×'],
    ['FCF margin', '22.4%'],
    ['Effective tax', '24.1%'],
    ['Inventory days', '142'],
  ]

  const width = 560
  const height = 220
  const count = 16
  const values = Array.from(
    { length: count },
    (_, index) => 48 + Math.sin(index * 0.6) * 8 + index * 2.2 + (index % 3 === 0 ? 4 : 0),
  )
  const min = Math.min(...values) - 4
  const max = Math.max(...values) + 4
  const stepX = width / (count - 1)
  const y = (value: number) => height - ((value - min) / (max - min)) * (height - 30) - 15
  const points = values.map((value, index) => [index * stepX, y(value)])
  const line = points.reduce(
    (path, [x, valueY], index) => `${path}${index ? ` L ${x} ${valueY}` : `M ${x} ${valueY}`}`,
    '',
  )
  const area = `${line} L ${width} ${height} L 0 ${height} Z`
  const color = '#263C49'

  return (
    <Chrome url="aperture.ace / lvmh_q4_24.pdf">
      <div className="apr">
        <div className="side">
          <div
            style={{
              color,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              letterSpacing: '0.1em',
            }}
          >
            EXTRACTED · 147 LINE ITEMS
          </div>
          <div className="hr" style={{ margin: '4px 0 8px' }} />
          {items.map(([label, value], index) => (
            <div className="it" key={label}>
              <span className="lbl">{label}</span>
              <span className="val">
                <EncryptedText
                  text={value}
                  revealDelayMs={78}
                  flipDelayMs={56}
                  startDelayMs={index * 130}
                />
              </span>
            </div>
          ))}
        </div>
        <div className="main">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 11,
                color: 'var(--ink-2)',
                letterSpacing: '0.1em',
              }}
            >
              REVENUE · 16Q
            </div>
            <div className="toggles">
              <span>Quarterly</span>
              <span className="on" style={{ background: color, color: '#fff' }}>
                Annual
              </span>
              <span>LTM</span>
            </div>
          </div>
          <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 220 }}>
            {[0.25, 0.5, 0.75].map((ratio, index) => (
              <line
                key={index}
                x1={0}
                x2={width}
                y1={height * ratio}
                y2={height * ratio}
                stroke="currentColor"
                strokeOpacity="0.1"
                strokeDasharray="2 4"
              />
            ))}
            <path d={area} fill={color} fillOpacity="0.14" />
            <path d={line} fill="none" stroke={color} strokeWidth="1.8" />
            {points.map(([x, valueY], index) => (
              <circle key={index} cx={x} cy={valueY} r="2.5" fill={color} opacity={index === points.length - 1 ? 1 : 0.5} />
            ))}
          </svg>
          <div className="stats">
            <div className="s">
              <div className="k">YoY</div>
              <div className="v">+11.2%</div>
              <div className="d" style={{ color }}>
                ↑ vs. +9.1%
              </div>
            </div>
            <div className="s">
              <div className="k">GROSS MARGIN</div>
              <div className="v">68.9%</div>
              <div className="d" style={{ color }}>
                ↑ +60bps
              </div>
            </div>
            <div className="s">
              <div className="k">CONFIDENCE</div>
              <div className="v">99.4%</div>
              <div className="d" style={{ color }}>
                p50 340ms
              </div>
            </div>
          </div>
        </div>
      </div>
    </Chrome>
  )
}

export function ParallaxMock({ isActive = true }: { isActive?: boolean } = {}) {
  const c = '#D95F3D'
  const p = '#2B1D34'
  const docCascadeOpen = isActive
  const docs = [
    ['1041', 'p.1', true],
    ['K-1', 'p.4', false],
    ['BANK', 'p.11', true],
    ['RENT', 'p.22', false],
    ['APPR', 'p.28', true],
    ['TAX', 'p.36', false],
  ] as const

  return (
    <Chrome url="parallax.ace / borrower_pkg_scan_38pg.pdf">
      <div style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: c, letterSpacing: '0.12em' }}>
            OCR · 38 PAGES · 12 FORMS
          </div>
          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: p, letterSpacing: '0.12em' }}>
            ● READY · COMMITTEE
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 8 }}>
          {docs.map(([k, page, highlight], index) => {
            const entryOffsetX = -22 - index * 10
            const entryOffsetY = 7 - index * 0.7
            const entryRotate = -2 + index * 0.2
            return (
              <div
                key={index}
                style={{
                  aspectRatio: '3/4',
                  background: '#F5F2EC',
                  border: '1px solid var(--line)',
                  position: 'relative',
                  padding: 6,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  opacity: docCascadeOpen ? 1 : 0.14,
                  transform: docCascadeOpen
                    ? 'translateX(0px) translateY(0px) rotate(0deg) scale(1)'
                    : `translateX(${entryOffsetX}px) translateY(${entryOffsetY}px) rotate(${entryRotate}deg) scale(0.96)`,
                  zIndex: docCascadeOpen ? 1 : 20 - index,
                  boxShadow: docCascadeOpen ? '0 8px 20px rgba(0, 0, 0, 0.18)' : '0 0 0 rgba(0, 0, 0, 0)',
                  transition:
                    'transform 540ms cubic-bezier(0.2, 0.8, 0.2, 1), opacity 460ms ease, box-shadow 500ms ease',
                  transitionDelay: docCascadeOpen ? `${index * 90}ms` : '0ms',
                  willChange: 'transform, opacity',
                }}
              >
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {[...Array(5)].map((_, j) => (
                  <div key={j} style={{ height: 2, background: '#C9C3B8', width: `${60 + ((j * 7) % 35)}%` }} />
                ))}
              </div>
              {highlight ? (
                <div
                  style={{
                    position: 'absolute',
                    left: 6,
                    right: 6,
                    top: '45%',
                    height: 18,
                    background: c,
                    opacity: 0.18,
                    border: `1px solid ${c}`,
                  }}
                />
              ) : null}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <div
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 9,
                    fontWeight: 600,
                    color: highlight ? c : 'var(--ink)',
                  }}
                >
                  {k}
                </div>
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: 'var(--ink-2)' }}>
                  {page}
                </div>
              </div>
              </div>
            )
          })}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginTop: 4 }}>
          {[
            ['DSCR', '1.42×', 'target 1.25×', true],
            ['LTV', '68%', 'cov. 75%', false],
            ['DEBT/EBITDA', '3.1×', 'cov. 4.0×', false],
            ['FCC', '1.88×', 'healthy', true],
          ].map(([k, v, d, highlight], index) => (
            <div
              key={index}
              style={{
                padding: '10px 12px',
                border: '1px solid var(--line)',
                background: highlight ? `${c}0F` : 'transparent',
                borderLeft: highlight ? `2px solid ${c}` : '1px solid var(--line)',
              }}
            >
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: 'var(--ink-2)', letterSpacing: '0.1em' }}>
                {k}
              </div>
              <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.03em', marginTop: 2, color: highlight ? c : 'var(--ink)' }}>
                {v}
              </div>
              <div style={{ fontSize: 9.5, color: 'var(--ink-2)', fontFamily: 'JetBrains Mono, monospace', marginTop: 2 }}>
                {d}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Chrome>
  )
}

export function LatticeMock({
  isActive = true,
  shouldAnimate = isActive,
}: { isActive?: boolean; shouldAnimate?: boolean } = {}) {
  const width = 640
  const height = 260
  const months = 30
  const breakEvenIndex = 19
  const revenue = Array.from({ length: months }, (_, index) => 40 + index * 6 + Math.sin(index * 0.6) * 5)
  const costLine = 40 + breakEvenIndex * 6
  const stepX = width / (months - 1)
  const min = 30
  const max = Math.max(...revenue, costLine) + 20
  const y = (value: number) => height - ((value - min) / (max - min)) * (height - 40) - 20
  const points = revenue.map((value, index) => [index * stepX, y(value)])
  const line = points.reduce((path, [x, valueY], index) => `${path}${index ? ` L ${x} ${valueY}` : `M ${x} ${valueY}`}`, '')
  const lineAfterBreak = points
    .slice(breakEvenIndex)
    .reduce((path, [x, valueY], index) => `${path}${index ? ` L ${x} ${valueY}` : `M ${x} ${valueY}`}`, '')
  const breakEvenX = breakEvenIndex * stepX
  const breakEvenY = y(revenue[breakEvenIndex])
  const drawDurationSec = 3.1
  const accentBeginSec = drawDurationSec * (breakEvenIndex / (months - 1))
  const color = '#7A8579'
  const baseLineOpacity = shouldAnimate ? 0.05 : 0.2

  return (
    <Chrome url="lattice.ace / runway_proforma.xlsx">
      <div className="ltt">
        <div className="head">
          <div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5, color: 'var(--ink-2)', letterSpacing: '0.1em' }}>
              SCENARIO
            </div>
            <div className="name">Breakeven · Opt 2 of 4 — Month 19</div>
          </div>
          <div className="pill-row">
            <span>BASE</span>
            <span className="on" style={{ background: color, color: '#fff', borderColor: color }}>
              BULL
            </span>
            <span>BEAR</span>
          </div>
        </div>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 260 }}>
          {[0.2, 0.4, 0.6, 0.8].map((ratio, index) => (
            <line
              key={index}
              x1={0}
              x2={width}
              y1={height * ratio}
              y2={height * ratio}
              stroke="currentColor"
              strokeOpacity="0.08"
              strokeDasharray="2 4"
            />
          ))}
          <line x1={0} x2={width} y1={y(costLine)} y2={y(costLine)} stroke="currentColor" strokeWidth="1.2" strokeDasharray="4 3" opacity="0.5" />
          <text x={8} y={y(costLine) - 6} fontFamily="JetBrains Mono, monospace" fontSize="10" fill="currentColor" opacity="0.6">
            FIXED COST · $154k/mo
          </text>
          <path d={line} fill="none" stroke="currentColor" strokeWidth="2" opacity={baseLineOpacity} />
          <path
            d={line}
            fill="none"
            stroke="currentColor"
            strokeWidth="2.1"
            pathLength={100}
            strokeDasharray={100}
            strokeDashoffset={100}
            opacity="0.7"
          >
            {shouldAnimate ? (
              <animate
                attributeName="stroke-dashoffset"
                from="100"
                to="0"
                dur={`${drawDurationSec}s`}
                begin="0s"
                fill="freeze"
              />
            ) : null}
          </path>
          <path
            d={lineAfterBreak}
            fill="none"
            stroke={color}
            strokeWidth="4.8"
            strokeLinecap="round"
            pathLength={100}
            strokeDasharray={100}
            strokeDashoffset={100}
            opacity="0"
          >
            {shouldAnimate ? (
              <>
                <animate
                  attributeName="opacity"
                  values="0;0.34"
                  dur="0.01s"
                  begin={`${accentBeginSec}s`}
                  fill="freeze"
                />
                <animate
                  attributeName="stroke-dashoffset"
                  from="100"
                  to="0"
                  dur={`${Math.max(0.45, drawDurationSec - accentBeginSec)}s`}
                  begin={`${accentBeginSec}s`}
                  fill="freeze"
                />
              </>
            ) : null}
          </path>
          <path
            d={lineAfterBreak}
            fill="none"
            stroke={color}
            strokeWidth="2.85"
            strokeLinecap="round"
            pathLength={100}
            strokeDasharray={100}
            strokeDashoffset={100}
            opacity="0"
          >
            {shouldAnimate ? (
              <>
                <animate
                  attributeName="opacity"
                  values="0;0.98"
                  dur="0.01s"
                  begin={`${accentBeginSec}s`}
                  fill="freeze"
                />
                <animate
                  attributeName="stroke-dashoffset"
                  from="100"
                  to="0"
                  dur={`${Math.max(0.45, drawDurationSec - accentBeginSec)}s`}
                  begin={`${accentBeginSec}s`}
                  fill="freeze"
                />
              </>
            ) : null}
          </path>
          <line x1={breakEvenX} x2={breakEvenX} y1={0} y2={height} stroke={color} strokeWidth="1" strokeDasharray="3 3" opacity="0.55" />
          <circle cx={breakEvenX} cy={breakEvenY} r="14" fill="none" stroke={color} strokeWidth="1" opacity="0.05">
            {shouldAnimate ? <animate attributeName="r" values="14;24;14" dur="1.4s" repeatCount="indefinite" /> : null}
            {shouldAnimate ? <animate attributeName="opacity" values="0.38;0.06;0.38" dur="1.4s" repeatCount="indefinite" /> : null}
          </circle>
          <circle cx={breakEvenX} cy={breakEvenY} r="14" fill="none" stroke={color} strokeWidth="1" opacity="0">
            {shouldAnimate ? <animate attributeName="r" values="14;22;14" dur="1.4s" begin="0.68s" repeatCount="indefinite" /> : null}
            {shouldAnimate ? <animate attributeName="opacity" values="0.3;0.04;0.3" dur="1.4s" begin="0.68s" repeatCount="indefinite" /> : null}
          </circle>
          <circle cx={breakEvenX} cy={breakEvenY} r="9" fill="none" stroke={color} strokeWidth="1.8" opacity="0.7">
            {shouldAnimate ? <animate attributeName="r" values="9;13;9" dur="1.4s" repeatCount="indefinite" /> : null}
            {shouldAnimate ? <animate attributeName="opacity" values="0.95;0.45;0.95" dur="1.4s" repeatCount="indefinite" /> : null}
          </circle>
          <circle cx={breakEvenX} cy={breakEvenY} r="4.8" fill={color} />
          <text x={breakEvenX + 16} y={breakEvenY - 12} fontFamily="JetBrains Mono, monospace" fontSize="11" fill={color} fontWeight="600">
            BE · M19
          </text>
        </svg>
      </div>
    </Chrome>
  )
}

export function DialectMock({
  isActive = true,
  shouldAnimate = isActive,
}: { isActive?: boolean; shouldAnimate?: boolean } = {}) {
  const prompt = `"Which clients had the largest revenue drop in Q4 vs. Q3, excluding their seasonal categories?"`
  const query = `SELECT
  c.client_id,
  c.name,
  SUM(q4.revenue) - SUM(q3.revenue) AS delta
FROM clients c
JOIN quarterly_revenue q4
  ON q4.client_id = c.id AND q4.period = '2025-Q4'
JOIN quarterly_revenue q3
  ON q3.client_id = c.id AND q3.period = '2025-Q3'
WHERE q4.category NOT IN ('seasonal', 'holiday')
GROUP BY c.client_id, c.name
HAVING delta < 0
ORDER BY delta ASC
LIMIT 14;`
  const [terminalRun, setTerminalRun] = useState(false)
  const [statsRun, setStatsRun] = useState(false)
  const promptKickoffTimeoutRef = useRef<number | null>(null)

  useEffect(() => {
    if (promptKickoffTimeoutRef.current !== null) {
      window.clearTimeout(promptKickoffTimeoutRef.current)
      promptKickoffTimeoutRef.current = null
    }

    if (!shouldAnimate) {
      setTerminalRun(false)
      setStatsRun(false)
      return
    }

    setTerminalRun(false)
    setStatsRun(false)
  }, [shouldAnimate])

  useEffect(() => {
    return () => {
      if (promptKickoffTimeoutRef.current !== null) {
        window.clearTimeout(promptKickoffTimeoutRef.current)
      }
    }
  }, [])

  const handlePromptComplete = () => {
    if (!shouldAnimate) return

    if (promptKickoffTimeoutRef.current !== null) {
      window.clearTimeout(promptKickoffTimeoutRef.current)
    }

    promptKickoffTimeoutRef.current = window.setTimeout(() => {
      setTerminalRun(true)
      promptKickoffTimeoutRef.current = null
    }, 500)
  }

  const handleTerminalComplete = () => {
    if (!shouldAnimate) return
    setStatsRun(true)
  }

  return (
    <Chrome url="dialect.ace / warehouse · snowflake-prod">
      <div className="dlct">
        <div className="prompt-pill">
          <TypewriterEffect
            text={prompt}
            run={shouldAnimate}
            typingSpeedMs={48}
            className="prompt-typewriter"
            ghostClassName="prompt-typewriter-ghost"
            liveClassName="prompt-typewriter-live"
            cursorClassName="prompt-typewriter-cursor"
            onComplete={handlePromptComplete}
          />
        </div>
        <div className={`meta${statsRun ? ' on' : ''}`}>
          generated · 340ms · <span className="meta-validated">validated</span>
        </div>
        <SqlTerminal
          text={query}
          typingSpeedMs={100}
          startDelayMs={0}
          loop={false}
          run={terminalRun}
          heightPx={292}
          onComplete={handleTerminalComplete}
        />
        <div className="stats">
          <div>
            ROWS RETURNED ·{' '}
            <b>
              <EncryptedText text="14" revealDelayMs={80} flipDelayMs={60} trigger={statsRun} />
            </b>
          </div>
          <div>
            TOTAL DELTA ·{' '}
            <b>
              <EncryptedText text="$4.82M ARR" revealDelayMs={80} flipDelayMs={60} trigger={statsRun} />
            </b>
          </div>
          <div>
            EXEC ·{' '}
            <b>
              <EncryptedText text="p50 340ms" revealDelayMs={80} flipDelayMs={60} trigger={statsRun} />
            </b>
          </div>
        </div>
      </div>
    </Chrome>
  )
}
