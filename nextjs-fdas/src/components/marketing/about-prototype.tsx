'use client'

import Image from 'next/image'
import { useEffect, useRef, useState } from 'react'
import { Eyebrow, MarketingFooter, useReveal } from '@/components/marketing/shared'

const TIMELINE_ENTRIES = [
  {
    years: '2025-Present',
    title: 'Director, Enterprise Analytics',
    company: 'Synovus + Pinnacle Integration',
    logo: '/assets/logos/pinnacle.jpeg',
    logoAlt: 'Pinnacle Financial Partners logo',
    banner: '/assets/logos/synovus-pinnacle-banner.jpeg',
    bannerAlt:
      'Southeastern U.S. footprint with Pinnacle Financial Partners and Synovus branding',
    body: 'Building a centralized enterprise analytics function for a combined $117B bank and translating that craft into product.',
    points: ['Team of 9 analysts/developers', 'Instrument-level finance models', 'Executive scorecards + advisor insights'],
  },
  {
    years: '2023-2025',
    title: 'Director, Strategic Finance',
    company: 'Synovus',
    logo: '/assets/logos/synovus-logo.jpeg',
    logoAlt: 'Synovus logo',
    body: 'Supported wholesale and treasury leadership while scaling performance analytics across business lines.',
    points: ['Segment-level finance leadership', 'Platform stewardship', 'Commercial + treasury coverage'],
  },
  {
    years: '2022-2023',
    title: 'Senior FP&A Manager',
    company: 'Synovus',
    logo: '/assets/logos/synovus-logo.jpeg',
    logoAlt: 'Synovus logo',
    body: 'Shipped a production analytics platform connecting ERP and GL data into usable operating intelligence.',
    points: ['Power BI + SQL platform', 'Faster time-to-insight', 'Enterprise data model groundwork'],
  },
  {
    years: '2014-2022',
    title: 'VP, Manager of Financial Analytics',
    company: 'First Horizon (formerly IBERIABANK)',
    logo: '/assets/logos/first-horizon-logo.jpeg',
    logoAlt: 'First Horizon logo',
    body: 'Scaled from analyst to manager and rebuilt the team around forward-looking profitability analytics.',
    points: ['Led analyst teams', 'Executive decision support', 'Modernized reporting stack'],
  },
  {
    years: '2013-2014',
    title: 'Asset Liability Analyst',
    company: 'Regions Financial',
    logo: '/assets/logos/regions-logo.jpeg',
    logoAlt: 'Regions logo',
    body: 'Moved into ALM and owned portions of NII and balance-sheet forecasting under multiple rate regimes.',
    points: ['CCAR support', 'Interest-rate risk simulation', 'Consolidated planning'],
  },
  {
    years: '2011-2013',
    title: 'Finance Development Program',
    company: 'Regions Financial',
    logo: '/assets/logos/regions-logo.jpeg',
    logoAlt: 'Regions logo',
    body: 'Built baseline muscle across treasury, investor relations, and portfolio analytics in a rotational seat.',
    points: ['Cross-functional rotations', 'Forecasting and reporting discipline', 'Early executive exposure'],
  },
] as const

export function AboutPrototypePage() {
  const wrapRef = useRef<HTMLDivElement | null>(null)
  const timelineRef = useRef<HTMLDivElement | null>(null)
  const cardRefs = useRef<Array<HTMLElement | null>>([])
  const [beamProgress, setBeamProgress] = useState(0)
  const [activeCard, setActiveCard] = useState(0)

  useReveal(wrapRef)

  useEffect(() => {
    let frame = 0

    const clamp = (value: number) => Math.min(1, Math.max(0, value))

    const updateBeam = () => {
      const timelineNode = timelineRef.current
      if (!timelineNode) return

      const rect = timelineNode.getBoundingClientRect()
      const anchor = window.innerHeight * 0.44
      const progress = clamp((anchor - rect.top) / Math.max(rect.height, 1))
      setBeamProgress(progress)

      let nextActive = 0
      cardRefs.current.forEach((card, index) => {
        if (!card) return
        if (card.getBoundingClientRect().top <= anchor + 18) {
          nextActive = index
        }
      })
      setActiveCard(nextActive)
    }

    const scheduleUpdate = () => {
      cancelAnimationFrame(frame)
      frame = window.requestAnimationFrame(updateBeam)
    }

    updateBeam()
    window.addEventListener('scroll', scheduleUpdate, { passive: true })
    window.addEventListener('resize', scheduleUpdate)

    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', scheduleUpdate)
      window.removeEventListener('resize', scheduleUpdate)
    }
  }, [])

  return (
    <div className="route" ref={wrapRef}>
      <section style={{ paddingTop: 140, paddingBottom: 80 }}>
        <div className="wrap">
          <Eyebrow op="/ ABOUT">The person behind the tool</Eyebrow>
          <h1 className="display h1" style={{ marginTop: 40 }}>
            One builder,
            <br />
            <span className="ital">ten years</span>
            <br />
            in the weeds.
          </h1>
        </div>
      </section>

      <section style={{ padding: '40px 0 120px' }}>
        <div className="wrap">
          <div className="grid-2-even" style={{ alignItems: 'start' }}>
            <div className="portrait about-photo">
              <Image
                src="/assets/alex-headshot.png"
                alt="Alex Cardell"
                fill
                sizes="(max-width: 1100px) 100vw, 40vw"
                className="about-photo-img"
                priority
              />
              <div className="about-photo-tag">
                <div className="tag">FIG. 01 · ALEX CARDELL</div>
                <div className="tag" style={{ marginTop: 4, color: 'var(--ink-3)' }}>
                  Finance · Analytics · Product
                </div>
              </div>
            </div>
            <div>
              <div className="about-summary-chip">PROFILE SNAPSHOT</div>
              <h2 className="about-top-name">Alex Cardell</h2>
              <p className="about-top-lede">
                One-part finance operator, one-part builder. I design analytical systems that
                survive real committee pressure and then productize the ones that consistently win.
              </p>
              <div className="about-summary-stats about-summary-stats-wide">
                <div className="row">
                  <span className="k">Experience</span>
                  <span className="v">14+ years</span>
                </div>
                <div className="row">
                  <span className="k">Current</span>
                  <span className="v">Enterprise Analytics Director</span>
                </div>
                <div className="row">
                  <span className="k">Focus</span>
                  <span className="v">Finance transformation + AI products</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="log">
        <div className="wrap">
          <Eyebrow op="OP_L">Log</Eyebrow>
          <h2
            style={{
              fontSize: 'clamp(44px, 6vw, 88px)',
              fontWeight: 600,
              letterSpacing: '-0.04em',
              lineHeight: 0.95,
              marginTop: 24,
              marginBottom: 48,
            }}
          >
            A short, <span className="ital">honest</span> timeline.
          </h2>
          <div className="about-beam-grid" ref={timelineRef}>
            <div className="about-track">
              <span className="about-track-line" />
              <span className="about-track-progress" style={{ height: `${Math.round(beamProgress * 100)}%` }} />
              {TIMELINE_ENTRIES.map((entry, index) => (
                <article
                  key={entry.years}
                  ref={(node) => {
                    cardRefs.current[index] = node
                  }}
                  className={`about-beam-card${index === activeCard ? ' on' : ''}${'banner' in entry && entry.banner ? ' has-banner' : ''}`}
                  data-reveal
                >
                  <span className="about-beam-dot" />
                  {'banner' in entry && entry.banner ? (
                    <div className="about-beam-banner">
                      <Image
                        src={entry.banner}
                        alt={entry.bannerAlt ?? ''}
                        fill
                        sizes="(max-width: 900px) 92vw, 820px"
                        className="about-beam-banner-img"
                        priority={index === 0}
                      />
                      <div className="about-beam-banner-fade" aria-hidden />
                    </div>
                  ) : null}
                  <div className="about-beam-card-main">
                    <div className="about-beam-head">
                      <div className="about-beam-meta">
                        <span className="about-year">{entry.years}</span>
                        <span className="about-company">{entry.company}</span>
                      </div>
                      <div className="about-beam-logo">
                        <Image
                          src={entry.logo}
                          alt={entry.logoAlt}
                          width={56}
                          height={40}
                          className="about-beam-logo-img"
                        />
                      </div>
                    </div>
                    <h3>{entry.title}</h3>
                    <p>{entry.body}</p>
                    <ul>
                      {entry.points.map((point) => (
                        <li key={point}>{point}</li>
                      ))}
                    </ul>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section style={{ padding: '120px 0' }}>
        <div className="wrap">
          <Eyebrow op="OP_V">Values</Eyebrow>
          <h2
            style={{
              fontSize: 'clamp(40px, 5vw, 72px)',
              fontWeight: 600,
              letterSpacing: '-0.03em',
              lineHeight: 1,
              marginTop: 20,
              marginBottom: 48,
            }}
          >
            Three things I <span className="ital">won&apos;t trade.</span>
          </h2>
          <div className="values">
            {[
              ['01', 'Slow enough to get it right.', "Every release is benchmarked against its last self. If it's slower, more wrong, or harder to audit - it doesn't ship."],
              ['02', 'No generic models.', 'A fine-tuned model on your schema beats a frontier model every time. I fine-tune. I do not wrap.'],
              ['03', 'Your data stays home.', 'Private cloud, on-prem, or air-gapped. Your filings never leave your perimeter unless you send them.'],
            ].map(([ix, title, body]) => (
              <div className="vcard" key={ix} data-reveal>
                <div>
                  <div className="ix">{ix}</div>
                  <h4 style={{ marginTop: 24 }}>{title}</h4>
                </div>
                <p style={{ fontSize: 15, color: 'var(--ink-2)', lineHeight: 1.5, marginTop: 20 }}>{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="contact-band">
        <div className="wrap">
          <div className="grid-2-even" style={{ alignItems: 'center' }}>
            <div>
              <div className="mono" style={{ color: '#B8B8B8' }}>
                ● OP_C1 · CONTACT
              </div>
              <h2 style={{ marginTop: 20 }}>
                Say hello.
                <br />
                <span className="ital">I reply.</span>
              </h2>
            </div>
            <div className="rows">
              {[
                { label: 'Email', value: 'hello@aceanalytics.dev', href: 'mailto:hello@aceanalytics.dev' },
                { label: 'Office', value: 'Birmingham, AL · 33.519°N 86.810°W' },
                { label: 'Press', value: 'press@aceanalytics.dev', href: 'mailto:press@aceanalytics.dev' },
                { label: 'Calendar', value: 'cal.aceanalytics.dev/demo', href: 'https://cal.aceanalytics.dev/demo' },
              ].map((item) => (
                <div className="row" key={item.label}>
                  <div className="k">{item.label}</div>
                  <div className="v">
                    {item.href ? (
                      <a href={item.href} style={{ color: 'inherit', textDecoration: 'underline' }}>
                        {item.value}
                      </a>
                    ) : (
                      item.value
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  )
}
