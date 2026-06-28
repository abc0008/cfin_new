'use client'

import Link from 'next/link'
import { type CSSProperties, useEffect, useMemo, useRef, useState } from 'react'
import { ClosingCTA, Eyebrow, MarketingFooter, useReveal } from '@/components/marketing/shared'
import { BOOK_DEMO_URL } from '@/lib/app-urls'
import { PROTOTYPE_TOOLS } from '@/components/marketing/home-prototype'
import { EncryptedText } from '@/components/ui/encrypted-text'

export function ProductPrototypePage() {
  const [active, setActive] = useState(0)
  const [tabsStuck, setTabsStuck] = useState(false)
  const wrapRef = useRef<HTMLDivElement | null>(null)
  const tabsRef = useRef<HTMLDivElement | null>(null)
  useReveal(wrapRef)

  useEffect(() => {
    let frame = 0

    const updateStickyState = () => {
      frame = 0
      if (!tabsRef.current) return
      const isStuck = tabsRef.current.getBoundingClientRect().top <= 74
      setTabsStuck((prev) => (prev === isStuck ? prev : isStuck))
    }

    const scheduleUpdate = () => {
      if (frame) return
      frame = window.requestAnimationFrame(updateStickyState)
    }

    updateStickyState()
    window.addEventListener('scroll', scheduleUpdate, { passive: true })
    window.addEventListener('resize', scheduleUpdate)

    return () => {
      if (frame) {
        window.cancelAnimationFrame(frame)
      }
      window.removeEventListener('scroll', scheduleUpdate)
      window.removeEventListener('resize', scheduleUpdate)
    }
  }, [])

  const activeTool = PROTOTYPE_TOOLS[active]

  const featureRows = useMemo(
    () => [
      [
        ['Scenario trees', 'Fork BASE into BULL and BEAR without losing references.'],
        ['Breakeven finder', 'Solve for month, price, cost line, or CAC with dynamic recalibration.'],
        ['Excel bridge', 'Two-way sync with workbook ranges so teams keep existing process muscle.'],
        ['Uncertainty bands', 'Forecasts ship with confidence intervals, not single-point narratives.'],
      ],
      [
        ['Schema-aware', 'Fine-tuned on bank chart-of-accounts and FR Y-14 style structures.'],
        ['Validated first', 'Planner checks types, joins, and PII access before execution.'],
        ['Read, not write', 'No DDL, no DML. IAM governed and SIEM logged.'],
        ['Natural handoff', 'Attach generated SQL to Jira, export to Excel, or paste into committee memos.'],
      ],
      [
        ['Confidence-scored', 'Every extracted field carries a p-score tied back to its source page and bounding box.'],
        ['Filings-native', 'Trained on 10-K, 10-Q, S-1, and private PCAP decks. Knows XBRL, knows footnotes.'],
        ['Diff mode', 'Compare quarter to quarter, year to year, peer to peer - with explanations a junior analyst can defend.'],
        ['Committee-ready', 'Export to Excel, PDF, or push straight to your deal memo. Audit trail attached, always.'],
      ],
      [
        ['OCR for reality', 'Handles scans, photos, stamps, handwriting, and the occasional coffee stain.'],
        ['Credit spreading', 'Outputs a clean spread with DSCR, LTV, FCC, and debt/EBITDA ready for committee.'],
        ['Covenant engine', 'Tracks covenants and flags breaches under stress scenarios before signature.'],
        ['Tax return savvy', 'Understands 1040, 1041, 1065, 1120, K-1s, and reconciles personal to business flows.'],
      ],
      [
        ['GL actuals baseline', 'Pulls GL_Fact, entity, and GL account history into a 60-month starting plan.'],
        ['Scenario layering', 'Macro, workforce, producer hiring, credit, liquidity, and expense levers recompute live.'],
        ['Guardrail monitor', 'Capital, liquidity, and appetite metrics show healthy, watch, and breach ranges by year.'],
        ['Forecast cube load', 'Approved plans write back as governed scenario versions with user lineage.'],
      ],
      [
        ['Agentic peer set', 'An AI agent assembles candidates by asset band, model, and Fed region; an advisor model pressure-tests the set. Sweep and trust banks auto-screened, swappable by hand.'],
        ['44 regulatory metrics', 'Scale, profitability, funding, capital, and asset quality - FDIC Call Report-derived and computed in code for clean comparability.'],
        ['Direction-aware reads', 'Efficiency, cost of funds, NIE/assets, and charge-offs scored better-when-lower. Percentile is position, not virtue.'],
        ['AI takeaways, grounded', 'An AI analyst writes mechanism-level findings, watch items, and caveats - every figure cited from the computed stats, never invented.'],
      ],
    ],
    [],
  )

  const features = featureRows[active]

  return (
    <div className="route" ref={wrapRef}>
      <section style={{ paddingTop: 140, paddingBottom: 60 }}>
        <div className="wrap">
          <Eyebrow op="/ PRODUCT">The toolkit</Eyebrow>
          <h1 className="display h1" style={{ marginTop: 40 }}>
            Six tools.
            <br />
            Each one a
            <br />
            <span className="ital" style={{ color: 'var(--accent-orange)' }}>
              scalpel.
            </span>
          </h1>
        </div>
      </section>

      <div className={`prod-tabs prod-tabs-toolkit${tabsStuck ? ' is-stuck' : ''}`} ref={tabsRef}>
        <div className="wrap">
          <div className="prod-tabs-ops" aria-hidden={tabsStuck}>
            {PROTOTYPE_TOOLS.map((tool, index) => (
              <div key={`${tool.code}-op`} className="prod-tabs-op">
                <EncryptedText
                  text={`${tool.op} · ${tool.code}`}
                  className="prod-tabs-op-text"
                  encryptedClassName="enc"
                  revealedClassName="rev"
                  revealDelayMs={82}
                  flipDelayMs={60}
                  startDelayMs={index * 1100}
                  trigger={!tabsStuck}
                />
              </div>
            ))}
          </div>
          <div className="prod-tabs-buttons">
            {PROTOTYPE_TOOLS.map((tool, index) => (
              <button
                key={tool.code}
                className={`p${index === active ? ' on' : ''}`}
                onClick={() => setActive(index)}
                style={
                  {
                    '--tab-accent': tool.color,
                    '--tab-fg': '#ffffff',
                  } as CSSProperties
                }
              >
                <span className="nm">{tool.name}</span>
                <span className="tg">{tool.tag}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <section style={{ padding: '100px 0 120px' }}>
        <div className="wrap">
          <div className="grid-2">
            <div>
              <Eyebrow op={activeTool.op}>{activeTool.tag}</Eyebrow>
              <div
                style={{
                  fontSize: 'clamp(80px, 10vw, 140px)',
                  fontWeight: 600,
                  letterSpacing: '-0.04em',
                  lineHeight: 0.9,
                  marginTop: 28,
                  color: activeTool.color,
                }}
              >
                {activeTool.name}
              </div>
              <p className="lede" style={{ marginTop: 28, fontSize: 22 }}>
                {activeTool.desc}
              </p>
              <div style={{ display: 'flex', gap: 12, marginTop: 36, flexWrap: 'wrap' }}>
                <Link
                  className="btn btn-primary"
                  style={{
                    background: activeTool.color,
                    color: activeTool.color === 'var(--accent)' ? '#111' : '#fff',
                  }}
                  href={activeTool.route}
                >
                  Visit {activeTool.name.toLowerCase()} →
                </Link>
                <a className="btn btn-ink" href={BOOK_DEMO_URL}>
                  Book a demo <span className="arr" />
                </a>
                <Link className="btn btn-ghost" href={activeTool.methodsRoute}>
                  Read the methods
                </Link>
              </div>
            </div>
            <div>{activeTool.mock()}</div>
          </div>
        </div>
      </section>

      <section style={{ padding: '40px 0 0' }}>
        <div className="wrap">
          <div className="feat-4">
            {features.map(([title, body], index) => (
              <div className="cell" key={index} data-reveal>
                <div className="ix">{String(index + 1).padStart(2, '0')}</div>
                <h5>{title}</h5>
                <p>{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="flow">
        <div className="wrap">
          <Eyebrow op="OP_B">Flow</Eyebrow>
          <h2
            style={{
              fontSize: 'clamp(48px, 7vw, 96px)',
              fontWeight: 600,
              letterSpacing: '-0.04em',
              lineHeight: 0.95,
              marginTop: 24,
            }}
          >
            Connect, query, <span className="ital">done.</span>
          </h2>
          <div className="cards">
            {[
              ['01', 'Connect', 'Upload filings, point at a warehouse, or drop a CSV. Three minutes from zero to ready.'],
              ['02', 'Calibrate', 'Run your known-good set. See confidence scores per field. Tune the thresholds you trust.'],
              ['03', 'Query', 'Ask in plain English. Drop a PDF. Build a scenario. Every answer includes its source and plan.'],
              ['04', 'Commit', 'Export to Excel, push to your warehouse, attach to the deal memo. Audit trail in every step.'],
            ].map(([num, title, body]) => (
              <div className="card" key={num}>
                <div>
                  <div className="n">{num}</div>
                </div>
                <h5>
                  {title}
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 400,
                      color: 'var(--ink-2)',
                      marginTop: 12,
                      letterSpacing: 0,
                    }}
                  >
                    {body}
                  </div>
                </h5>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section style={{ padding: '120px 0' }}>
        <div className="wrap">
          <div className="grid-2-even">
            <div>
              <Eyebrow op="OP_C">Specs</Eyebrow>
              <h2
                style={{
                  fontSize: 'clamp(48px, 6.5vw, 88px)',
                  fontWeight: 600,
                  letterSpacing: '-0.04em',
                  lineHeight: 0.95,
                  marginTop: 24,
                }}
              >
                The things nobody asks about <span className="ital">until they matter.</span>
              </h2>
            </div>
            <div className="specs">
              {[
                ['Warehouses', 'Snowflake · Databricks · BigQuery · Redshift · Postgres'],
                ['Export', 'Excel · CSV · Parquet · Arrow · direct push'],
                ['Auth', 'SSO · SAML 2.0 · SCIM provisioning · MFA required'],
                ['Compliance', 'SOC 2 Type II · GLBA · CCPA · data residency opt-in'],
                ['Deployment', 'Managed SaaS · private cloud · on-prem (air-gapped)'],
                ['Latency', 'p50 340ms · p99 1.2s · streaming fallback'],
                ['Models', 'Claude 3.7 · GPT-5 · self-hosted Llama · fine-tuned bank schemas'],
                ['SLA', '99.95% · 4h response · 30d change window'],
              ].map(([key, value]) => (
                <div className="row" key={key}>
                  <div className="k">{key}</div>
                  <div className="v">{value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <ClosingCTA />
      <MarketingFooter />
    </div>
  )
}
