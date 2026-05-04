'use client'

import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

type TypewriterEffectProps = {
  text: string
  run?: boolean
  typingSpeedMs?: number
  startDelayMs?: number
  className?: string
  liveClassName?: string
  ghostClassName?: string
  cursorClassName?: string
  onComplete?: () => void
}

export function TypewriterEffect({
  text,
  run = true,
  typingSpeedMs = 30,
  startDelayMs = 0,
  className,
  liveClassName,
  ghostClassName,
  cursorClassName,
  onComplete,
}: TypewriterEffectProps) {
  const [visibleChars, setVisibleChars] = useState(run ? 0 : text.length)
  const [cursorVisible, setCursorVisible] = useState(true)
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
    let startTimeout: number | null = null
    let typeTimeout: number | null = null

    const type = () => {
      if (cancelled) return
      setVisibleChars((prev) => {
        const next = prev + 1
        if (next >= text.length) {
          if (!hasCompletedRef.current) {
            hasCompletedRef.current = true
            onCompleteRef.current?.()
          }
          return text.length
        }
        typeTimeout = window.setTimeout(type, typingSpeedMs)
        return next
      })
    }

    hasCompletedRef.current = false
    setVisibleChars(0)
    startTimeout = window.setTimeout(type, Math.max(0, startDelayMs))

    return () => {
      cancelled = true
      if (startTimeout !== null) window.clearTimeout(startTimeout)
      if (typeTimeout !== null) window.clearTimeout(typeTimeout)
    }
  }, [run, startDelayMs, text, typingSpeedMs])

  return (
    <span className={cn(className)}>
      <span className={cn(ghostClassName)} aria-hidden="true">
        {text}
      </span>
      <span className={cn(liveClassName)} aria-label={text} role="text">
        {text.slice(0, visibleChars)}
        <span className={cn(cursorClassName, cursorVisible ? 'on' : '')} />
      </span>
    </span>
  )
}
