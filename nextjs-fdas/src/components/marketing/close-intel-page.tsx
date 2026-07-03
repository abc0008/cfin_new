'use client'

import { type CSSProperties, type ReactNode, useEffect, useState } from 'react'

import { ProductSubnav } from '@/components/marketing/shared'
import { CLOSE_INTEL_URL } from '@/lib/app-urls'

type Phase = 0 | 1 | 2

const findings = [
  ['Retail', 'FDIC assessment', 'z +4.8', '92'],
  ['Ops', 'Software renewal', 'z +3.9', '81'],
  ['Treasury', 'Deposit beta', 'z -3.1', '74'],
  ['Mortgage', 'Fee income', 'z +2.8', '69'],
]

const monthPairs = [
  ['MAY', 'JUN'],
  ['JUN', 'JUL'],
]

export function CloseIntelProductDetailPage() {
  return (
    <main className="pp pp-rm">
      <ProductSubnav />

      <section className="pp-hero">
        <div className="wrap pp-hero-grid">
          <div className="pp-hero-copy">
            <div className="pp-eyebrow">
              <span className="op" style={{ color: 'var(--accent-blue)' }}>
                OP_CLSI
              </span>
              <span className="pill">aceanalytics.dev / close-intel</span>
            </div>
            <h1 className="pp-h1">
              The close that
              <br />
              <span className="ital" style={{ color: 'var(--accent-blue)' }}>
                writes itself.
              </span>
            </h1>
            <p className="pp-lede">
              A continuous monitoring agent watches the GL between closes - baselined by account,
              cost center, and month-of-year. You teach it what is real in minutes. At month-end, a
              guarded narrator turns penny-tied variance bridges into board-grade commentary where
              every number is computed and every judgment cites its source.
            </p>
            <div className="pp-hero-actions">
              <a
                className="btn btn-primary"
                style={{ background: 'var(--accent-blue)', color: '#fff' }}
                href={CLOSE_INTEL_URL}
              >
                Open Close Intel →
              </a>
              <a className="btn btn-ghost" href="/product/close-intel/guide">
                Read the guide
              </a>
            </div>
            <div className="pp-hero-tags">
              {[
                ['21,585', 'GL cells scored in ~50s'],
                ['592', 'penny-tied variance bridges'],
                ['0', 'LLM-computed numbers'],
              ].map(([a, b], i) => (
                <div key={i} className="pp-tag" style={{ '--tc': 'var(--accent-blue)' } as CSSProperties}>
                  <div className="t">{a}</div>
                  <div className="s">{b}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="pp-hero-art">
            <CloseIntelMock />
          </div>
        </div>
      </section>

      <section className="pp-strip" id="methods">
        <div className="wrap">
          <CapCard
            ix="01"
            title="The agent notices"
            body="Robust month-of-year baselines per GL account × cost center, plus a leg against the active forecast version. Score = statistical surprise × dollar materiality × relevance weight."
            accent="var(--accent-blue)"
          />
          <CapCard
            ix="02"
            title="You teach it"
            body="Disposition each finding - real, noise, known-recurring - with a note. Rules draft themselves; you activate. Agent memory stays visible, and month N+1 provably behaves differently."
            accent="var(--accent-2)"
          />
          <CapCard
            ix="03"
            title="The narrator delivers"
            body="Rate/volume/mix, headcount×rate, and level bridges that tie to the penny feed cited commentary - per line, per LOB, and a company summary judged against expectation bands."
            accent="var(--accent-plum)"
          />
          <CapCard
            ix="04"
            title="The guard enforces"
            body="Every numeric token in every narrative string-matches a deterministically computed figure, or a deterministic fallback ships instead. The discipline is code, not a prompt."
            accent="var(--accent-orange)"
          />
        </div>
      </section>

      <section className="cid-section">
        <div className="wrap">
          <div className="cid-eyebrow">CI_D1</div>
          <h2 className="pp-h2">
            Notice. Teach. Narrate.{' '}
            <span className="ital" style={{ color: 'var(--accent-blue)' }}>
              Repeat, smarter.
            </span>
          </h2>
          <p className="cid-caption">
            One loop per month. The agent notices intra-month, the analyst teaches it what&apos;s
            real, and at close the narrator writes commentary where every number is computed and
            every judgment is grounded. The teaching returns to the top of next month&apos;s loop -
            that&apos;s the compounding.
          </p>
          <CloseIntelCycleDiagram />
          <p className="cid-caption cid-caption-after">
            Blue chips mark the deterministic layer - the math the narrator is never allowed to do
            for itself. The dashed blue return edge is the product: a disposition in month N
            provably changes month N+1 behavior.
          </p>
        </div>
      </section>

      <section className="cid-section">
        <div className="wrap">
          <div className="cid-eyebrow">CI_D2</div>
          <h2 className="pp-h2">Zero LLM-computed numbers.</h2>
          <p className="cid-caption">
            The claim the whole product stands on, drawn as the pipeline that enforces it.
          </p>
          <CloseIntelRailDiagram />
        </div>
      </section>

      <PPFlow
        op="OP_CLSI_03"
        title={
          <>
            Notice.{' '}
            <span className="ital" style={{ color: 'var(--accent-blue)' }}>
              Teach.
            </span>{' '}
            Narrate.
          </>
        }
        steps={[
          {
            n: '01',
            t: 'Run the monitor',
            b: 'Scheduled or on demand: 21,585 cells baselined and scored; suppression rules applied with attribution; the top findings briefed by a guarded model.',
          },
          {
            n: '02',
            t: 'Disposition in minutes',
            b: 'Real, noise, or known-recurring - with a note. Drafted rules wait for your activation; every verdict becomes retrieval memory.',
          },
          {
            n: '03',
            t: 'Run the close',
            b: 'Bridges compute, expectations judge, the narrator writes, the guard verifies. The board page renders commentary with citation chips down to the GL transaction.',
          },
        ]}
        accent="var(--accent-blue)"
      />

      <PPCta
        title={
          <>
            Notice everything.
            <br />
            Explain <span className="ital">every dollar.</span>
          </>
        }
        sub="Close Intel gives FP&A a monitor that never sleeps, a memory that compounds, and commentary the board can trust to the penny."
        primary="Open Close Intel"
        primaryHref={CLOSE_INTEL_URL}
        secondary="Read the methods"
        secondaryHref="/product/close-intel#methods"
        accent="var(--accent-blue)"
      />
    </main>
  )
}

export function CloseIntelMock({ isActive = true }: { isActive?: boolean }) {
  const [phase, setPhase] = useState<Phase>(2)
  const [monthIndex, setMonthIndex] = useState(0)
  const [reducedMotion, setReducedMotion] = useState(false)

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReducedMotion(media.matches)

    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    if (reducedMotion || !isActive) return

    setPhase(0)
    const interval = window.setInterval(() => {
      setPhase((current) => {
        if (current === 2) {
          setMonthIndex((index) => (index + 1) % monthPairs.length)
          return 0
        }
        return (current + 1) as Phase
      })
    }, 2800)

    return () => window.clearInterval(interval)
  }, [isActive, reducedMotion])

  const [month, nextMonth] = monthPairs[monthIndex]
  const visiblePhase = reducedMotion ? 2 : phase

  return (
    <div className="prx-mock cid-mock">
      <div className="prx-chrome cid-mock-chrome">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <div className="url">close-intel.ace / {month} 2026 · CLOSE</div>
        <div className="tag" style={{ color: 'var(--accent-blue)' }}>
          ● MONITOR · LIVE <span className="cid-month-tick">{month} → {nextMonth}</span>
        </div>
      </div>
      <div className={`prx-body cid-mock-body${reducedMotion ? ' cid-reduced' : ''}`}>
        <div className="cid-phase-stack">
          <MockNoticePhase active={visiblePhase === 0} reduced={reducedMotion} />
          <MockTeachPhase active={visiblePhase === 1} reduced={reducedMotion} />
          <MockNarratePhase active={visiblePhase === 2} reduced={reducedMotion} />
        </div>
        <div className="cid-phase-indicator" aria-label="Close Intel loop phase">
          {['NOTICE', 'TEACH', 'NARRATE'].map((label, index) => (
            <span key={label} className={visiblePhase === index ? 'on' : ''}>
              {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

function MockNoticePhase({ active, reduced }: { active: boolean; reduced: boolean }) {
  return (
    <div className={phaseClass(active, reduced)}>
      <div className="cid-phase-label">NOTICE</div>
      <div className="cid-ledger">
        {findings.map(([entity, gl, z, score], index) => (
          <div
            key={`${entity}-${gl}`}
            className={`cid-ledger-row${index === 0 ? ' hot' : ''}`}
            style={{ transitionDelay: active ? `${index * 80}ms` : '0ms' }}
          >
            <span>{entity}</span>
            <span>{gl}</span>
            <span>{z}</span>
            <span>{score}</span>
          </div>
        ))}
      </div>
      <div className="cid-findings-foot">
        <span>candidates 21,585</span>
        <span>→</span>
        <span>findings 100</span>
      </div>
    </div>
  )
}

function MockTeachPhase({ active, reduced }: { active: boolean; reduced: boolean }) {
  return (
    <div className={phaseClass(active, reduced)}>
      <div className="cid-phase-label">TEACH</div>
      <div className="cid-disposition-card">
        <div className="cid-disposition-top">
          <span className="cid-verdict">KNOWN-RECURRING</span>
          <span>Retail · FDIC assessment · score 92</span>
        </div>
        <div className="cid-note">annual FDIC true-up - every June</div>
      </div>
      <div className="cid-rule-row">RULE · annual · month 06 · active</div>
      <div className="cid-memory">
        <span>AGENT MEMORY</span>
        <span className={active ? 'from off' : 'from'}>suppressed 0</span>
        <span className={active ? 'to on' : 'to'}>suppressed 1</span>
      </div>
    </div>
  )
}

function MockNarratePhase({ active, reduced }: { active: boolean; reduced: boolean }) {
  return (
    <div className={phaseClass(active, reduced)}>
      <div className="cid-phase-label">NARRATE</div>
      <div className="cid-commentary-card">
        <p className={`cid-commentary-text${active ? ' on' : ''}`}>
          Deposits ran $35.9MM favorable - as flagged and dispositioned on the 3rd. Efficiency
          ratio 57.9%, within the 54-63% band.
        </p>
        <div className="cid-citations" aria-label="Narrative citations">
          {['BRIDGE', 'FINDING', 'DISPOSITION', 'EXPECTATION'].map((chip) => (
            <span key={chip}>[{chip}]</span>
          ))}
        </div>
      </div>
      <div className="cid-guard">GUARD ✓ 10/10 narratives</div>
    </div>
  )
}

function phaseClass(active: boolean, reduced: boolean) {
  return `cid-phase${active ? ' on' : ''}${reduced ? ' reduced' : ''}`
}

function CloseIntelCycleDiagram() {
  const stations = [
    {
      op: 'CI_01 · MONITOR',
      title: 'Agent notices',
      body: 'Baselines per GL account × cost center × month-of-year, and vs the active forecast version. Score = surprise × dollar materiality × relevance.',
      kind: 'deterministic',
      className: 'det',
    },
    {
      op: 'CI_01 · JUDGE',
      title: 'Findings briefed',
      body: 'Each surviving finding classified - timing, posting error, real change, known-recurring - citing the GL transactions. Numbers are provided, never computed.',
      kind: 'guarded LLM',
      className: 'llm',
    },
    {
      op: 'CI_02 · TEACH',
      title: 'Analyst dispositions',
      body: 'Real, noise, or known-recurring - with a note. Noise drafts a suppression rule; every verdict becomes retrieval context. Agent memory is visible.',
      kind: 'analyst',
      className: 'human',
    },
    {
      op: 'CI_04-05 · NARRATE',
      title: 'Close writes itself',
      body: 'Penny-tied variance bridges + expectations bands feed cited, board-grade commentary - “as flagged and dispositioned on the 3rd.”',
      kind: 'guarded LLM',
      className: 'llm',
    },
  ]

  return (
    <div className="cid-cycle">
      <div className="cid-ring">
        {stations.map((station) => (
          <div className="cid-station" key={station.op}>
            <div className="op">{station.op}</div>
            <div className="t">{station.title}</div>
            <div className="d">{station.body}</div>
            <span className={`kind ${station.className}`}>{station.kind}</span>
          </div>
        ))}
      </div>
      <div className="cid-return">
        <svg viewBox="0 0 1000 56" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <marker
              id="cid-ret"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto"
            >
              <path d="M0 0L10 5L0 10z" fill="currentColor" />
            </marker>
          </defs>
          <path
            d="M965 4 V30 H38 V10"
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            strokeDasharray="7 6"
            markerEnd="url(#cid-ret)"
          />
        </svg>
        <span className="lbl">
          rules suppress · dispositions become retrieval context → month N+1 starts smarter
        </span>
        <span className="cid-month">
          MAY → JUN → JUL · suppressed <b>0 → 1 → …</b>
        </span>
      </div>
    </div>
  )
}

function CloseIntelRailDiagram() {
  return (
    <div className="cid-rail">
      <div className="cellb">
        <div className="h">Deterministic engines compute</div>
        <div className="s">
          Baselines, scores, 592 penny-tied bridge components, expectation verdicts - SQL and
          Python only.
        </div>
        <div className="mono-line">rate/volume/mix · headcount×rate · residual ties to $0.00</div>
      </div>
      <div className="vb">
        <span className="verb">figures provided to</span>
        <span className="arr">→</span>
      </div>
      <div className="cellb panelb">
        <div className="h">The narrator writes</div>
        <div className="s">
          Sonnet drafts per-line, per-LOB, and company commentary - quoting only the exact
          formatted figures it was handed.
        </div>
        <div className="mono-line">&quot;USE THESE EXACT FIGURES&quot; · one guarded retry</div>
      </div>
      <div className="vb">
        <span className="verb">string-matched by</span>
        <span className="arr">→</span>
      </div>
      <div className="cellb">
        <div className="h">The guard verifies</div>
        <div className="s">
          Every numeric token in every narrative must match a computed figure - or the deterministic
          fallback ships instead.
        </div>
        <div className="mono-line">
          close 6693b249 · 10/10 narratives <span className="ok">guard_pass = true</span>
        </div>
      </div>
    </div>
  )
}

function CapCard({
  ix,
  title,
  body,
  accent,
}: {
  ix: string
  title: string
  body: string
  accent: string
}) {
  return (
    <div className="pp-cap" style={{ '--c': accent } as CSSProperties}>
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
}: {
  op: string
  title: ReactNode
  steps: Array<{ n: string; t: string; b: string }>
  accent: string
}) {
  return (
    <section className="pp-flow">
      <div className="wrap">
        <div className="eyebrow">
          <span style={{ color: 'var(--ink-2)' }}>{op}</span>
          <span style={{ opacity: 0.4 }}>·</span>
          <span>Flow</span>
        </div>
        <h2 className="pp-h2" style={{ marginTop: 20 }}>
          {title}
        </h2>
        <div className="pp-flow-grid" style={{ marginTop: 56 }}>
          {steps.map((step, i) => (
            <div key={i} className="pp-step" style={{ '--c': accent } as CSSProperties}>
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
}: {
  title: ReactNode
  sub: string
  primary: string
  primaryHref: string
  secondary: string
  secondaryHref: string
  accent: string
}) {
  return (
    <section className="pp-cta" style={{ '--c': accent } as CSSProperties}>
      <div className="wrap">
        <h2>{title}</h2>
        <div>
          <p>{sub}</p>
          <div className="actions">
            <a className="btn btn-primary" style={{ background: accent, color: '#fff' }} href={primaryHref}>
              {primary} →
            </a>
            <a className="btn btn-ghost" href={secondaryHref}>
              {secondary}
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
