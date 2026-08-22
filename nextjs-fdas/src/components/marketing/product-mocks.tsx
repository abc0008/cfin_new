'use client'

import { type CSSProperties, useEffect, useRef, useState } from 'react'
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

export function PeerLensMock({ isActive = true }: { isActive?: boolean } = {}) {
  void isActive
  const teal = 'var(--accent-teal)'
  const glow = 'rgba(19, 168, 168, 0.22)'
  const rows: Array<{ k: string; v: string; pct: number; pos: number }> = [
    { k: 'ROA', v: '0.54%', pct: 0, pos: 8 },
    { k: 'Efficiency', v: '83.2%', pct: 100, pos: 94 },
    { k: 'NIM', v: '4.00%', pct: 73, pos: 70 },
    { k: 'ROTCE', v: '11.4%', pct: 18, pos: 22 },
    { k: 'CET1', v: '11.5%', pct: 18, pos: 22 },
  ]

  return (
    <Chrome url="peeranalysis.ace / Arvest Bank vs 11 peers">
      <div style={{ padding: '14px 16px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 8,
          }}
        >
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              letterSpacing: '0.1em',
              color: 'var(--ink-2)',
            }}
          >
            PEER PERCENTILE · 12 BANKS · FDIC
          </span>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              color: teal,
            }}
          >
            <span style={{ width: 3, height: 12, background: teal, borderRadius: 1 }} /> ARVEST
          </span>
        </div>
        {rows.map((r) => (
          <div
            key={r.k}
            style={{
              display: 'grid',
              gridTemplateColumns: '76px 1fr 50px',
              gap: 12,
              alignItems: 'center',
              padding: '9px 0',
              borderTop: '1px solid var(--line)',
            }}
          >
            <div style={{ fontSize: 12.5, fontWeight: 600 }}>{r.k}</div>
            <div style={{ position: 'relative', height: 18 }}>
              <span
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: 0,
                  right: 0,
                  height: 5,
                  transform: 'translateY(-50%)',
                  borderRadius: 999,
                  background: 'color-mix(in srgb, currentColor 10%, transparent)',
                }}
              />
              <span
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: '15%',
                  width: '70%',
                  height: 5,
                  transform: 'translateY(-50%)',
                  borderRadius: 999,
                  background: 'color-mix(in srgb, currentColor 20%, transparent)',
                }}
              />
              <span
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  width: 2,
                  height: 13,
                  transform: 'translate(-50%, -50%)',
                  borderRadius: 1,
                  background: 'color-mix(in srgb, currentColor 55%, transparent)',
                }}
              />
              <span
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: `${r.pos}%`,
                  width: 4,
                  height: 18,
                  transform: 'translate(-50%, -50%)',
                  borderRadius: 2,
                  background: teal,
                  boxShadow: `0 0 0 3px ${glow}`,
                }}
              />
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: teal }}>
                {r.v}
              </div>
              <div
                style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: 'var(--ink-2)' }}
              >
                {r.pct}th
              </div>
            </div>
          </div>
        ))}
      </div>
    </Chrome>
  )
}

export function MarketLensMock({ isActive = true }: { isActive?: boolean } = {}) {
  void isActive
  const amber = 'var(--accent)'
  const ramp = [0.1, 0.26, 0.45, 0.66, 0.9]
  const steps = [
    0, 1, 1, 2, 1, 0, 0, 1,
    1, 2, 3, 4, 3, 1, 0, 0,
    0, 2, 4, 4, 3, 2, 1, 0,
    0, 1, 2, 3, 2, 2, 1, 0,
  ]
  const hatched = new Set([5, 15, 23, 31])
  const rows: Array<{ mkt: string; dep: string; sz: string; gr: string; spark: number[] }> = [
    { mkt: 'Nashville, TN', dep: '$21.6bn', sz: 'MAJOR', gr: 'HIGH', spark: [8, 11, 10, 14, 17, 21, 24] },
    { mkt: 'Atlanta, GA', dep: '$15.3bn', sz: 'MAJOR', gr: 'MED', spark: [6, 7, 9, 9, 12, 13, 16] },
    { mkt: 'Columbus, GA-AL', dep: '$5.7bn', sz: 'SECONDARY', gr: 'LOW', spark: [9, 9, 10, 10, 11, 11, 12] },
    { mkt: 'Birmingham, AL', dep: '$4.1bn', sz: 'MAJOR', gr: 'MED', spark: [7, 8, 8, 9, 10, 10, 11] },
    { mkt: 'Knoxville, TN', dep: '$3.4bn', sz: 'SECONDARY', gr: 'HIGH', spark: [7, 7, 6, 7, 6, 6, 6] },
  ]

  return (
    <Chrome url="marketlens.ace / Pinnacle Financial Partners · 81 markets">
      <div style={{ padding: '14px 16px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 10,
          }}
        >
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              letterSpacing: '0.1em',
              color: 'var(--ink-2)',
            }}
          >
            DEPOSIT SHARE · COUNTY · FDIC SOD
          </span>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              color: amber,
            }}
          >
            <span style={{ width: 3, height: 12, background: amber, borderRadius: 1 }} /> $96B PRO-FORMA
          </span>
        </div>

        <svg viewBox="0 0 256 100" style={{ width: '100%', display: 'block' }} aria-hidden="true">
          <defs>
            <pattern id="ml-hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="5" height="5" fill="color-mix(in srgb, currentColor 6%, transparent)" />
              <line x1="0" y1="0" x2="0" y2="5" stroke="currentColor" strokeWidth="1.1" opacity="0.32" />
            </pattern>
          </defs>
          {steps.map((step, i) => {
            const col = i % 8
            const row = Math.floor(i / 8)
            const jx = ((i * 7) % 3) - 1
            const jy = ((i * 5) % 3) - 1
            const isHatched = hatched.has(i)
            return (
              <rect
                key={i}
                x={col * 32 + 2 + jx}
                y={row * 24 + 3 + jy}
                width={28 - jx}
                height={20 - jy}
                rx="2"
                fill={isHatched ? 'url(#ml-hatch)' : amber}
                fillOpacity={isHatched ? 1 : ramp[step]}
                stroke="var(--line)"
                strokeWidth="0.6"
              />
            )
          })}
        </svg>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            margin: '10px 0 4px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 9,
            letterSpacing: '0.1em',
            color: 'var(--ink-2)',
          }}
        >
          <span>LOW</span>
          {ramp.map((opacity) => (
            <span
              key={opacity}
              style={{
                width: 18,
                height: 8,
                borderRadius: 2,
                background: amber,
                opacity,
                border: '1px solid var(--line)',
              }}
            />
          ))}
          <span>HIGH</span>
          <span style={{ marginLeft: 'auto' }}>▨ NO SOD FILING</span>
        </div>

        {rows.map((r) => (
          <div
            key={r.mkt}
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 58px 52px 46px',
              gap: 10,
              alignItems: 'center',
              padding: '8px 0',
              borderTop: '1px solid var(--line)',
            }}
          >
            <div>
              <div style={{ fontSize: 12.5, fontWeight: 600 }}>{r.mkt}</div>
              <div
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 9,
                  letterSpacing: '0.1em',
                  color: 'var(--ink-2)',
                }}
              >
                {r.sz} · {r.gr} GROWTH
              </div>
            </div>
            <svg viewBox="0 0 58 18" style={{ width: 58, height: 18, display: 'block' }} aria-hidden="true">
              <polyline
                points={r.spark
                  .map((value, i) => `${(i / (r.spark.length - 1)) * 56 + 1},${16 - (value / 26) * 14}`)
                  .join(' ')}
                fill="none"
                stroke={amber}
                strokeWidth="1.4"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            </svg>
            <div
              style={{
                textAlign: 'right',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: amber,
              }}
            >
              {r.dep}
            </div>
            <div
              style={{
                textAlign: 'right',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 9,
                letterSpacing: '0.08em',
                color: 'var(--ink-2)',
              }}
            >
              CITED
            </div>
          </div>
        ))}

        <div
          style={{
            marginTop: 10,
            paddingTop: 10,
            borderTop: '1px solid var(--line)',
            fontSize: 11.5,
            lineHeight: 1.45,
            color: 'var(--ink-2)',
          }}
        >
          <span style={{ color: amber, fontWeight: 600 }}>Brief · </span>
          Entrenched Leader in{' '}
          <span style={{ color: 'var(--ink)', borderBottom: `1px dotted ${amber}` }}>Nashville</span> at{' '}
          <span style={{ color: 'var(--ink)', borderBottom: `1px dotted ${amber}` }}>$21.6bn</span>
          {' '}(22.5% of the book); Atlanta is the second book at $15.3bn.
        </div>
      </div>
    </Chrome>
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
    }, 180)
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
            typingSpeedMs={22}
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
          typingSpeedMs={42}
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

/* ------------------------------------------------------------------ */
/* Annex — M&A target screener + Deal Lab + board packs.              */
/* A three-beat phase loop (SCREEN → BUILD → DEFEND), slate accent,   */
/* modelled on the Close Intel phase-loop + Lattice line-draw craft.  */
/* ------------------------------------------------------------------ */

type AnnexPhase = 0 | 1 | 2

function useCountUp(
  target: number,
  active: boolean,
  reduced: boolean,
  { start = 0, duration = 1000 }: { start?: number; duration?: number } = {},
) {
  const [value, setValue] = useState<number>(reduced ? target : start)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    if (reduced) {
      setValue(target)
      return
    }
    if (!active) {
      setValue(start)
      return
    }
    let startTs: number | null = null
    const tick = (ts: number) => {
      if (startTs === null) startTs = ts
      const p = Math.min(1, (ts - startTs) / duration)
      const eased = 1 - Math.pow(1 - p, 3)
      setValue(start + (target - start) * eased)
      if (p < 1) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [active, reduced, target, start, duration])

  return value
}

export function AnnexMock({ isActive = true }: { isActive?: boolean } = {}) {
  const [phase, setPhase] = useState<AnnexPhase>(0)
  const [reduced, setReduced] = useState(false)

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    if (reduced || !isActive) return
    setPhase(0)
    const id = window.setInterval(() => {
      setPhase((current) => ((current + 1) % 3) as AnnexPhase)
    }, 3200)
    return () => window.clearInterval(id)
  }, [isActive, reduced])

  const on = (index: number) => reduced || phase === index
  const phaseName = ['SCREEN', 'BUILD', 'DEFEND'][phase]

  return (
    <div className="prx-mock anx-mock">
      <div className="prx-chrome anx-chrome">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <div className="url">annex.ace / Arvest Bank {'×'} Southern Bancorp · Bolt-On</div>
        <div className="tag">
          ● ANNEX · LIVE{' '}
          <span className="anx-phase-tick">{reduced ? 'SCREEN · BUILD · DEFEND' : phaseName}</span>
        </div>
      </div>
      <div className={`prx-body anx-body${reduced ? ' anx-reduced' : ''}`}>
        <div className="anx-phase-stack">
          <AnnexScreenPhase active={on(0)} reduced={reduced} />
          <AnnexBuildPhase active={on(1)} reduced={reduced} />
          <AnnexDefendPhase active={on(2)} reduced={reduced} />
        </div>
        <div className="anx-phase-indicator" aria-label="Annex loop phase">
          {['SCREEN', 'BUILD', 'DEFEND'].map((label, index) => (
            <span key={label} className={phase === index ? 'on' : ''}>
              {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

function AnnexScreenPhase({ active, reduced }: { active: boolean; reduced: boolean }) {
  const count = useCountUp(12, active, reduced, { start: 4612, duration: 1150 })
  const survivors = new Set([12, 27, 41, 52, 63, 77, 88, 101, 113])
  const winner = 52
  const filters = ['ASSET 0.5–2.0×', 'IN-MARKET', 'FUNDING MIX', 'CET1 ≥ 8%']
  const rows: Array<{ rank: string; nm: string; cert: string; assets: string; sc: string; win: boolean }> = [
    { rank: '1', nm: 'Southern Bancorp Bank', cert: 'CERT 1528', assets: '$3.1B', sc: '94', win: true },
    { rank: '2', nm: 'Delta Heritage Bank', cert: 'CERT 3407', assets: '$1.9B', sc: '88', win: false },
    { rank: '3', nm: 'Ozark Community Bcshs', cert: 'CERT 5162', assets: '$1.2B', sc: '85', win: false },
  ]

  return (
    <div className={`anx-phase${active ? ' on' : ''}`}>
      <div className="anx-phase-label">
        <span>SCREEN · FDIC UNIVERSE</span>
        <span className="sub">outside-in</span>
      </div>
      <div className="anx-count">
        <span className="big">{Math.round(count).toLocaleString('en-US')}</span>
        <span className="cap">
          SHORTLISTED
          <br />
          FROM 4,612 TARGETS
        </span>
      </div>
      <div className="anx-filters">
        {filters.map((f, i) => (
          <span key={f} style={{ transitionDelay: active ? `${120 + i * 80}ms` : '0ms' }}>
            {f}
          </span>
        ))}
      </div>
      <div className="anx-field">
        {Array.from({ length: 120 }).map((_, i) => (
          <span
            key={i}
            className={`anx-dot${survivors.has(i) ? ' keep' : ''}${i === winner ? ' win' : ''}`}
            style={{ transitionDelay: active ? `${(i % 30) * 8}ms` : '0ms' }}
          />
        ))}
      </div>
      <div className="anx-list">
        <div className="anx-row head">
          <span className="rank">#</span>
          <span className="nm">TARGET</span>
          <span>CERT</span>
          <span>ASSETS</span>
          <span className="sc">FIT</span>
        </div>
        {rows.map((r, i) => (
          <div
            key={r.nm}
            className={`anx-row${r.win ? ' win' : ''}`}
            style={{ transitionDelay: active ? `${700 + i * 90}ms` : '0ms' }}
          >
            <span className="rank">{r.rank}</span>
            <span className="nm">{r.nm}</span>
            <span>{r.cert}</span>
            <span>{r.assets}</span>
            <span className="sc">{r.sc}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function AnnexBuildPhase({ active, reduced }: { active: boolean; reduced: boolean }) {
  const eps = useCountUp(3.4, active, reduced, { duration: 1200 })
  const cet1 = useCountUp(8.0, active, reduced, { start: 9.4, duration: 1200 })
  const earn = useCountUp(12.7, active, reduced, { duration: 1400 })
  const irr = useCountUp(14.2, active, reduced, { duration: 1200 })

  const levers: Array<{ k: string; v: string; w: number }> = [
    { k: 'PRICE / TBV', v: '1.42×', w: 68 },
    { k: 'COST SYNERGIES', v: '30%', w: 52 },
    { k: 'CREDIT MARK', v: '2.8%', w: 34 },
  ]

  const kpis: Array<[string, string, string]> = [
    ['EPS ACCR', `+${eps.toFixed(1)}%`, 'var(--accent-slate)'],
    ['PF CET1', `${cet1.toFixed(1)}%`, 'var(--accent-orange)'],
    ['EARNBACK', `${earn.toFixed(1)}y`, 'var(--accent-2)'],
    ['IRR', `${irr.toFixed(1)}%`, 'var(--accent-plum)'],
  ]

  return (
    <div className={`anx-phase${active ? ' on' : ''}`}>
      <div className="anx-phase-label">
        <span>BUILD · DEAL LAB</span>
        <span className="sub">recompute live</span>
      </div>
      <div className="anx-levers">
        {levers.map((lever, i) => (
          <div className="anx-lever" key={lever.k}>
            <span>{lever.k}</span>
            <span className="anx-track" style={{ '--w': `${lever.w}%` } as CSSProperties}>
              <span className="fill" style={{ transitionDelay: active ? `${i * 90}ms` : '0ms' }} />
              <span className="thumb" style={{ transitionDelay: active ? `${i * 90}ms` : '0ms' }} />
            </span>
            <span className="lv">{lever.v}</span>
          </div>
        ))}
      </div>
      <div className="anx-chart">
        <AnnexEarnbackChart reduced={reduced} />
      </div>
      <div className="anx-kpis">
        {kpis.map(([l, n, c]) => (
          <div className="k" key={l} style={{ '--c': c } as CSSProperties}>
            <div className="l">{l}</div>
            <div className="n">{n}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function AnnexEarnbackChart({ reduced }: { reduced: boolean }) {
  const width = 520
  const height = 124
  const years = 15
  const crossover = 12.7
  const value = (t: number) => -6.8 + 0.5 * t + 0.0025 * t * t
  const values = Array.from({ length: years + 1 }, (_, t) => value(t))
  const min = Math.min(...values) - 0.8
  const max = Math.max(...values) + 0.8
  const xAt = (t: number) => (t / years) * width
  const yAt = (v: number) => height - ((v - min) / (max - min)) * (height - 16) - 8

  const line = values
    .map((v, t) => `${t === 0 ? 'M' : 'L'} ${xAt(t).toFixed(1)} ${yAt(v).toFixed(1)}`)
    .join(' ')

  // Underwater band (TBV dilution, before earnback crossover).
  let dilution = `M ${xAt(0).toFixed(1)} ${yAt(0).toFixed(1)} `
  for (let t = 0; t <= 12; t += 1) dilution += `L ${xAt(t).toFixed(1)} ${yAt(values[t]).toFixed(1)} `
  dilution += `L ${xAt(crossover).toFixed(1)} ${yAt(0).toFixed(1)} Z`

  // Accretive band (after crossover).
  let accretion = `M ${xAt(crossover).toFixed(1)} ${yAt(0).toFixed(1)} `
  for (let t = 13; t <= years; t += 1) accretion += `L ${xAt(t).toFixed(1)} ${yAt(values[t]).toFixed(1)} `
  accretion += `L ${xAt(years).toFixed(1)} ${yAt(0).toFixed(1)} Z`

  const zeroY = yAt(0)
  const crossX = xAt(crossover)
  const slate = 'var(--accent-slate)'

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
      <path d={dilution} fill="var(--accent-orange)" fillOpacity="0.1" />
      <path d={accretion} fill={slate} fillOpacity="0.12" />
      <line
        x1={0}
        x2={width}
        y1={zeroY}
        y2={zeroY}
        stroke="currentColor"
        strokeOpacity="0.28"
        strokeDasharray="3 4"
      />
      <text x={4} y={zeroY - 6} fontFamily="JetBrains Mono, monospace" fontSize="9" fill="currentColor" fillOpacity="0.5" letterSpacing="0.1em">
        TBV NEUTRAL
      </text>
      <path
        className="anx-draw"
        d={line}
        fill="none"
        stroke={slate}
        strokeWidth="2.1"
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={100}
      />
      <line x1={crossX} x2={crossX} y1={zeroY} y2={10} stroke={slate} strokeWidth="1" strokeDasharray="2 3" opacity="0.55" />
      {reduced ? null : <circle className="anx-cross-ring" cx={crossX} cy={zeroY} r={5} fill="none" stroke={slate} strokeWidth="1.4" />}
      <circle cx={crossX} cy={zeroY} r="4.4" fill={slate} />
      <text x={crossX + 8} y={16} fontFamily="JetBrains Mono, monospace" fontSize="10.5" fontWeight="600" fill={slate} letterSpacing="0.06em">
        EARNBACK · 12.7y
      </text>
      <text x={4} y={height - 3} fontFamily="JetBrains Mono, monospace" fontSize="8.5" fill="currentColor" fillOpacity="0.45" letterSpacing="0.1em">
        CUMULATIVE TBV · YR 0
      </text>
      <text x={width - 4} y={height - 3} fontFamily="JetBrains Mono, monospace" fontSize="8.5" fill="currentColor" fillOpacity="0.45" letterSpacing="0.1em" textAnchor="end">
        YR 15
      </text>
    </svg>
  )
}

function AnnexDefendPhase({ active, reduced }: { active: boolean; reduced: boolean }) {
  void reduced
  const rows: Array<[string, string, string]> = [
    ['EPS ACCRETION', '+3.4%', 'FDIC · RI'],
    ['PRO-FORMA CET1', '8.0%', 'FDIC · RC-R'],
    ['TBV EARNBACK', '12.7y', 'FDIC · RC-R'],
    ['DEAL IRR', '14.2%', 'FDIC · RC-K'],
  ]

  return (
    <div className={`anx-phase${active ? ' on' : ''}`}>
      <div className="anx-phase-label">
        <span>DEFEND · BOARD PACK</span>
        <span className="sub">every figure cited</span>
      </div>
      <div className="anx-pack">
        <div className="anx-pack-head">
          <span>BOLT-ON · ARVEST {'×'} SOUTHERN BANCORP</span>
          <span className="st">{active ? '● READY' : '● ASSEMBLING'}</span>
        </div>
        {rows.map(([m, v, src], i) => (
          <div className="anx-cite-row" key={m} style={{ transitionDelay: active ? `${i * 120}ms` : '0ms' }}>
            <span className="m">
              {m}
              <b>{v}</b>
            </span>
            <span className="anx-trace" />
            <span className="anx-src">
              <span className="dot" />
              {src}
            </span>
          </div>
        ))}
      </div>
      <div className="anx-guard">GUARD ✓ EVERY FIGURE CITED · 0 WITHOUT LINEAGE</div>
    </div>
  )
}
