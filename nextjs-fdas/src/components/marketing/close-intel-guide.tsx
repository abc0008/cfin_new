import type { CSSProperties, ReactNode } from 'react'

import { Eyebrow, ProductSubnav } from '@/components/marketing/shared'

const CLOSE_INTEL_APP_URL = 'https://bankanalysis.aceanalytics.dev/forecasting/close-intel'
const ACCENT_BLUE = 'var(--accent-blue, #4b7fe0)'

const textRows = [
  [
    'Where it lives',
    'Close Intel is a tab suite inside the Forecasting module: CI_01 Monitor · CI_02 Agent memory · CI_03 Expectations · CI_04 Close run · CI_05 Board page.',
  ],
  [
    'What it reads',
    'GL actuals at cost-center grain, the active forecast cycle versions, the instrument tape, and the HR roster - all seeded in the demo environment.',
  ],
  [
    'What it never does',
    'Compute a number with an LLM. Every figure in every narrative is string-match verified against the deterministic engines.',
  ],
] as const

const steps = [
  {
    n: '01',
    t: 'Run the monitor',
    b: 'CI_01 → Run monitor. About a minute later the findings queue lands, sorted by score. Expand a row: actual vs baseline vs forecast, the score factors, and the GL transactions behind the cell.',
  },
  {
    n: '02',
    t: 'Judge the top findings',
    b: 'Judge batch briefs the highest-scoring findings: a classification (timing, posting error, real change, known-recurring), a criticality, and a one-paragraph brief citing specific transactions.',
  },
  {
    n: '03',
    t: 'Teach with a disposition',
    b: 'Pick a finding you recognize - say the annual FDIC true-up. Disposition it known-recurring with a note. A suppression rule drafts itself, scoped to the account, entity, and month.',
  },
  {
    n: '04',
    t: 'Activate the rule',
    b: 'CI_02 Agent memory shows the drafted rule with your note attached. Toggle it active. Re-run the monitor: the item is suppressed, attributed to your rule - suppressed count 0 → 1.',
  },
  {
    n: '05',
    t: 'Run the close',
    b: 'CI_04 → Run close for the period. The bridges compute (rate/volume/mix where the tape supports it, headcount×rate for comp, level plus a residual that ties to the penny), then the narrator writes.',
  },
  {
    n: '06',
    t: 'Read the board page',
    b: 'CI_05 renders the P&L with expandable commentary. Every paragraph carries citation chips - bridge, finding, disposition, comment, expectation. Click through: chip → bridge waterfall → GL transactions.',
  },
] as const

const citationRows = [
  [
    'BRIDGE',
    'A deterministic variance component - click for the waterfall and the calc inputs (balances, rates, source: tape / gl_implied / roster).',
  ],
  ['FINDING', 'A monitor finding for the period, with its score decomposition and underlying transactions.'],
  [
    'DISPOSITION',
    'Your verdict and note, timestamped - the narrator quotes it: "as flagged and dispositioned on the 3rd."',
  ],
  [
    'COMMENT',
    'An intra-month analyst comment on GL line × cost center × period, carried into close context.',
  ],
  [
    'EXPECTATION',
    'The band the variance was judged against - target, tolerance, and verdict (within / above / below).',
  ],
] as const

const goodToKnowRows = [
  [
    'Scope the close',
    'A whole-book close runs long; scope to a division or a few entities for demos - the board page renders whatever the run covered.',
  ],
  [
    'Dry run',
    'Both the monitor and the close accept a dry-run flag: full deterministic math, no LLM, nothing persisted (monitor) - ideal for a first look.',
  ],
  [
    'Guard failures',
    'If a narrative fails the numbers guard twice, a deterministic fallback ships and the row is marked - you will never read an unverified figure.',
  ],
  [
    'Demo data',
    "Instrument tape and expectation seeds are synthetic and labeled as such in data (seed_batch, fdic_seed) - the GL history is the environment's own.",
  ],
] as const

const phases = [
  ['Intra-month', 'weeks 1–4 · scheduled runs'],
  ['Teach', 'minutes per finding'],
  ['Close run', 'close week'],
  ['Board review', 'day 3–5'],
] as const

const swimlanes = [
  {
    owner: 'Agent · deterministic',
    color: ACCENT_BLUE,
    cells: [
      {
        tab: 'CI_01',
        text: 'Runs the monitor: 21,585 cells baselined, scored, thresholded; suppression rules applied with attribution.',
      },
      {
        tab: 'CI_02',
        text: 'Drafts a suppression rule from each noise / known-recurring verdict; files the disposition into memory.',
      },
      {
        tab: 'CI_04',
        text: 'Computes every bridge: rate/volume/mix, headcount×rate, level + residual. Penny-tie enforced.',
      },
      null,
    ],
  },
  {
    owner: 'Analyst · you',
    color: '#2f9e6e',
    cells: [
      {
        tab: 'CI_01',
        text: 'Reviews the findings queue — score factors visible; adds comments on GL line × cost center × period.',
        handoff: true,
      },
      {
        tab: 'CI_01–02',
        text: 'Dispositions each finding — real / noise / known-recurring + note; activates the drafted rule in Agent memory.',
      },
      {
        tab: 'CI_03',
        text: 'Keeps expectations current: efficiency path, NIM band, growth ceilings, unit seasonality notes.',
      },
      {
        tab: 'CI_05',
        text: 'Reads the board page; clicks citation chips → bridge waterfall → the underlying GL transactions.',
        handoff: true,
      },
    ],
  },
  {
    owner: 'Narrator · guarded LLM',
    color: 'var(--ink-2)',
    cells: [
      {
        tab: 'CI_01',
        text: 'Briefs top findings: classification + criticality, citing specific transactions and prior dispositions.',
      },
      null,
      {
        tab: 'CI_04',
        text: 'Writes per-line, per-LOB, and company commentary from provided figures; guard string-matches every number.',
      },
      {
        tab: 'CI_05',
        text: 'Every paragraph carries its citations: bridges, findings, dispositions, comments, expectations.',
      },
    ],
  },
] as const

const verdicts = [
  {
    verdict: 'real',
    color: '#d9534f',
    outcome: (
      <>
        Stays flagged. <b>Cited by the narrator at close</b> — “as flagged and dispositioned on the
        3rd” — and carried as context for related lines.
      </>
    ),
  },
  {
    verdict: 'noise',
    color: 'var(--ink-2)',
    outcome: (
      <>
        Drafts a <b>one-time suppression rule</b> anchored to this period. You activate it; the cell
        won&apos;t resurface for this month&apos;s pattern.
      </>
    ),
  },
  {
    verdict: 'known-recurring',
    color: ACCENT_BLUE,
    outcome: (
      <>
        Drafts an <b>annual rule</b> — “FDIC true-up, every June.” Next year&apos;s June run suppresses it
        automatically, with the rule attributed in the run log.
      </>
    ),
  },
] as const

export function CloseIntelGuidePage() {
  return (
    <main className="pp pp-rm">
      <ProductSubnav />

      <section className="pp-hero">
        <div className="wrap">
          <div style={{ maxWidth: 920 }}>
            <div className="pp-eyebrow">
              <span className="op" style={{ color: ACCENT_BLUE }}>
                OP_CLSI · GUIDE
              </span>
              <span className="pill">close intelligence · user guide</span>
            </div>
            <h1 className="pp-h1">
              Run your first{' '}
              <span className="ital" style={{ color: ACCENT_BLUE }}>
                intelligent close.
              </span>
            </h1>
            <p className="pp-lede" style={{ maxWidth: 760 }}>
              This guide walks the full loop on live data: run the monitor, teach it with a
              disposition, run the close, and read commentary where every number traces to its
              source. Budget twenty minutes the first time; minutes a month after that.
            </p>
            <div className="pp-hero-actions">
              <a className="btn btn-primary" style={primaryButtonStyle} href={CLOSE_INTEL_APP_URL}>
                Open Close Intel →
              </a>
              <a className="btn btn-ghost" href="/product/close-intel">
                Product overview
              </a>
            </div>
          </div>
        </div>
      </section>

      <GuideSection op="G_00" eyebrow="Before you start" title="Before you start">
        <HairlineRows rows={textRows} />
      </GuideSection>

      <GuideSection
        op="G_01"
        eyebrow="The analyst month"
        title={
          <>
            Who does what,{' '}
            <span className="ital" style={{ color: ACCENT_BLUE }}>
              when.
            </span>
          </>
        }
        caption="The guide's spine: three owners, four phases, and the two handoffs that matter — the queue passing to the analyst, and the analyst's teaching passing back to the agent. Dashed cell tops mark ownership transfers."
      >
        <AnalystMonthDiagram />
      </GuideSection>

      <section className="pp-flow">
        <div className="wrap">
          <Eyebrow op="G_02">Step by step</Eyebrow>
          <h2 className="pp-h2" style={{ marginTop: 20 }}>
            Step by step
          </h2>
          <div className="pp-flow-grid" style={{ marginTop: 56 }}>
            {steps.map((step) => (
              <StepCard key={step.n} step={step} />
            ))}
          </div>
        </div>
      </section>

      <GuideSection
        op="G_03"
        eyebrow="The teaching moment"
        title="One verdict, three futures."
        caption="The disposition is the only decision the product asks of you — and each answer changes what the system does next month."
      >
        <TeachingMomentDiagram />
      </GuideSection>

      <GuideSection op="G_04" eyebrow="Reading the citations" title="Reading the citations">
        <HairlineRows rows={citationRows} />
      </GuideSection>

      <GuideSection op="G_05" eyebrow="Good to know" title="Good to know">
        <HairlineRows rows={goodToKnowRows} />
      </GuideSection>

      <section style={closingSectionStyle}>
        <div className="wrap" style={{ textAlign: 'center' }}>
          <h2 className="pp-h2" style={{ margin: '0 auto', maxWidth: 820 }}>
            Twenty minutes to a{' '}
            <span className="ital" style={{ color: ACCENT_BLUE }}>
              smarter close.
            </span>
          </h2>
          <div style={centerActionsStyle}>
            <a className="btn btn-primary" style={primaryButtonStyle} href={CLOSE_INTEL_APP_URL}>
              Open Close Intel →
            </a>
            <a className="btn btn-ghost" href="/product/close-intel">
              Back to product
            </a>
          </div>
        </div>
      </section>
    </main>
  )
}

function GuideSection({
  op,
  eyebrow,
  title,
  caption,
  children,
}: {
  op: string
  eyebrow: string
  title: ReactNode
  caption?: string
  children: ReactNode
}) {
  return (
    <section style={guideSectionStyle}>
      <div className="wrap">
        <Eyebrow op={op}>{eyebrow}</Eyebrow>
        <h2 className="pp-h2" style={{ marginTop: 20 }}>
          {title}
        </h2>
        {caption ? <p style={captionStyle}>{caption}</p> : null}
        <div style={{ marginTop: caption ? 26 : 40 }}>{children}</div>
      </div>
    </section>
  )
}

function HairlineRows({ rows }: { rows: ReadonlyArray<readonly [string, string]> }) {
  return (
    <div style={rowListStyle}>
      {rows.map(([key, value]) => (
        <div key={key} style={hairlineRowStyle}>
          <div className="mono" style={hairlineKeyStyle}>
            {key}
          </div>
          <div style={hairlineValueStyle}>{value}</div>
        </div>
      ))}
    </div>
  )
}

function StepCard({ step }: { step: (typeof steps)[number] }) {
  return (
    <div className="pp-step" style={{ '--c': ACCENT_BLUE } as CSSProperties}>
      <div className="n">{step.n}</div>
      <div className="bar" />
      <h4>{step.t}</h4>
      <p>{step.b}</p>
    </div>
  )
}

function AnalystMonthDiagram() {
  return (
    <div>
      <div className="mono" style={flowLabelStyle}>
        THE MONTH FLOWS →
      </div>
      <div style={{ overflowX: 'auto' }}>
        <div style={phaseMatrixStyle}>
          <div style={matrixRowStyle}>
            <div style={matrixCornerStyle}>Owner ▸ phase</div>
            {phases.map(([phase, cadence]) => (
              <div key={phase} style={phaseHeaderStyle}>
                <div style={phaseNameStyle}>{phase}</div>
                <div className="mono" style={phaseCadenceStyle}>
                  {cadence}
                </div>
              </div>
            ))}
          </div>
          {swimlanes.map((lane) => (
            <div key={lane.owner} style={matrixRowStyle}>
              <div
                style={{
                  ...ownerCellStyle,
                  color: lane.color,
                  borderLeft: `3px solid ${lane.color}`,
                }}
              >
                {lane.owner}
              </div>
              {lane.cells.map((cell, index) => {
                const handoff = isHandoffCell(cell)

                return (
                  <div
                    key={`${lane.owner}-${index}`}
                    style={{
                      ...matrixCellStyle,
                      borderTop: handoff ? `2px dashed ${ACCENT_BLUE}` : `2px solid ${lane.color}`,
                    }}
                  >
                    {cell ? (
                      <>
                        <span className="mono" style={cellTabStyle}>
                          {cell.tab}
                          {handoff ? <span style={{ color: ACCENT_BLUE }}> · HANDOFF</span> : null}
                        </span>
                        {cell.text}
                      </>
                    ) : (
                      <div style={emptyCellRuleStyle} aria-hidden="true" />
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function isHandoffCell(cell: (typeof swimlanes)[number]['cells'][number]) {
  return Boolean(cell && 'handoff' in cell && cell.handoff)
}

function TeachingMomentDiagram() {
  return (
    <div style={decisionDiagramStyle}>
      <div style={questionCardStyle}>
        <div style={{ fontWeight: 600, fontSize: 15 }}>Is this finding real?</div>
        <div style={{ fontSize: 12, color: 'var(--ink-2)', marginTop: 4 }}>
          A note is required either way — your reasoning becomes part of the agent&apos;s retrieval
          memory.
        </div>
      </div>
      <div style={verdictListStyle}>
        {verdicts.map((item) => (
          <div key={item.verdict} style={verdictRowStyle}>
            <div className="mono" style={{ ...verdictLabelStyle, color: item.color }}>
              {item.verdict}
            </div>
            <div style={verdictOutcomeStyle}>{item.outcome}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

const primaryButtonStyle: CSSProperties = {
  background: ACCENT_BLUE,
  color: '#fff',
}

const guideSectionStyle: CSSProperties = {
  padding: '96px 0',
  borderTop: '1px solid var(--line)',
}

const captionStyle: CSSProperties = {
  color: 'var(--ink-2)',
  fontSize: 15,
  lineHeight: 1.5,
  maxWidth: 760,
  marginTop: 14,
}

const rowListStyle: CSSProperties = {
  borderBottom: '1px solid var(--line)',
}

const hairlineRowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(180px, 0.34fr) minmax(0, 1fr)',
  gap: 28,
  padding: '18px 0',
  borderTop: '1px solid var(--line)',
  alignItems: 'start',
}

const hairlineKeyStyle: CSSProperties = {
  color: ACCENT_BLUE,
  fontSize: 11,
}

const hairlineValueStyle: CSSProperties = {
  color: 'var(--ink-2)',
  lineHeight: 1.5,
  fontSize: 16,
}

const flowLabelStyle: CSSProperties = {
  color: 'var(--ink-2)',
  fontSize: 11,
  marginBottom: 8,
}

const phaseMatrixStyle: CSSProperties = {
  border: '1px solid var(--line)',
  borderRadius: 14,
  overflow: 'hidden',
  minWidth: 860,
}

const matrixRowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '170px repeat(4, minmax(170px, 1fr))',
}

const matrixCornerStyle: CSSProperties = {
  background: 'var(--ink)',
  color: 'var(--bg)',
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 10.5,
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  padding: '12px 14px',
  display: 'flex',
  alignItems: 'center',
}

const phaseHeaderStyle: CSSProperties = {
  background: 'var(--panel)',
  padding: '10px 12px',
  borderLeft: '1px solid var(--line)',
}

const phaseNameStyle: CSSProperties = {
  fontWeight: 600,
  fontSize: 13,
}

const phaseCadenceStyle: CSSProperties = {
  fontSize: 10,
  letterSpacing: '0.06em',
  color: 'var(--ink-2)',
  marginTop: 2,
}

const ownerCellStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '12px 14px',
  fontSize: 13,
  fontWeight: 600,
  background: 'var(--panel)',
  borderTop: '1px solid var(--line)',
}

const matrixCellStyle: CSSProperties = {
  borderLeft: '1px solid var(--line)',
  padding: '11px 12px',
  fontSize: 12,
  lineHeight: 1.45,
  color: 'var(--ink)',
  background: 'var(--bg)',
  minHeight: 96,
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
}

const cellTabStyle: CSSProperties = {
  fontSize: 9.5,
  letterSpacing: '0.1em',
  color: 'var(--ink-3)',
  display: 'block',
  marginBottom: 2,
}

const emptyCellRuleStyle: CSSProperties = {
  width: 16,
  height: 2,
  background: 'var(--line)',
  alignSelf: 'center',
}

const decisionDiagramStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 24,
  alignItems: 'flex-start',
}

const questionCardStyle: CSSProperties = {
  flex: '1 1 240px',
  border: '1px solid var(--line-strong)',
  background: 'var(--panel)',
  padding: 16,
  borderRadius: 14,
}

const verdictListStyle: CSSProperties = {
  flex: '3 1 460px',
  display: 'grid',
  gap: 10,
}

const verdictRowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(140px, 150px) minmax(0, 1fr)',
  border: '1px solid var(--line)',
  background: 'var(--bg)',
}

const verdictLabelStyle: CSSProperties = {
  fontSize: 11,
  letterSpacing: '0.08em',
  padding: '12px 14px',
  borderRight: '1px solid var(--line)',
  display: 'flex',
  alignItems: 'center',
}

const verdictOutcomeStyle: CSSProperties = {
  padding: '12px 14px',
  fontSize: 12.5,
  color: 'var(--ink-2)',
  lineHeight: 1.5,
}

const closingSectionStyle: CSSProperties = {
  padding: '120px 0',
  borderTop: '1px solid var(--line)',
}

const centerActionsStyle: CSSProperties = {
  display: 'flex',
  gap: 12,
  marginTop: 32,
  justifyContent: 'center',
  flexWrap: 'wrap',
}
