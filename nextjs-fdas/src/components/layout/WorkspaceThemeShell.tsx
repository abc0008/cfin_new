'use client'

import { useEffect, useState, type ReactNode } from 'react'

type Direction = 'A' | 'B'

const getStoredDirection = (): Direction => {
  if (typeof window === 'undefined') return 'A'
  const saved = window.localStorage.getItem('ace.direction')
  return saved === 'B' ? 'B' : 'A'
}

export function WorkspaceThemeShell({ children }: { children: ReactNode }) {
  const [direction, setDirection] = useState<Direction>('A')

  useEffect(() => {
    setDirection(getStoredDirection())

    const handleDirectionChange = (event: Event) => {
      const customEvent = event as CustomEvent<{ direction?: Direction }>
      const nextDirection = customEvent.detail?.direction
      if (nextDirection === 'A' || nextDirection === 'B') {
        setDirection(nextDirection)
        return
      }
      setDirection(getStoredDirection())
    }

    const handleStorage = (event: StorageEvent) => {
      if (!event.key || event.key === 'ace.direction') {
        setDirection(getStoredDirection())
      }
    }

    window.addEventListener('ace-direction-change', handleDirectionChange)
    window.addEventListener('storage', handleStorage)
    return () => {
      window.removeEventListener('ace-direction-change', handleDirectionChange)
      window.removeEventListener('storage', handleStorage)
    }
  }, [])

  useEffect(() => {
    const body = document.body
    body.classList.add('workspace-theme-active')
    return () => {
      body.classList.remove('workspace-theme-active')
      body.removeAttribute('data-direction')
    }
  }, [])

  useEffect(() => {
    document.body.setAttribute('data-direction', direction)
  }, [direction])

  return (
    <div className="workspace-theme-shell" data-direction={direction}>
      {children}
    </div>
  )
}
