'use client'

import { useEffect, useMemo, useState } from 'react'

export function MarketPanel() {
  const [tick, setTick] = useState(0)
  const [candles, setCandles] = useState(() => generateCandles(1337))

  useEffect(() => {
    const interval = setInterval(() => {
      setTick((value) => value + 1)
    }, 11000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (tick === 0) return
    setCandles(generateCandles(1337 + tick))
  }, [tick])

  const last = candles[candles.length - 1]
  const price = last.c.toFixed(2)
  const previousOpen = candles[0].o
  const change = (last.c - previousOpen).toFixed(2)
  const changePct = (((last.c - previousOpen) / previousOpen) * 100).toFixed(2)

  const symbols = [
    { s: 'ACE.OP', p: price, d: `+${changePct}%`, up: true },
    { s: 'APRT', p: '412.08', d: '+1.24%', up: true },
    { s: 'PRLX', p: '198.52', d: '+0.88%', up: true },
    { s: 'LTTC', p: '188.40', d: '-0.42%', up: false },
    { s: 'DLCT', p: '276.15', d: '+2.06%', up: true },
    { s: 'NDX', p: '22,418.6', d: '+0.31%', up: true },
    { s: 'VIX', p: '14.08', d: '-2.11%', up: false },
    { s: 'DXY', p: '103.87', d: '+0.18%', up: true },
  ]

  const orderBook = useMemo(() => {
    const mid = last.c
    return generateOrderBook(mid, 2027 + tick)
  }, [last.c, tick])

  const maxSize = Math.max(...orderBook.map((row) => Math.max(row.bidSize, row.askSize)))

  return (
    <div className="mkt">
      <div className="ticker-strip">
        {symbols.map((symbol) => (
          <div key={symbol.s}>
            <div className="sym">{symbol.s}</div>
            <div className="px">{symbol.p}</div>
            <div className={`delta ${symbol.up ? 'up' : 'dn'}`}>
              {symbol.up ? '▲' : '▼'} {symbol.d}
            </div>
          </div>
        ))}
      </div>
      <div className="body">
        <div className="left-pane">
          <div className="hdr">
            <div>
              <div className="sym-head">ACE.OP · ACE OPERATIONS INDEX</div>
              <div className="price-big">{price}</div>
              <div className="chg">
                <span>
                  ▲ {change} · +{changePct}%
                </span>
                <span className="livepill">
                  <span className="d" />
                  LIVE
                </span>
              </div>
            </div>
          </div>
          <div className="ranges">
            <span>1D</span>
            <span>1W</span>
            <span className="active">1M</span>
            <span>1Y</span>
            <span>5Y</span>
          </div>
          <div className="chart-wrap">
            <Chart candles={candles} />
          </div>
          <div className="kpi-row">
            <div>
              <div className="k">OPEN</div>
              <div className="v">{candles[0].o.toFixed(2)}</div>
            </div>
            <div>
              <div className="k">HIGH</div>
              <div className="v">{Math.max(...candles.map((c) => c.h)).toFixed(2)}</div>
            </div>
            <div>
              <div className="k">LOW</div>
              <div className="v">{Math.min(...candles.map((c) => c.l)).toFixed(2)}</div>
            </div>
            <div>
              <div className="k">VOL</div>
              <div className="v">1.48M</div>
            </div>
            <div>
              <div className="k">AVG</div>
              <div className="v">
                {(candles.reduce((total, candle) => total + candle.c, 0) / candles.length).toFixed(2)}
              </div>
            </div>
          </div>
        </div>
        <div className="right-pane">
          <div className="l2-head">
            <span>ORDER BOOK · L2</span>
            <span>BID · ASK</span>
          </div>
          <div className="l2">
            {orderBook.map((row, index) => (
              <div className="l2-row" key={index}>
                <div className="bid">
                  <span className="bar b" style={{ width: `${(row.bidSize / maxSize) * 50}%` }} />
                  {row.bidP}
                </div>
                <div className="ask">
                  <span className="bar a" style={{ width: `${(row.askSize / maxSize) * 50}%` }} />
                  {row.askP}
                </div>
              </div>
            ))}
          </div>
          <div className="spread">
            <span>SPREAD</span>
            <span>0.04 · 0.01%</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function createRng(seed: number) {
  let state = seed >>> 0
  return () => {
    state = (1664525 * state + 1013904223) >>> 0
    return state / 4294967296
  }
}

function generateOrderBook(mid: number, seed: number) {
  const rand = createRng(seed)
  const rows: { bidP: string; askP: string; bidSize: number; askSize: number }[] = []
  for (let i = 0; i < 14; i += 1) {
    const bidP = (mid - 0.03 - i * 0.02).toFixed(2)
    const askP = (mid + 0.02 + i * 0.02).toFixed(2)
    rows.push({
      bidP,
      askP,
      bidSize: Math.floor(300 + rand() * 3200),
      askSize: Math.floor(300 + rand() * 3200),
    })
  }
  return rows
}

function generateCandles(seed: number) {
  const rand = createRng(seed)
  const output: { o: number; h: number; l: number; c: number }[] = []
  let price = 148 + rand() * 4
  for (let i = 0; i < 46; i += 1) {
    const open = price
    const drift = (rand() - 0.47) * 1.8
    const close = open + drift
    const high = Math.max(open, close) + rand() * 1.2
    const low = Math.min(open, close) - rand() * 1.2
    output.push({ o: open, h: high, l: low, c: close })
    price = close
  }
  return output
}

function Chart({ candles }: { candles: Array<{ o: number; h: number; l: number; c: number }> }) {
  const width = 720
  const height = 220
  const count = candles.length
  const values = candles.flatMap((candle) => [candle.h, candle.l])
  const min = Math.min(...values) - 0.5
  const max = Math.max(...values) + 0.5
  const stepX = width / count
  const bodyWidth = stepX * 0.55
  const y = (value: number) => height - ((value - min) / (max - min)) * (height - 20) - 10

  const points = candles.map((candle, index) => [index * stepX + stepX / 2, y(candle.c)] as const)
  const linePath = smoothPath(points)
  const areaPath = `${linePath} L ${width},${height} L 0,${height} Z`

  const maPoints = candles.map((_, index) => {
    const window = candles.slice(Math.max(0, index - 6), index + 1)
    const average = window.reduce((sum, candle) => sum + candle.c, 0) / window.length
    return [index * stepX + stepX / 2, y(average)] as const
  })
  const maPath = smoothPath(maPoints)

  const last = candles[count - 1]
  const lastX = (count - 1) * stepX + stepX / 2
  const lastY = y(last.c)

  return (
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      {[0.25, 0.5, 0.75].map((ratio, index) => (
        <line
          key={index}
          x1={0}
          x2={width}
          y1={height * ratio}
          y2={height * ratio}
          stroke="currentColor"
          strokeOpacity="0.14"
          strokeDasharray="2 4"
        />
      ))}
      <path d={areaPath} fill="#FFAC03" fillOpacity="0.10" />
      <path d={linePath} fill="none" stroke="#FFAC03" strokeWidth="1.4" strokeOpacity="0.55" />
      {candles.map((candle, index) => {
        const x = index * stepX + stepX / 2
        const up = candle.c >= candle.o
        const color = up ? '#FFAC03' : 'currentColor'
        const opacity = up ? 0.95 : 0.38
        return (
          <g key={index} opacity={opacity}>
            <line x1={x} x2={x} y1={y(candle.h)} y2={y(candle.l)} stroke={color} strokeWidth="1" />
            <rect
              x={x - bodyWidth / 2}
              y={Math.min(y(candle.o), y(candle.c))}
              width={bodyWidth}
              height={Math.max(1, Math.abs(y(candle.o) - y(candle.c)))}
              fill={color}
            />
          </g>
        )
      })}
      <path d={maPath} fill="none" stroke="#FFAC03" strokeWidth="1.2" strokeDasharray="4 3" opacity="0.8" />
      <line x1={lastX} x2={lastX} y1={0} y2={height} stroke="#FFAC03" strokeOpacity="0.22" strokeWidth="1" />
      <rect x={width - 56} y={lastY - 10} width={54} height={20} rx={10} fill="#FFAC03" />
      <text
        x={width - 29}
        y={lastY + 4}
        textAnchor="middle"
        fontSize="11"
        fontFamily="JetBrains Mono, monospace"
        fill="#111"
        fontWeight="600"
      >
        {last.c.toFixed(2)}
      </text>
    </svg>
  )
}

function smoothPath(points: readonly (readonly [number, number])[]) {
  if (points.length === 0) return ''
  let d = `M ${points[0][0]} ${points[0][1]}`
  for (let i = 1; i < points.length; i += 1) {
    const [x0, y0] = points[i - 1]
    const [x1, y1] = points[i]
    const cx = (x0 + x1) / 2
    d += ` Q ${cx} ${y0}, ${cx} ${(y0 + y1) / 2} T ${x1} ${y1}`
  }
  return d
}
