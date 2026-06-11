'use client';

import React, { useCallback, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Citation } from '@/types';
import { Table2, AlignLeft, FileText } from 'lucide-react';

interface CitationMarkerProps {
  citation: Citation;
  /** 1-based marker number shown in the superscript pill. */
  index: number;
  onClick?: (citation: Citation) => void;
}

/**
 * Inline citation marker with a hover preview card.
 *
 * Shows the marker number plus the cited page; on hover, reveals the cited
 * text, source document, and whether the highlight is anchored to a financial
 * table cell or narrative prose. The preview renders through a portal with
 * fixed positioning so it is never clipped by chat scroll containers.
 * Clicking jumps the PDF pane to the highlight.
 */
export function CitationMarker({ citation, index, onClick }: CitationMarkerProps) {
  const page = citation.startPageNumber || (citation as any).page;
  const quote = (citation.displayText || citation.citedText || '').trim();
  const sourceType = citation.sourceType;
  const anchorRef = useRef<HTMLAnchorElement | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ left: number; top: number } | null>(null);

  const showTooltip = useCallback(() => {
    const el = anchorRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const width = 260;
    const margin = 8;
    let left = rect.left + rect.width / 2 - width / 2;
    left = Math.max(margin, Math.min(left, window.innerWidth - width - margin));
    setTooltipPos({ left, top: rect.top - margin });
  }, []);

  const hideTooltip = useCallback(() => setTooltipPos(null), []);

  return (
    <>
      <a
        ref={anchorRef}
        href={`#citation-${encodeURIComponent(citation.id)}`}
        className="citation-link inline-flex items-center px-1 py-0.5 mx-0.5 rounded bg-yellow-100 text-yellow-800 hover:bg-yellow-200 border border-yellow-200 cursor-pointer text-xs align-top no-underline"
        data-testid="citation-marker"
        data-citation-id={citation.id}
        onClick={(event) => {
          event.preventDefault();
          hideTooltip();
          onClick?.(citation);
        }}
        onMouseEnter={showTooltip}
        onMouseLeave={hideTooltip}
        onFocus={showTooltip}
        onBlur={hideTooltip}
        aria-label={`Citation ${index}${page ? ` on page ${page}` : ''}: ${quote.substring(0, 60)}`}
      >
        <sup className="font-medium">{index}</sup>
        {page ? (
          <span className="ml-0.5 text-[9px] font-medium opacity-75">p.{page}</span>
        ) : null}
      </a>

      {tooltipPos &&
        typeof document !== 'undefined' &&
        createPortal(
          <span
            className="cfin-citation-tooltip cfin-citation-tooltip--visible"
            role="tooltip"
            style={{
              position: 'fixed',
              left: tooltipPos.left,
              top: tooltipPos.top,
              transform: 'translateY(-100%)',
              width: 260,
            }}
          >
            {quote && <span className="cfin-citation-tooltip-quote">“{quote}”</span>}
            <span className="cfin-citation-tooltip-meta">
              <span className="inline-flex min-w-0 items-center gap-1">
                <FileText className="h-3 w-3 flex-shrink-0" />
                <span className="truncate">
                  {citation.documentTitle || 'Source document'}
                  {page ? ` · p.${page}` : ''}
                </span>
              </span>
              {sourceType === 'table' && (
                <span className="cfin-citation-badge cfin-citation-badge--table">
                  <Table2 className="h-2.5 w-2.5" />
                  Table
                </span>
              )}
              {sourceType === 'text' && (
                <span className="cfin-citation-badge cfin-citation-badge--text">
                  <AlignLeft className="h-2.5 w-2.5" />
                  Text
                </span>
              )}
            </span>
            <span className="mt-1 block text-[10px] text-muted-foreground">
              Click to view in document
            </span>
          </span>,
          document.body
        )}
    </>
  );
}

export default CitationMarker;
