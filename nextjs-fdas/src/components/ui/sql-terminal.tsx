'use client'

import { useEffect, useMemo, useRef, useState } from 'react'

type SqlTokenType = 'kw' | 'fn' | 'st' | 'id' | 'default'

type SqlToken = {
  value: string
  type: SqlTokenType
}

type SqlTerminalProps = {
  text: string
  typingSpeedMs?: number
  startDelayMs?: number
  loop?: boolean
  pauseAfterDoneMs?: number
  run?: boolean
  heightPx?: number
  onComplete?: () => void
}

const SQL_KEYWORDS = new Set([
  'SELECT',
  'FROM',
  'JOIN',
  'ON',
  'AND',
  'WHERE',
  'NOT',
  'IN',
  'GROUP',
  'BY',
  'HAVING',
  'ORDER',
  'ASC',
  'LIMIT',
  'AS',
])

function tokenizeSql(text: string): SqlToken[] {
  const tokens: SqlToken[] = []
  let index = 0

  const push = (value: string, type: SqlTokenType) => {
    if (!value) return
    tokens.push({ value, type })
  }

  while (index < text.length) {
    const char = text[index]

    if (/\s/.test(char)) {
      let end = index + 1
      while (end < text.length && /\s/.test(text[end])) end += 1
      push(text.slice(index, end), 'default')
      index = end
      continue
    }

    if (char === "'") {
      let end = index + 1
      while (end < text.length) {
        if (text[end] === "'") {
          end += 1
          break
        }
        end += 1
      }
      push(text.slice(index, end), 'st')
      index = end
      continue
    }

    if (/[0-9]/.test(char)) {
      let end = index + 1
      while (end < text.length && /[0-9.]/.test(text[end])) end += 1
      push(text.slice(index, end), 'st')
      index = end
      continue
    }

    if (/[A-Za-z_]/.test(char)) {
      let end = index + 1
      while (end < text.length && /[A-Za-z0-9_]/.test(text[end])) end += 1
      const word = text.slice(index, end)
      const upper = word.toUpperCase()

      let lookahead = end
      while (lookahead < text.length && /\s/.test(text[lookahead])) lookahead += 1
      const next = text[lookahead]

      if (SQL_KEYWORDS.has(upper)) {
        push(word, 'kw')
      } else if (next === '(') {
        push(word, 'fn')
      } else {
        push(word, 'id')
      }

      index = end
      continue
    }

    push(char, 'default')
    index += 1
  }

  return tokens
}

export function SqlTerminal({
  text,
  typingSpeedMs = 18,
  startDelayMs = 180,
  loop = false,
  pauseAfterDoneMs = 1200,
  run = true,
  heightPx,
  onComplete,
}: SqlTerminalProps) {
  const [visibleChars, setVisibleChars] = useState(0)
  const [cursorVisible, setCursorVisible] = useState(true)
  const tokens = useMemo(() => tokenizeSql(text), [text])
  const hasCompletedRef = useRef(false)
  const onCompleteRef = useRef(onComplete)

  useEffect(() => {
    onCompleteRef.current = onComplete
  }, [onComplete])

  useEffect(() => {
    const blink = window.setInterval(() => {
      setCursorVisible((value) => !value)
    }, 520)
    return () => window.clearInterval(blink)
  }, [])

  useEffect(() => {
    if (!run) {
      setVisibleChars(0)
      hasCompletedRef.current = false
      return
    }

    let cancelled = false
    let stepTimeout: number | null = null
    let restartTimeout: number | null = null

    const startTyping = () => {
      if (cancelled) return
      setVisibleChars(0)
      hasCompletedRef.current = false

      const tick = () => {
        if (cancelled) return

        setVisibleChars((prev) => {
          const next = prev + 1
          if (next >= text.length) {
            if (!hasCompletedRef.current) {
              hasCompletedRef.current = true
              onCompleteRef.current?.()
            }
            if (loop) {
              restartTimeout = window.setTimeout(startTyping, pauseAfterDoneMs)
            }
            return text.length
          }

          stepTimeout = window.setTimeout(tick, typingSpeedMs)
          return next
        })
      }

      stepTimeout = window.setTimeout(tick, typingSpeedMs)
    }

    restartTimeout = window.setTimeout(startTyping, startDelayMs)

    return () => {
      cancelled = true
      if (stepTimeout !== null) window.clearTimeout(stepTimeout)
      if (restartTimeout !== null) window.clearTimeout(restartTimeout)
    }
  }, [text, typingSpeedMs, startDelayMs, loop, pauseAfterDoneMs, run])

  const lineCount = useMemo(() => Math.max(1, text.split('\n').length), [text])
  const terminalStyle = heightPx
    ? { height: `${heightPx}px`, minHeight: `${heightPx}px` }
    : { minHeight: `${lineCount * 1.6}em` }

  const renderTokens = (charLimit: number) => {
    let remaining = charLimit
    return tokens.map((token, index) => {
      if (remaining <= 0) return null
      const visibleChunk = token.value.slice(0, remaining)
      remaining -= visibleChunk.length
      const className = token.type === 'default' ? undefined : token.type
      return (
        <span key={`${token.type}-${index}-${token.value.length}`} className={className}>
          {visibleChunk}
        </span>
      )
    })
  }

  return (
    <div className="sql-terminal" style={terminalStyle}>
      <pre className="sql-terminal-ghost" aria-hidden="true">
        {renderTokens(text.length)}
      </pre>
      <pre className="sql-terminal-live">
        {renderTokens(visibleChars)}
        <span className={`sql-cursor${cursorVisible ? ' on' : ''}`} />
      </pre>
    </div>
  )
}
