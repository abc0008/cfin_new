'use client'

import Image from 'next/image'
import { useEffect, useRef, useState } from 'react'
import { ParallaxMock, PeerLensMock } from '@/components/marketing/product-mocks'
import { Eyebrow, ProductSubnav, useReveal } from '@/components/marketing/shared'
import {
  BOOK_DEMO_URL,
  CFIN_WORKSPACE_URL,
  CREDIT_SPREAD_URL,
  PEER_ANALYSIS_URL,
  REGIONAL_FORECASTING_URL,
  RM_PRO_FORMA_URL,
} from '@/lib/app-urls'

const TEXT2SQL_APP_URL =
  process.env.NEXT_PUBLIC_TEXT2SQL_APP_URL || 'https://text2sql.aceanalytics.dev'
const TEXT2SQL_GUIDED_MODE_URL = `${TEXT2SQL_APP_URL.replace(/\/+$/, '')}/guided-mode`

export function CfinProductDetailPage() {
  return (
    <main className="pp pp-cfin">
      <ProductSubnav />

      <section className="pp-hero">
        <div className="wrap pp-hero-grid">
          <div className="pp-hero-copy">
            <div className="pp-eyebrow">
              <span className="op">OP_APRT</span>
              <span className="pill">aceanalytics.dev / cfin</span>
            </div>
            <h1 className="pp-h1">
              Financial documents,
              <br />
              <span className="ital" style={{ color: 'var(--accent)' }}>
                read closely.
              </span>
            </h1>
            <p className="pp-lede">
              Aperture turns filings, decks, and statements into structured, cited data - with
              every number tied back to a page, a table, a bounding box.
            </p>
            <div className="pp-hero-actions">
              <a className="btn btn-primary" href={CFIN_WORKSPACE_URL}>
                Upload a document →
              </a>
              <a className="btn btn-ghost" href={BOOK_DEMO_URL}>
                See a live run
              </a>
            </div>
            <div className="pp-hero-tags">
              {[
                ['PDF · XLSX · DOCX', 'multi-format'],
                ['99.4%', 'line-item accuracy'],
                ['18mo', 'in the wild'],
              ].map(([a, b], i) => (
                <div key={i} className="pp-tag">
                  <div className="t">{a}</div>
                  <div className="s">{b}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="pp-hero-art">
            <ApertureMockLive />
          </div>
        </div>
      </section>

      <section className="pp-strip">
        <div className="wrap">
          <CapCard
            ix="01"
            title="Line-item extraction"
            body="Every cell of every statement, labeled, typed, and referenced back to the source page."
            accent="var(--accent)"
          />
          <CapCard
            ix="02"
            title="Ratio engine"
            body="ROE, ROA, NIM, efficiency - calculated live, traceable to the inputs that made them."
            accent="var(--accent-orange)"
          />
          <CapCard
            ix="03"
            title="Citation tracking"
            body="Click any number. Jump to the exact page, row, and bounding box it was pulled from."
            accent="var(--accent-2)"
          />
          <CapCard
            ix="04"
            title="Cross-document Q&A"
            body="Ask questions across filings. Answers come with receipts, not paraphrase."
            accent="var(--accent-slate)"
          />
        </div>
      </section>

      <ApertureBeam />

      <section className="pp-split" id="methods">
        <div className="wrap">
          <div className="pp-split-head">
            <Eyebrow op="OP_APRT_02">Specialized analyses</Eyebrow>
            <h2 className="pp-h2">
              Four modules.
              <br />
              One document engine.
            </h2>
          </div>
          <div className="pp-modules">
            {[
              {
                ix: 'A.01',
                name: 'Financial Statements',
                body: 'Income, balance, cash flow - with automated ratio roll-ups and period-over-period.',
                color: 'var(--accent)',
              },
              {
                ix: 'A.02',
                name: 'Risk Assessment',
                body: 'Leverage, coverage, stress. Identify exposure before the committee asks.',
                color: 'var(--accent-orange)',
              },
              {
                ix: 'A.03',
                name: 'Due Diligence',
                body: 'M&A review at scale. Compliance flags, redlines, and missing-document alerts.',
                color: 'var(--accent-slate)',
              },
              {
                ix: 'A.04',
                name: 'Portfolio Review',
                body: 'Loan tapes, performance across vintages, covenant drift across the book.',
                color: 'var(--accent-2)',
              },
            ].map((module, i) => (
              <div key={i} className="pp-module" style={{ '--m-color': module.color } as React.CSSProperties}>
                <div className="ix">{module.ix}</div>
                <h3>{module.name}</h3>
                <p>{module.body}</p>
                <div className="arrow">→</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <PPFlow
        op="OP_APRT_03"
        title={
          <>
            Upload.{' '}
            <span className="ital" style={{ color: 'var(--accent)' }}>
              Extract.
            </span>{' '}
            Cite.
          </>
        }
        steps={[
          {
            n: '01',
            t: 'Upload & Process',
            b: 'Drop a filing. OCR, layout, and table detection run in parallel. Structured data is ready in seconds.',
          },
          {
            n: '02',
            t: 'Ask & Analyze',
            b: 'Natural-language Q&A over the document. Every answer threads back to the source.',
          },
          {
            n: '03',
            t: 'Visualize & Act',
            b: 'Live ratios, trend charts, exportable models. Hand it to audit, unedited.',
          },
        ]}
        accent="var(--accent)"
      />

      <PPCta
        title={
          <>
            Read <span className="ital">between</span>
            <br />
            the numbers.
          </>
        }
        sub="Start with a single filing. See the difference cited extraction makes."
        primary="Open CFIN Workspace"
        primaryHref={CFIN_WORKSPACE_URL}
        secondary="See benchmark methodology"
        secondaryHref="/product/cfin#methods"
        accent="var(--accent)"
      />
    </main>
  )
}

function ApertureMockLive() {
  const [hot, setHot] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setHot((h) => (h + 1) % 4), 2200)
    return () => clearInterval(id)
  }, [])

  const rows = [
    {
      label: 'Total Revenue',
      y26: '$47,734',
      y27: '$244,627',
      y28: '$506,986',
      cite: 'p. 12 · B14',
      k: 'REV_FY',
    },
    {
      label: 'Net Income',
      y26: '-$46,593',
      y27: '$80,794',
      y28: '$308,296',
      cite: 'p. 12 · B21',
      k: 'NI_FY',
    },
    {
      label: 'Return on Equity',
      y26: '-5.30%',
      y27: '2.80%',
      y28: '5.40%',
      cite: 'p. 14 · D08',
      k: 'ROE',
    },
    {
      label: 'Net Interest Margin',
      y26: '4.20%',
      y27: '6.47%',
      y28: '6.65%',
      cite: 'p. 14 · D11',
      k: 'NIM',
    },
  ]

  return (
    <div className="apt-mock">
      <div className="apt-chrome">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <div className="url">aperture.ace / filing_Q3_2026.pdf</div>
        <div className="tag">EXTRACTED · 12 tables · 38 pages</div>
      </div>
      <div className="apt-body">
        <div className="apt-doc">
          <div className="apt-page-tag">PAGE 12 OF 38</div>
          <div className="apt-pg">
            <div className="apt-head">
              <div className="apt-title">Consolidated Income Statement</div>
              <div className="apt-sub">Fiscal year ended · in thousands</div>
            </div>
            <div className="apt-tbl">
              <div className="apt-th">
                <div>Metric</div>
                <div>2026</div>
                <div>2027</div>
                <div>2028</div>
              </div>
              {rows.map((row, i) => (
                <div key={i} className={`apt-tr${i === hot ? ' hot' : ''}`}>
                  <div className="l">{row.label}</div>
                  <div>{row.y26}</div>
                  <div>{row.y27}</div>
                  <div className="v">{row.y28}</div>
                </div>
              ))}
            </div>
            <div className="apt-box" style={{ top: `${98 + hot * 28}px` }} />
          </div>
        </div>
        <div className="apt-extract">
          <div className="apt-extract-label">EXTRACTED</div>
          <div className="apt-card">
            <div className="k">{rows[hot].k}</div>
            <div className="v">{rows[hot].y28}</div>
            <div className="meta">FY 2028 · estimate</div>
            <div className="cite">
              <span className="pin">●</span>
              <div>
                <div className="c1">CITATION</div>
                <div className="c2">{rows[hot].cite}</div>
              </div>
            </div>
          </div>
          <div className="apt-trace">
            <div className="dot" />
            <div className="trace-line" />
            <div className="trace-label">Traced to source cell</div>
          </div>
          <div className="apt-ratios">
            {[
              ['ROE', '5.40%', 'var(--accent)'],
              ['ROA', '4.39%', 'var(--accent-orange)'],
              ['NIM', '6.65%', 'var(--accent-2)'],
              ['EFF', '26.2%', 'var(--accent-slate)'],
            ].map(([k, v, c], i) => (
              <div key={i} className="r" style={{ '--r-c': c } as React.CSSProperties}>
                <div className="rk">{k}</div>
                <div className="rv">{v}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function ApertureBeam() {
  const wrapRef = useRef<HTMLElement | null>(null)
  useReveal(wrapRef)

  const inputs = [
    {
      id: 'in-01',
      op: 'IN_01',
      label: 'PDF',
      sub: 'filings · 10-K · decks',
      icon: '/icons/pdf-svgrepo-com.svg',
      slot: 'beam-pos-in-1',
      tone: 'beam-orb-lust',
      tint: 'beam-icon-lust',
    },
    {
      id: 'in-02',
      op: 'IN_02',
      label: 'XLSX',
      sub: 'models · schedules',
      icon: '/icons/ms-excel-svgrepo-com.svg',
      slot: 'beam-pos-in-2',
      tone: 'beam-orb-hobgoblin',
      tint: '',
    },
    {
      id: 'in-03',
      op: 'IN_03',
      label: 'DOCX',
      sub: 'MD&A · memos · covenants',
      icon: '/icons/ms-word-svgrepo-com.svg',
      slot: 'beam-pos-in-3',
      tone: 'beam-orb-rushmore',
      tint: '',
    },
  ]
  const outputs = [
    {
      id: 'out-01',
      op: 'OUT_01',
      label: 'Dashboards',
      sub: 'ratios · trend · roll-up',
      icon: '/icons/dashboard-svgrepo-com.svg',
      slot: 'beam-pos-out-1',
      tone: 'beam-orb-caribbean',
      tint: 'beam-icon-caribbean',
    },
    {
      id: 'out-02',
      op: 'OUT_02',
      label: 'Cited Q&A',
      sub: 'answers with page-level proof',
      icon: '/icons/chat-round-unread-svgrepo-com.svg',
      slot: 'beam-pos-out-2',
      tone: 'beam-orb-lust',
      tint: 'beam-icon-lust',
    },
  ]
  const beamPaths = [
    {
      id: 'beam-grad-in-1',
      d: 'M 60.8,76 Q 303.525,96 546.25,151.05',
      from: 'var(--accent-orange)',
      to: 'var(--accent-plum)',
      dash: '64% 36%',
      delay: '0s',
    },
    {
      id: 'beam-grad-in-2',
      d: 'M 60.8,151.05 Q 303.525,151.05 546.25,151.05',
      from: 'var(--accent-2)',
      to: 'var(--accent-plum)',
      dash: '84% 16%',
      delay: '0.25s',
    },
    {
      id: 'beam-grad-in-3',
      d: 'M 60.8,226.1 Q 303.525,206.1 546.25,151.05',
      from: 'var(--ink-3)',
      to: 'var(--accent-plum)',
      dash: '48% 52%',
      delay: '0.5s',
    },
    {
      id: 'beam-grad-out-1',
      d: 'M 546.25,151.05 Q 788.975,166.05 1031.7,75.525',
      from: 'var(--accent-plum)',
      to: 'var(--accent-slate)',
      dash: '45% 55%',
      delay: '0.8s',
    },
    {
      id: 'beam-grad-out-2',
      d: 'M 546.25,151.05 Q 788.975,136.05 1031.7,226.575',
      from: 'var(--accent-plum)',
      to: 'var(--accent-orange)',
      dash: '67% 33%',
      delay: '1.05s',
    },
  ]

  return (
    <section className="pp-beam" ref={wrapRef}>
      <div className="wrap">
        <div className="pp-beam-head">
          <Eyebrow op="OP_APRT_BEAM">Inside the pipeline</Eyebrow>
          <h2 className="pp-h2">
            Messy in.{' '}
            <span className="ital" style={{ color: 'var(--accent)' }}>
              Structured out.
            </span>
          </h2>
          <p className="pp-beam-sub">
            Aperture ingests unstructured financial documents, extracts line-items with page-level
            citations, and delivers auditable outputs. Watch a filing move through the system.
          </p>
        </div>

        <div className="beam-stage">
          <svg className="beam-wires" viewBox="0 0 1092.5 302.1" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              {beamPaths.map((path) => (
                <linearGradient key={path.id} id={path.id} gradientUnits="userSpaceOnUse" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor={path.from} stopOpacity="1" />
                  <stop offset="100%" stopColor={path.to} stopOpacity="0" />
                </linearGradient>
              ))}
            </defs>
            {beamPaths.map((path) => (
              <g key={`${path.id}-wire`}>
                <path d={path.d} className="wire-base" />
                <path
                  d={path.d}
                  className="wire-pulse"
                  style={{
                    stroke: `url(#${path.id})`,
                    strokeDasharray: path.dash,
                    animationDelay: path.delay,
                  }}
                />
              </g>
            ))}
          </svg>

          {inputs.map((input) => (
            <div key={input.id} className={`beam-orb-wrap beam-orb-left ${input.slot}`}>
              <div className={`beam-orb ${input.tone}`}>
                <Image
                  src={input.icon}
                  alt={input.label}
                  width={32}
                  height={32}
                  className={`beam-orb-icon${input.tint ? ` ${input.tint}` : ''}`}
                />
              </div>
              <div className="beam-orb-meta">
                <span className="beam-meta-op">{input.op}</span>
                <span className="beam-meta-label">{input.label}</span>
                <span className="beam-meta-sub">{input.sub}</span>
              </div>
            </div>
          ))}

          <div className="beam-orb-wrap beam-pos-core beam-orb-core-wrap">
            <div className="beam-orb beam-orb-core">
              <Image
                src="/icons/claude-ai-icon.svg"
                alt="Aperture processing engine"
                width={40}
                height={40}
                className="beam-orb-icon"
              />
            </div>
            <div className="beam-core-meta">
              <span className="beam-meta-op">OP_APRT</span>
              <span className="beam-meta-label">Aperture</span>
              <span className="beam-meta-sub">extracting and binding citations</span>
            </div>
          </div>

          {outputs.map((output) => (
            <div key={output.id} className={`beam-orb-wrap beam-orb-right ${output.slot}`}>
              <div className={`beam-orb ${output.tone}`}>
                <Image
                  src={output.icon}
                  alt={output.label}
                  width={32}
                  height={32}
                  className={`beam-orb-icon${output.tint ? ` ${output.tint}` : ''}`}
                />
              </div>
              <div className="beam-orb-meta">
                <span className="beam-meta-op">{output.op}</span>
                <span className="beam-meta-label">{output.label}</span>
                <span className="beam-meta-sub">{output.sub}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="beam-legend">
          <div className="lg">
            <span className="lg-k">INGEST</span>
            <span className="lg-v">multi-format, any vintage</span>
          </div>
          <div className="lg">
            <span className="lg-k">EXTRACT</span>
            <span className="lg-v">line-item, table, bounding box</span>
          </div>
          <div className="lg">
            <span className="lg-k">BIND</span>
            <span className="lg-v">page-level citation on every value</span>
          </div>
          <div className="lg">
            <span className="lg-k">SERVE</span>
            <span className="lg-v">dashboards, chat, structured export</span>
          </div>
        </div>
      </div>
    </section>
  )
}

export function ForecastingProductDetailPage() {
  return (
    <main className="pp pp-rm">
      <ProductSubnav />

      <section className="pp-hero">
        <div className="wrap pp-hero-grid">
          <div className="pp-hero-copy">
            <div className="pp-eyebrow">
              <span className="op" style={{ color: 'var(--accent-plum)' }}>
                OP_FCST
              </span>
              <span className="pill">aceanalytics.dev / forecasting</span>
            </div>
            <h1 className="pp-h1">
              The Forecast tool
              <br />
              <span className="ital" style={{ color: 'var(--accent-plum)' }}>
                you&apos;ve dreamed of
              </span>
            </h1>
            <p className="pp-lede">
              Forecast with governance, lineage &amp; guardrails, with AI-assistance at every
              level. Start with review of baseline (actuals pulled from GL database), layer on
              macro scenarios, input existing workforce assumptions, producer hiring, expense
              controls, and regulatory guardrails into a governed scenario version.
            </p>
            <div className="pp-hero-actions">
              <a
                className="btn btn-primary"
                style={{ background: 'var(--accent-plum)', color: '#fff' }}
                href={REGIONAL_FORECASTING_URL}
              >
                Open Forecasting Module →
              </a>
              <a className="btn btn-ghost" href="https://bankanalysis.aceanalytics.dev/forecasting/guide">
                See Forecasting Guide
              </a>
            </div>
            <div className="pp-hero-tags">
              {[
                ['60 months', 'monthly planning horizon'],
                ['GL_Fact', 'baseline and forecast target'],
                ['Lineage', 'user-input audit trail'],
              ].map(([a, b], i) => (
                <div key={i} className="pp-tag" style={{ '--tc': 'var(--accent-plum)' } as React.CSSProperties}>
                  <div className="t">{a}</div>
                  <div className="s">{b}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="pp-hero-art">
            <ForecastingMockLive />
          </div>
        </div>
      </section>

      <section className="pp-strip" id="methods">
        <div className="wrap">
          <CapCard
            ix="01"
            title="Base forecast review"
            body="Actuals load from GL_Fact, entity, and account dimensions into a monthly executive review surface."
            accent="var(--accent-plum)"
          />
          <CapCard
            ix="02"
            title="Macro scenario layer"
            body="Rates, GDP, deposit runoff, credit stress, and inflation toggles show annual divergence from base."
            accent="var(--accent-slate)"
          />
          <CapCard
            ix="03"
            title="Top-down control meets bottoms-up input"
            body="Finance liaisons collect market hiring, attrition, ramp, and controllable spend assumptions with user lineage."
            accent="var(--accent-2)"
          />
          <CapCard
            ix="04"
            title="Governed writeback"
            body="Validated rows replace the selected scenario, data source, planning entity, and forecast periods in GL_Fact."
            accent="var(--accent-orange)"
          />
        </div>
      </section>

      <section className="pp-video" style={{ padding: '0 0 80px' }}>
        <div className="wrap">
          <div
            style={{
              border: '1px solid var(--line)',
              borderRadius: 16,
              overflow: 'hidden',
              background: '#000',
            }}
          >
            <video
              controls
              preload="metadata"
              playsInline
              poster="https://bankanalysis.aceanalytics.dev/media/forecasting-module-launch-poster.jpg"
              style={{ display: 'block', width: '100%', height: 'auto' }}
            >
              <source
                src="https://bankanalysis.aceanalytics.dev/media/forecasting-module-launch.mp4"
                type="video/mp4"
              />
              Your browser does not support embedded video.{' '}
              <a href="https://bankanalysis.aceanalytics.dev/media/forecasting-module-launch.mp4">
                Download the walkthrough
              </a>
              .
            </video>
          </div>
        </div>
      </section>

      <PPFlow
        op="OP_FCST_03"
        title={
          <>
            Baseline.{' '}
            <span className="ital" style={{ color: 'var(--accent-plum)' }}>
              Adjust.
            </span>{' '}
            Load.
          </>
        }
        steps={[
          {
            n: '01',
            t: 'Source baseline',
            b: 'Read GL actuals by region and market, then project the base forecast monthly across the planning horizon.',
          },
          {
            n: '02',
            t: 'Layer assumptions',
            b: 'Apply macro toggles, existing workforce levers, producer hiring economics, and controllable spend changes.',
          },
          {
            n: '03',
            t: 'Commit scenario',
            b: 'Stage the forecast, validate row status, and write a governed scenario version back to GL_Fact.',
          },
        ]}
        accent="var(--accent-plum)"
      />

      <PPCta
        title={
          <>
            Forecast from the market.
            <br />
            Govern from the <span className="ital">center.</span>
          </>
        }
        sub="Forecast gives FP&A a live operating surface for market-owned assumptions, centralized controls, and audit-ready forecast loads."
        primary="Open Forecasting Module"
        primaryHref={REGIONAL_FORECASTING_URL}
        secondary="Read the methods"
        secondaryHref="/product/forecasting#methods"
        accent="var(--accent-plum)"
      />
    </main>
  )
}

function ForecastingMockLive() {
  const planRows = [
    ['FY2027', '$431M', '$444M', '+$12.8M'],
    ['FY2028', '$462M', '$479M', '+$17.1M'],
    ['FY2029', '$491M', '$510M', '+$19.3M'],
  ]
  const guardrails = [
    ['LCR', '119.2%', '78%'],
    ['CET1', '11.3%', '64%'],
    ['Loan / Deposit', '91.5%', '58%'],
  ]

  return (
    <div className="prx-mock">
      <div className="prx-chrome">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <div className="url">forecast.ace / Southeast · FY2027 PLAN</div>
        <div className="tag" style={{ color: 'var(--accent-plum)' }}>
          ● SCENARIO · STAGED
        </div>
      </div>
      <div className="prx-body">
        <div className="prx-head">
          <div>
            <div className="k">BASELINE VS MODIFIED</div>
            <div className="v" style={{ color: 'var(--accent-plum)' }}>
              +$12.8M
            </div>
            <div className="sub">FY2027 net income variance</div>
          </div>
          <div className="prx-pills">
            <span>BASE</span>
            <span className="on">PLAN</span>
            <span>STRESS</span>
          </div>
        </div>

        <div
          style={{
            border: '1px solid var(--line)',
            display: 'grid',
            gridTemplateColumns: '0.8fr 1fr 1fr 1fr',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
          }}
        >
          {['Year', 'Baseline', 'Modified', 'Variance'].map((header) => (
            <div
              key={header}
              style={{
                color: 'var(--ink-3)',
                letterSpacing: '0.12em',
                padding: '10px 12px',
                borderBottom: '1px solid var(--line)',
                textTransform: 'uppercase',
              }}
            >
              {header}
            </div>
          ))}
          {planRows.flatMap((row) =>
            row.map((cell, index) => (
              <div
                key={`${row[0]}-${index}`}
                style={{
                  padding: '11px 12px',
                  borderBottom: row[0] === 'FY2029' ? '0' : '1px solid var(--line)',
                  color: index === 3 ? 'var(--accent-2)' : 'var(--ink)',
                  fontWeight: index === 0 || index === 3 ? 600 : 400,
                }}
              >
                {cell}
              </div>
            )),
          )}
        </div>

        <div style={{ display: 'grid', gap: 12, marginTop: 20 }}>
          {guardrails.map(([metric, value, position]) => (
            <div key={metric} style={{ display: 'grid', gridTemplateColumns: '96px 1fr 56px', gap: 12, alignItems: 'center' }}>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: 'var(--ink-2)' }}>{metric}</div>
              <div
                style={{
                  height: 12,
                  position: 'relative',
                  background:
                    'linear-gradient(90deg, rgba(119,151,106,.35) 0 60%, rgba(255,172,3,.32) 60% 82%, rgba(216,93,57,.32) 82% 100%)',
                }}
              >
                <span
                  style={{
                    position: 'absolute',
                    left: position,
                    top: -4,
                    width: 8,
                    height: 20,
                    background: 'var(--accent-plum)',
                  }}
                />
              </div>
              <div style={{ fontWeight: 600, color: 'var(--ink)' }}>{value}</div>
            </div>
          ))}
        </div>

        <div className="prx-kpis">
          {[
            ['Rows', '960', 'var(--accent-plum)'],
            ['Markets', '24', 'var(--accent-slate)'],
            ['Status', 'Ready', 'var(--accent-2)'],
            ['Load', 'GL_Fact', 'var(--accent-orange)'],
          ].map(([k, v, c], i) => (
            <div key={i} className="k" style={{ '--c': c } as React.CSSProperties}>
              <div className="l">{k}</div>
              <div className="n">{v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function CreditSpreadProductDetailPage() {
  return (
    <main className="pp pp-rm">
      <ProductSubnav />

      <section className="pp-hero">
        <div className="wrap pp-hero-grid">
          <div className="pp-hero-copy">
            <div className="pp-eyebrow">
              <span className="op" style={{ color: 'var(--accent-orange)' }}>
                OP_PRLX
              </span>
              <span className="pill">bankanalysis.aceanalytics.dev / credit-spread</span>
            </div>
            <h1 className="pp-h1">
              Borrower packages,
              <br />
              <span className="ital" style={{ color: 'var(--accent-orange)' }}>
                spread cleanly.
              </span>
            </h1>
            <p className="pp-lede">
              Parallax ingests scanned borrower packets and outputs committee-ready spreads with
              covenants, DSCR, and risk-ready ratios tied to source pages.
            </p>
            <div className="pp-hero-actions">
              <a
                className="btn btn-primary"
                style={{ background: 'var(--accent-orange)', color: '#fff' }}
                href={CREDIT_SPREAD_URL}
              >
                Open Credit Spreading App →
              </a>
              <a className="btn btn-ghost" href="/product/credit-spread#methods">
                See sample spread output
              </a>
            </div>
            <div className="pp-hero-tags">
              {[
                ['OCR-first', 'scans + handwriting'],
                ['Committee-ready', 'DSCR · FCC · LTV'],
                ['Covenant aware', 'stress-tested outputs'],
              ].map(([a, b], i) => (
                <div key={i} className="pp-tag" style={{ '--tc': 'var(--accent-orange)' } as React.CSSProperties}>
                  <div className="t">{a}</div>
                  <div className="s">{b}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="pp-hero-art">
            <ParallaxMock isActive />
          </div>
        </div>
      </section>

      <section className="pp-strip" id="methods">
        <div className="wrap">
          <CapCard
            ix="01"
            title="OCR tuned for real packets"
            body="Tax returns, K-1s, statements, appraisals, and scanned exhibits are parsed into structured fields."
            accent="var(--accent-orange)"
          />
          <CapCard
            ix="02"
            title="Credit spreading outputs"
            body="DSCR, FCC, LTV, leverage, and trend deltas are computed automatically from the extracted package."
            accent="var(--accent-slate)"
          />
          <CapCard
            ix="03"
            title="Covenant sensitivity"
            body="Scenario overlays highlight where thresholds break before a package reaches committee."
            accent="var(--accent-2)"
          />
          <CapCard
            ix="04"
            title="Audit trail included"
            body="Each line item and ratio can be traced back to source pages for defensible underwriting."
            accent="var(--accent-plum)"
          />
        </div>
      </section>

      <PPFlow
        op="OP_PRLX_03"
        title={
          <>
            Ingest.{' '}
            <span className="ital" style={{ color: 'var(--accent-orange)' }}>
              Spread.
            </span>{' '}
            Deliver.
          </>
        }
        steps={[
          {
            n: '01',
            t: 'Upload packet',
            b: 'Drop a borrower package and let OCR parse forms, statements, and appendices in one pass.',
          },
          {
            n: '02',
            t: 'Review spread',
            b: 'Inspect normalized financials, covenants, and risk metrics with source-linked context.',
          },
          {
            n: '03',
            t: 'Ship to committee',
            b: 'Export a lender-ready spread package with confidence annotations and audit support.',
          },
        ]}
        accent="var(--accent-orange)"
      />

      <PPCta
        title={
          <>
            Spread with speed.
            <br />
            Defend with <span className="ital">evidence.</span>
          </>
        }
        sub="Parallax replaces hand-keyed borrower spreading with a repeatable, auditable workflow."
        primary="Open Credit Spreading App"
        primaryHref={CREDIT_SPREAD_URL}
        secondary="Read the methods"
        secondaryHref="/product/credit-spread#methods"
        accent="var(--accent-orange)"
      />
    </main>
  )
}

export function LatticeProductDetailPage() {
  return (
    <main className="pp pp-rm">
      <ProductSubnav />

      <section className="pp-hero">
        <div className="wrap pp-hero-grid">
          <div className="pp-hero-copy">
            <div className="pp-eyebrow">
              <span className="op" style={{ color: 'var(--accent-2)' }}>
                OP_LTTC
              </span>
              <span className="pill">bankanalysis.aceanalytics.dev / rm-pro-forma</span>
            </div>
            <h1 className="pp-h1">
              Breakeven models
              <br />
              <span className="ital" style={{ color: 'var(--accent-2)' }}>
                for every hire.
              </span>
            </h1>
            <p className="pp-lede">
              Lattice builds production-grade pro-forma models for new RMs - yield curve, loan
              production, payback, and full financial statements tied to live rate assumptions.
            </p>
            <div className="pp-hero-actions">
              <a
                className="btn btn-primary"
                style={{ background: 'var(--accent-2)', color: '#fff' }}
                href={RM_PRO_FORMA_URL}
              >
                Open Lattice Workspace →
              </a>
              <a className="btn btn-ghost" href={RM_PRO_FORMA_URL}>
                Export to Excel
              </a>
            </div>
            <div className="pp-hero-tags">
              {[
                ['1y 5mo', 'avg. payback'],
                ['6 years', 'projection horizon'],
                ['$18.4M', 'modeled assets · yr 6'],
              ].map(([a, b], i) => (
                <div key={i} className="pp-tag" style={{ '--tc': 'var(--accent-2)' } as React.CSSProperties}>
                  <div className="t">{a}</div>
                  <div className="s">{b}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="pp-hero-art">
            <LatticeMockLive />
          </div>
        </div>
      </section>

      <section className="pp-strip">
        <div className="wrap">
          <CapCard
            ix="01"
            title="RM Type & Start"
            body="Hire date, segment, book assumptions. The model adapts to the persona you're funding."
            accent="var(--accent-2)"
          />
          <CapCard
            ix="02"
            title="Balance Sheet Dynamics"
            body="Volume, pricing, runoff, and deposit mix - modeled month by month over six years."
            accent="var(--accent-slate)"
          />
          <CapCard
            ix="03"
            title="Yield Curve Projections"
            body="3M through 30Y, with scenario overlays. Rate shocks propagate to every projected cash flow."
            accent="var(--accent-2)"
          />
          <CapCard
            ix="04"
            title="Cumulative Payback"
            body="Exact month break-even lands in. Hand it to the Chief Credit Officer, unedited."
            accent="var(--accent-plum)"
          />
        </div>
      </section>

      <section className="pp-rm-statements" id="methods">
        <div className="wrap">
          <div className="pp-split-head">
            <Eyebrow op="OP_LTTC_02">Full financial statements</Eyebrow>
            <h2 className="pp-h2">
              Balance sheet, income statement,
              <br />
              and{' '}
              <span className="ital" style={{ color: 'var(--accent-2)' }}>
                key ratios.
              </span>{' '}
              Every time.
            </h2>
          </div>
          <RmIncomeStatement />
        </div>
      </section>

      <PPFlow
        op="OP_LTTC_03"
        title={
          <>
            Configure.{' '}
            <span className="ital" style={{ color: 'var(--accent-2)' }}>
              Calculate.
            </span>{' '}
            Commit.
          </>
        }
        steps={[
          {
            n: '01',
            t: 'Configure inputs',
            b: 'Salary, merit, incentive comp, deferred costs per loan, avg. exposure at origination.',
          },
          {
            n: '02',
            t: 'Calculate pro-forma',
            b: 'Six-year projection across balance sheet, P&L, and key ratios. Yield curve baked in.',
          },
          {
            n: '03',
            t: 'Commit & export',
            b: 'Lock the assumption set, export to Excel or to a committee memo PDF.',
          },
        ]}
        accent="var(--accent-2)"
      />

      <PPCta
        title={
          <>
            Model the <span className="ital">hire,</span>
            <br />
            not just the role.
          </>
        }
        sub="Lattice replaces the ad-hoc RM spreadsheet every bank keeps rebuilding."
        primary="Open Lattice Workspace"
        primaryHref={RM_PRO_FORMA_URL}
        secondary="See sample committee output"
        secondaryHref="/product/lattice#methods"
        accent="var(--accent-2)"
      />
    </main>
  )
}

export function PeerLensProductDetailPage() {
  const accent = 'var(--accent-teal)'
  return (
    <main className="pp pp-rm">
      <ProductSubnav />

      <section className="pp-hero">
        <div className="wrap pp-hero-grid">
          <div className="pp-hero-copy">
            <div className="pp-eyebrow">
              <span className="op" style={{ color: accent }}>
                OP_PRLN
              </span>
              <span className="pill">peeranalysis.aceanalytics.dev</span>
            </div>
            <h1 className="pp-h1">
              Read a bank against
              <br />
              <span className="ital" style={{ color: accent }}>
                a fair peer set.
              </span>
            </h1>
            <p className="pp-lede">
              Peer Lens runs an AI agent to identify a defensible peer group from FDIC regulatory data,
              compares it across 44 metrics, and an advisor-backed model writes CFO-grade takeaways -
              interpretation by AI, every figure grounded in the Call Report.
            </p>
            <div className="pp-hero-actions">
              <a
                className="btn btn-primary"
                style={{ background: accent, color: '#fff' }}
                href={PEER_ANALYSIS_URL}
              >
                Open Peer Lens →
              </a>
              <a className="btn btn-ghost" href={PEER_ANALYSIS_URL}>
                Try the demo
              </a>
            </div>
            <div className="pp-hero-tags">
              {[
                ['44', 'metrics compared'],
                ['~11', 'defensible peers'],
                ['0', 'fabricated figures'],
              ].map(([a, b], i) => (
                <div key={i} className="pp-tag" style={{ '--tc': accent } as React.CSSProperties}>
                  <div className="t">{a}</div>
                  <div className="s">{b}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="pp-hero-art">
            <PeerLensMock />
          </div>
        </div>
      </section>

      <section className="pp-strip">
        <div className="wrap">
          <CapCard
            ix="01"
            title="Agentic peer identification"
            body="An AI agent assembles candidates from FDIC data - asset band, business model, Fed region, proximity - then an advisor model pressure-tests whether the set is defensible. Sweep and trust banks are screened out; swap any member by hand."
            accent={accent}
          />
          <CapCard
            ix="02"
            title="44 regulatory metrics"
            body="Scale, profitability, funding, capital, and asset quality - FDIC Call Report-derived and bank-level. Computed in code, not guessed, for clean comparability."
            accent="var(--accent-slate)"
          />
          <CapCard
            ix="03"
            title="Direction-aware"
            body="Efficiency, cost of funds, NIE/assets, and charge-offs read better-when-lower. Percentile is position, not virtue."
            accent={accent}
          />
          <CapCard
            ix="04"
            title="AI analysis, grounded"
            body="An AI analyst - an executor model with a stronger advisor - writes mechanism-level findings, watch items, and caveats. Every figure is cited from the computed stats; the model never invents one."
            accent="var(--accent-plum)"
          />
        </div>
      </section>

      <section className="pp-rm-statements" id="methods">
        <div className="wrap">
          <div className="pp-split-head">
            <Eyebrow op="OP_PRLN_02">How the peer set is built</Eyebrow>
            <h2 className="pp-h2">
              Regulatory-first, screened for outliers,
              <br />
              and{' '}
              <span className="ital" style={{ color: accent }}>
                defensible to a CFO.
              </span>
            </h2>
          </div>
          <p className="pp-lede" style={{ marginTop: 24, maxWidth: '70ch' }}>
            Start from FDIC BankFind. An agent screens candidates to a 0.5x-2.0x asset band, gates on
            business model and Fed region, ranks by proximity, and an advisor model checks the set&apos;s
            defensibility - sweep and trust banks fall into a tray you can pull back in. The metrics are
            computed in code and grounded in the Call Report; the AI interprets them, it never invents a
            number.
          </p>
        </div>
      </section>

      <PPFlow
        op="OP_PRLN_03"
        title={
          <>
            Pick.{' '}
            <span className="ital" style={{ color: accent }}>
              Compare.
            </span>{' '}
            Read.
          </>
        }
        steps={[
          {
            n: '01',
            t: 'Pick a target',
            b: 'Type a bank name or FDIC CERT. Ambiguous names disambiguate by certificate.',
          },
          {
            n: '02',
            t: 'Agent builds the set',
            b: 'An AI agent proposes a defensible ~11-bank group and an advisor model pressure-tests it; remove, swap, or pull screened-out banks back in.',
          },
          {
            n: '03',
            t: 'Read the AI analysis',
            b: 'Percentile strips, a performance-frontier scatter, and AI-written CFO-grade findings - every figure traced to FDIC.',
          },
        ]}
        accent={accent}
      />

      <PPCta
        title={
          <>
            Benchmark a bank <span className="ital">in under a minute.</span>
          </>
        }
        sub="Peer Lens replaces the hand-built comp sheet with agentic peer identification and AI analysis, grounded in regulatory data."
        primary="Open Peer Lens"
        primaryHref={PEER_ANALYSIS_URL}
        secondary="Read the methods"
        secondaryHref="/product/peer-analysis#methods"
        accent={accent}
      />
    </main>
  )
}

function LatticeMockLive() {
  return (
    <div className="prx-mock">
      <div className="prx-chrome">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <div className="url">lattice.ace / RM 1 · Consolidated View</div>
        <div className="tag" style={{ color: 'var(--accent-2)' }}>
          ● PRO-FORMA · READY
        </div>
      </div>
      <div className="prx-body">
        <div className="prx-head">
          <div>
            <div className="k">CUMULATIVE PAYBACK</div>
            <div className="v">1y 5mo</div>
            <div className="sub">Payback achieved on Sep 2027</div>
          </div>
          <div className="prx-pills">
            <span>BASE</span>
            <span className="on">BULL</span>
            <span>BEAR</span>
          </div>
        </div>
        <PrxChart />
        <div className="prx-kpis">
          {[
            ['ROE', '5.40%', 'var(--accent-2)'],
            ['ROA', '4.39%', 'var(--accent-slate)'],
            ['NIM', '6.65%', 'var(--accent-2)'],
            ['EFF', '26.2%', 'var(--accent-plum)'],
          ].map(([k, v, c], i) => (
            <div key={i} className="k" style={{ '--c': c } as React.CSSProperties}>
              <div className="l">{k}</div>
              <div className="n">{v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function PrxChart() {
  const width = 540
  const height = 180
  const months = 72
  const points: number[] = []
  for (let i = 0; i <= months; i += 1) {
    const t = i / months
    const v = -500 + 3000 * (t * t * 1.2) + Math.sin(i * 0.7) * 30
    points.push(v)
  }
  const min = Math.min(...points)
  const max = Math.max(...points)
  const y = (v: number) => height - ((v - min) / (max - min)) * (height - 20) - 10
  const xStep = width / months
  const line = points.reduce(
    (d, v, i) => `${d}${i ? ` L ${i * xStep} ${y(v)}` : `M ${i * xStep} ${y(v)}`}`,
    '',
  )
  const area = `${line} L ${months * xStep} ${height} L 0 ${height} Z`

  let cross = 0
  for (let i = 0; i < points.length - 1; i += 1) {
    if (points[i] < 0 && points[i + 1] >= 0) cross = i
  }
  const cx = cross * xStep
  const cy = y(0)

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
      <line x1="0" y1={y(0)} x2={width} y2={y(0)} stroke="currentColor" strokeOpacity="0.2" strokeDasharray="3 4" />
      <path d={area} fill="var(--accent-2)" fillOpacity="0.12" />
      <path d={line} fill="none" stroke="var(--accent-2)" strokeWidth="1.8" />
      <path
        d={`M 0 ${y(0)} L ${cx} ${y(0)} L ${cx} ${height} L 0 ${height} Z`}
        fill="var(--accent-plum)"
        fillOpacity="0.14"
      />
      <circle cx={cx} cy={cy} r="4" fill="var(--accent-2)" />
      <line x1={cx} y1={y(0)} x2={cx} y2="10" stroke="var(--accent-2)" strokeOpacity="0.6" strokeDasharray="2 3" />
      <text
        x={cx + 6}
        y="16"
        fontFamily="JetBrains Mono, monospace"
        fontSize="10"
        fill="var(--accent-2)"
        letterSpacing="0.1em"
      >
        SEP 2027
      </text>
      <text
        x="4"
        y="16"
        fontFamily="JetBrains Mono, monospace"
        fontSize="9"
        fill="currentColor"
        fillOpacity="0.5"
        letterSpacing="0.12em"
      >
        CUMULATIVE PROFIT
      </text>
    </svg>
  )
}

function RmIncomeStatement() {
  const cols = ['2026', '2027', '2028', '2029', '2030', '2031', 'Total']
  const rows: Array<[string, string[]]> = [
    [
      'Total Interest Income',
      ['$46,604', '$238,459', '$494,235', '$802,699', '$1,159,920', '$464,885', '$3,245,298'],
    ],
    ['Interest Expense', ['$2,972', '$16,714', '$38,041', '$67,098', '$104,267', '$42,943', '$272,035']],
    ['Non-Interest Income', ['$1,130', '$6,168', '$12,751', '$20,414', '$28,964', '$11,641', '$42,572']],
    ['Total Revenue', ['$47,734', '$244,627', '$506,986', '$823,113', '$1,188,884', '$476,526', '$3,014,295']],
    ['Non-Interest Expense', ['$78,000', '$119,498', '$122,902', '$126,409', '$130,022', '$43,956', '$620,787']],
    ['Provision Expense', ['$13,333', '$27,500', '$37,500', '$47,500', '$57,500', '$20,000', '$203,333']],
  ]
  const netIncome = ['-$46,593', '$80,794', '$308,296', '$581,716', '$896,551', '$369,410', '$2,190,174']
  const ratios: Array<[string, string[]]> = [
    ['Efficiency Ratio', ['174.34%', '52.46%', '26.22%', '16.73%', '11.99%', '10.14%', '48.65%']],
    ['Return on Assets', ['-4.39%', '2.30%', '4.39%', '5.28%', '5.82%', '2.01%', '23.30%']],
    ['Return on Equity', ['-5.30%', '2.80%', '5.40%', '6.54%', '7.27%', '2.52%', '28.98%']],
    ['Net Interest Margin', ['4.20%', '6.47%', '6.65%', '6.83%', '7.02%', '2.35%', '31.51%']],
  ]

  return (
    <div className="rm-is">
      <div className="rm-is-head">
        <div className="caption">INCOME STATEMENT · PROJECTED</div>
        <div className="legend">
          <span style={{ background: 'var(--accent-2)' }} />
          NET POSITIVE &nbsp;·&nbsp;
          <span style={{ background: 'var(--accent-plum)' }} />
          NET NEGATIVE
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            {cols.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, vals]) => (
            <tr key={label}>
              <td className="m">{label}</td>
              {vals.map((v, i) => (
                <td key={`${label}-${i}`}>{v}</td>
              ))}
            </tr>
          ))}
          <tr className="tot">
            <td className="m">Net Income</td>
            {netIncome.map((v, i) => (
              <td
                key={i}
                style={{
                  color: v.startsWith('-') ? 'var(--accent-plum)' : 'var(--accent-2)',
                  fontWeight: 600,
                }}
              >
                {v}
              </td>
            ))}
          </tr>
          <tr className="sep">
            <td colSpan={cols.length + 1} />
          </tr>
          {ratios.map(([label, vals]) => (
            <tr key={label} className="ratio">
              <td className="m">{label}</td>
              {vals.map((v, i) => (
                <td key={`${label}-${i}`}>{v}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Text2SqlProductDetailPage() {
  return (
    <main className="pp pp-t2s">
      <ProductSubnav />

      <section className="pp-hero pp-hero-dark">
        <div className="wrap pp-hero-grid">
          <div className="pp-hero-copy">
            <div className="pp-eyebrow">
              <span className="op" style={{ color: 'var(--accent)' }}>
                OP_DLCT
              </span>
              <span className="pill">text2sql.aceanalytics.dev</span>
            </div>
            <h1 className="pp-h1">
              Ask in English.
              <br />
              Get <span className="ital" style={{ color: 'var(--accent)' }}>production SQL.</span>
            </h1>
            <p className="pp-lede">
              Dialect routes your question through nine specialized agents - intent, context,
              schema, planner, writer, validator - before any LLM writes a line of SQL.
            </p>
            <div className="pp-hero-actions">
              <a
                className="btn btn-primary"
                style={{ background: 'var(--accent)', color: '#111' }}
                href={TEXT2SQL_APP_URL}
              >
                Try a query →
              </a>
              <a className="btn btn-ghost" href={TEXT2SQL_GUIDED_MODE_URL}>
                Open Guided Mode
              </a>
            </div>
            <div className="pp-hero-tags">
              {[
                ['9 agents', 'purpose-built'],
                ['Schema-valid', 'every output'],
                ['Self-correcting', 'repair loop'],
              ].map(([a, b], i) => (
                <div key={i} className="pp-tag" style={{ '--tc': 'var(--accent)' } as React.CSSProperties}>
                  <div className="t">{a}</div>
                  <div className="s">{b}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="pp-hero-art">
            <DialectMockLive />
          </div>
        </div>
      </section>

      <section className="pp-t2s-pipe" id="methods">
        <div className="wrap">
          <div className="pp-split-head">
            <Eyebrow op="OP_DLCT_02">The 9-agent pipeline</Eyebrow>
            <h2 className="pp-h2" style={{ color: 'var(--accent-bg-ink,#EBEBEB)' }}>
              Nine agents.
              <br />
              <span className="ital" style={{ color: 'var(--accent)' }}>
                One question.
              </span>
            </h2>
          </div>
          <AgentPipeline />
        </div>
      </section>

      <section className="pp-strip pp-strip-dark">
        <div className="wrap">
          <CapCard
            ix="01"
            title="Banking semantic layer"
            body="Domain-specific table descriptions, column relationships, and business glossary baked into every plan."
            accent="var(--accent)"
            dark
          />
          <CapCard
            ix="02"
            title="Context reranking"
            body="Candidate tables and fields are scored by relevance, with dimensional modeling preferences applied."
            accent="var(--accent-orange)"
            dark
          />
          <CapCard
            ix="03"
            title="Self-correcting SQL"
            body="Validation failures trigger an automatic repair loop. Schema errors are fixed before you see them."
            accent="var(--accent-2)"
            dark
          />
          <CapCard
            ix="04"
            title="Explainable plans"
            body="Every query comes with a step-by-step breakdown of what it does and why each join was chosen."
            accent="var(--accent-slate-2,#6DA3BD)"
            dark
          />
        </div>
      </section>

      <PPFlow
        op="OP_DLCT_03"
        title={
          <>
            Ask.{' '}
            <span className="ital" style={{ color: 'var(--accent)' }}>
              Enrich.
            </span>{' '}
            Execute.
          </>
        }
        accent="var(--accent)"
        dark
        steps={[
          {
            n: '01',
            t: 'Ask in plain English',
            b: 'Type "Show average deposit balance by market for Q4". Intent is classified instantly.',
          },
          {
            n: '02',
            t: 'Multi-agent pipeline',
            b: 'Nine agents collaborate to fetch context, rank fields, plan structure, and validate SQL.',
          },
          {
            n: '03',
            t: 'Execute & visualize',
            b: 'Run against live banking data. Explore results in interactive tables and charts.',
          },
        ]}
      />

      <PPCta
        dark
        title={
          <>
            The best prompt
            <br />
            is <span className="ital">richer context.</span>
          </>
        }
        sub="Dialect ships with the banking semantic layer. Plug in your schema, get answers."
        primary="Open Text2SQL app"
        primaryHref={TEXT2SQL_APP_URL}
        secondary="Read the context paper"
        secondaryHref="/product/text2sql#methods"
        accent="var(--accent)"
      />
    </main>
  )
}

function DialectMockLive() {
  return (
    <div className="dlc-mock">
      <div className="dlc-chrome">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <div className="url">dialect.ace / query_session_0417</div>
        <div className="tag">● CONNECTED · banking_core</div>
      </div>
      <div className="dlc-body">
        <div className="dlc-prompt">
          <span className="label">QUERY</span>
          <span className="q">&quot;Show average deposit balance by market for Q4&quot;</span>
        </div>
        <div className="dlc-plan">
          {[
            ['Intent', 'write_sql · aggregation · time_filter', '12ms'],
            ['Context', '3 tables ranked · 12 fields selected', '45ms'],
            ['Planner', 'GROUP BY market · AVG(balance)', '28ms'],
            ['Validator', 'schema-valid · joins OK', '19ms'],
          ].map(([k, v, t], i) => (
            <div
              key={i}
              className="dlc-row"
              style={{ '--d': `${i * 120}ms` } as React.CSSProperties}
            >
              <div className="agent">{k}</div>
              <div className="detail">{v}</div>
              <div className="t">{t}</div>
            </div>
          ))}
        </div>
        <div className="dlc-sql">
          <div className="label">GENERATED SQL</div>
          <pre>
            <span className="co">-- validated · schema-safe</span>
            {'\n'}
            <span className="kw">SELECT</span> d.market,{'\n'}
            {'       '}
            <span className="fn">AVG</span>(b.balance) <span className="kw">AS</span> avg_deposit
            {'\n'}
            <span className="kw">FROM</span> deposits b{'\n'}
            <span className="kw">JOIN</span> dim_market d <span className="kw">ON</span> b.market_id =
            d.id{'\n'}
            <span className="kw">WHERE</span> b.period_end <span className="kw">BETWEEN</span>{' '}
            <span className="st">&apos;2026-10-01&apos;</span>
            {'\n'}
            {'      '}
            <span className="kw">AND</span> <span className="st">&apos;2026-12-31&apos;</span>
            {'\n'}
            <span className="kw">GROUP BY</span> d.market{'\n'}
            <span className="kw">ORDER BY</span> avg_deposit <span className="kw">DESC</span>;
          </pre>
        </div>
      </div>
    </div>
  )
}

function AgentPipeline() {
  const agents = [
    { n: '01', k: 'Intent', d: 'Classifies request type and required operators' },
    {
      n: '02',
      k: 'Context',
      d: 'Retrieves candidate tables and fields from the semantic layer',
    },
    {
      n: '03',
      k: 'Reranker',
      d: 'Scores candidates, applies dimensional modeling preferences',
    },
    { n: '04', k: 'Glossary', d: 'Maps business terms (ROE, NIM, market) to columns' },
    { n: '05', k: 'Planner', d: 'Decides joins, filters, grouping, and order' },
    { n: '06', k: 'Writer', d: "Emits SQL using the planner's structure" },
    { n: '07', k: 'Validator', d: 'Schema, join, and type checks. Fails closed.' },
    { n: '08', k: 'Repair', d: 'On failure, revises and retries - up to n times' },
    {
      n: '09',
      k: 'Explainer',
      d: 'Produces plan-of-reasoning and cell-level provenance',
    },
  ]
  return (
    <div className="agent-grid">
      {agents.map((agent) => (
        <div key={agent.n} className="agent-card">
          <div className="agent-top">
            <div className="n">{agent.n}</div>
            <div className="k">{agent.k}</div>
          </div>
          <div className="d">{agent.d}</div>
          <div className="bar">
            <span />
          </div>
        </div>
      ))}
    </div>
  )
}

function CapCard({
  ix,
  title,
  body,
  accent,
  dark,
}: {
  ix: string
  title: string
  body: string
  accent: string
  dark?: boolean
}) {
  return (
    <div className={`pp-cap${dark ? ' dark' : ''}`} style={{ '--c': accent } as React.CSSProperties}>
      <div className="ix">{ix}</div>
      <h3>{title}</h3>
      <p>{body}</p>
      <div className="rule" />
    </div>
  )
}

function PPFlow({
  op,
  title,
  steps,
  accent,
  dark,
}: {
  op: string
  title: React.ReactNode
  steps: Array<{ n: string; t: string; b: string }>
  accent: string
  dark?: boolean
}) {
  return (
    <section className={`pp-flow${dark ? ' dark' : ''}`}>
      <div className="wrap">
        <Eyebrow op={op}>Flow</Eyebrow>
        <h2 className="pp-h2" style={{ marginTop: 20 }}>
          {title}
        </h2>
        <div className="pp-flow-grid" style={{ marginTop: 56 }}>
          {steps.map((step, i) => (
            <div key={i} className="pp-step" style={{ '--c': accent } as React.CSSProperties}>
              <div className="n">{step.n}</div>
              <div className="bar" />
              <h4>{step.t}</h4>
              <p>{step.b}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function PPCta({
  title,
  sub,
  primary,
  primaryHref,
  secondary,
  secondaryHref,
  accent,
  dark,
}: {
  title: React.ReactNode
  sub: string
  primary: string
  primaryHref: string
  secondary: string
  secondaryHref: string
  accent: string
  dark?: boolean
}) {
  return (
    <section className={`pp-cta${dark ? ' dark' : ''}`} style={{ '--c': accent } as React.CSSProperties}>
      <div className="wrap">
        <h2>{title}</h2>
        <p>{sub}</p>
        <div className="actions">
          <a
            className="btn btn-primary"
            style={{ background: accent, color: dark ? '#111' : undefined }}
            href={primaryHref}
          >
            {primary} →
          </a>
          <a className="btn btn-ghost" href={secondaryHref}>
            {secondary}
          </a>
        </div>
      </div>
    </section>
  )
}
