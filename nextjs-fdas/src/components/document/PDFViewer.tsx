'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { File, Loader2, AlertCircle } from 'lucide-react';
import { ProcessedDocument, Citation } from '@/types';
import {
  PdfLoader,
  PdfHighlighter,
  Highlight,
  Popup,
  AreaHighlight,
  IHighlight,
  LTWHP 
} from "react-pdf-highlighter";
import { documentsApi, cleanupBlobUrls } from '@/lib/api/documents';
import { convertCitationToHighlight, convertHighlightToCitation } from '@/lib/pdf/citationService';
import { searchMultiplePages } from '@/lib/pdf/textSearch';

// Add PDF.js type declaration
declare global {
  interface Window {
    pdfjsLib?: any;
  }
}

interface PDFViewerProps {
  document?: ProcessedDocument;
  isLoading?: boolean;
  error?: string;
  onCitationCreate?: (citation: Omit<Citation, 'id'>) => void;
  onCitationClick?: (citation: Citation | IHighlight) => void;
  aiHighlights?: IHighlight[];
  onCitationsLoaded?: (citations: IHighlight[]) => void;
  pdfUrl?: string;
  highlightId?: string | null;
  renderingQuality?: 'low' | 'medium' | 'high';
  pageBufferSize?: number;
  /**
   * Additional citations supplied by the parent (e.g. placeholders created
   * during streaming). They are merged with backend citations when building
   * highlights so scrollToHighlight can work immediately.
   */
  extraCitations?: Citation[];
}

export function PDFViewer({ 
  document, 
  isLoading, 
  error, 
  onCitationCreate, 
  onCitationClick,
  aiHighlights = [], 
  onCitationsLoaded,
  pdfUrl: propsPdfUrl,
  highlightId,
  pageBufferSize = 5,
  extraCitations = []
}: PDFViewerProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [userHighlights, setUserHighlights] = useState<IHighlight[]>([]);
  const [pdfUrl, setPdfUrl] = useState<string | null>(propsPdfUrl || null);
  const [errorState, setErrorState] = useState<string | null>(error || null);
  const [loadingState, setLoadingState] = useState<string | null>(null);
  const [documentCitations, setDocumentCitations] = useState<Citation[]>([]);
  const [searchResolvedCitations, setSearchResolvedCitations] = useState<Citation[]>([]);
  const [totalPages, setTotalPages] = useState<number>(0);
  const [visiblePages, setVisiblePages] = useState<number[]>([]);
  const [loadedPages, setLoadedPages] = useState<Set<number>>(new Set());
  const [renderScale, setRenderScale] = useState<string>('page-fit');
  const [isBrowser, setIsBrowser] = useState(false);
  
  const [currentPdfDocument, setCurrentPdfDocument] = useState<any>(null);
  const scrollViewerRef = useRef<((highlight: IHighlight) => void) | null>(null);
  const cleanupRef = useRef<() => void>(() => {});
  const pendingScrollHighlightIdRef = useRef<string | null>(null);
  const lastScrolledHighlightIdRef = useRef<string | null>(null);
  const lastScrollRefKickTargetRef = useRef<string | null>(null);
  const scrollSessionRef = useRef<{
    targetId: string;
    pageNumber: number;
    pageKickDone: boolean;
    helperKickDone: boolean;
    centerKickDone: boolean;
    sawHighlightElement: boolean;
  } | null>(null);

  const escapeForAttributeSelector = useCallback((value: string) => {
    return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
  }, []);

  const getHighlightElement = useCallback(
    (highlightId: string, pageNumber?: number): HTMLElement | null => {
      const safeId = escapeForAttributeSelector(highlightId);
      const wrappers = Array.from(
        globalThis.document?.querySelectorAll(`.PdfHighlighter [data-highlight-id="${safeId}"]`) || []
      ) as HTMLElement[];

      if (wrappers.length === 0) {
        return null;
      }

      const candidates: HTMLElement[] = [];
      wrappers.forEach((wrapper) => {
        // react-pdf-highlighter renders the painted rectangle in child nodes.
        // The wrapper itself can be zero-sized, so prefer concrete painted parts.
        const parts = wrapper.querySelectorAll('.Highlight__part, .AreaHighlight__part');
        if (parts.length > 0) {
          parts.forEach((part) => candidates.push(part as HTMLElement));
          return;
        }
        candidates.push(wrapper);
      });

      const paintedCandidates = candidates.filter((el) => {
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      });

      const pageScopedCandidates =
        typeof pageNumber === 'number'
          ? paintedCandidates.filter((el) => {
              const pageEl = el.closest('.page[data-page-number]') as HTMLElement | null;
              const pageAttr = pageEl?.getAttribute('data-page-number');
              return pageAttr ? Number(pageAttr) === pageNumber : false;
            })
          : [];

      const searchPool =
        pageScopedCandidates.length > 0
          ? pageScopedCandidates
          : paintedCandidates.length > 0
            ? paintedCandidates
            : candidates;

      // Prefer a currently visible candidate when duplicates exist.
      const viewportHeight =
        globalThis.window?.innerHeight ?? globalThis.document?.documentElement?.clientHeight ?? 0;
      const viewportWidth =
        globalThis.window?.innerWidth ?? globalThis.document?.documentElement?.clientWidth ?? 0;

      const visibleCandidate = searchPool.find((el) => {
        const rect = el.getBoundingClientRect();
        return (
          rect.width > 0 &&
          rect.height > 0 &&
          rect.bottom > 0 &&
          rect.top < viewportHeight &&
          rect.right > 0 &&
          rect.left < viewportWidth
        );
      });
      if (visibleCandidate) {
        return visibleCandidate;
      }

      const mountedCandidate = searchPool.find(
        (el) => el.isConnected && (el.offsetParent !== null || el.getClientRects().length > 0)
      );
      return mountedCandidate || searchPool[0] || null;
    },
    [escapeForAttributeSelector]
  );

  // Pulse the highlight rect(s) after a jump so the analyst's eye lands on the
  // exact cited value instead of hunting through the page.
  const flashHighlight = useCallback((targetHighlightId: string) => {
    const safeId = escapeForAttributeSelector(targetHighlightId);
    const wrappers = Array.from(
      globalThis.document?.querySelectorAll(`.PdfHighlighter [data-highlight-id="${safeId}"]`) || []
    ) as HTMLElement[];
    wrappers.forEach((wrapper) => {
      const parts = wrapper.querySelectorAll('.Highlight__part, .AreaHighlight__part');
      const targets: HTMLElement[] =
        parts.length > 0 ? (Array.from(parts) as HTMLElement[]) : [wrapper];
      targets.forEach((el) => {
        el.classList.remove('cfin-citation-flash');
        // Force reflow so re-adding the class restarts the animation on repeat jumps.
        void el.offsetWidth;
        el.classList.add('cfin-citation-flash');
        globalThis.window?.setTimeout(() => el.classList.remove('cfin-citation-flash'), 2600);
      });
    });
  }, [escapeForAttributeSelector]);

  const isElementVisibleInViewport = useCallback((element: HTMLElement) => {
    const rect = element.getBoundingClientRect();
    const viewportHeight = globalThis.window?.innerHeight ?? globalThis.document?.documentElement?.clientHeight ?? 0;
    const viewportWidth = globalThis.window?.innerWidth ?? globalThis.document?.documentElement?.clientWidth ?? 0;
    const verticallyVisible = rect.bottom > 0 && rect.top < viewportHeight;
    const horizontallyVisible = rect.right > 0 && rect.left < viewportWidth;

    return (
      rect.height > 0 &&
      rect.width > 0 &&
      verticallyVisible &&
      horizontallyVisible
    );
  }, []);

  const scrollElementIntoPdfView = useCallback((element: HTMLElement, block: 'start' | 'center') => {
    const scrollContainer = element.closest('.PdfHighlighter') as HTMLElement | null;
    if (scrollContainer && scrollContainer.scrollHeight > scrollContainer.clientHeight) {
      const containerRect = scrollContainer.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();
      const centerOffset = block === 'center'
        ? (scrollContainer.clientHeight - elementRect.height) / 2
        : 0;
      const targetTop = scrollContainer.scrollTop + elementRect.top - containerRect.top - centerOffset;

      scrollContainer.scrollTo({
        top: Math.max(0, targetTop),
        behavior: 'auto',
      });
      return;
    }

    element.scrollIntoView({ behavior: 'auto', block, inline: 'nearest' });
  }, []);

  const centerElementInView = useCallback((element: HTMLElement) => {
    scrollElementIntoPdfView(element, 'center');
  }, [scrollElementIntoPdfView]);

  // Use pdf.js 2.16.x which matches react-pdf-highlighter's internal version.
  // Provide local worker first, with CDN fallback **of the same version**.
  const [workerUrl, setWorkerUrl] = useState('/pdf.worker.min.js');

  // Merge backend citations with any extra ones from props
  const combinedCitations = React.useMemo(() => {
    const byId = new Map<string, Citation>();
    [...documentCitations, ...extraCitations, ...searchResolvedCitations].forEach((citation) => {
      const existing = byId.get(citation.id);
      if (!existing) {
        byId.set(citation.id, citation);
        return;
      }

      // Prefer whichever version has rect boxes. This avoids stale placeholder
      // citations (no rects) overriding rect-backed citations from backend.
      const existingHasRects = (existing.rects?.length || 0) > 0;
      const incomingHasRects = (citation.rects?.length || 0) > 0;
      if (!existingHasRects && incomingHasRects) {
        byId.set(citation.id, citation);
        return;
      }

      if (existingHasRects && !incomingHasRects) {
        return;
      }

      byId.set(citation.id, {
        ...existing,
        ...citation,
        rects: incomingHasRects ? citation.rects : existing.rects,
      });
    });
    return Array.from(byId.values());
  }, [extraCitations, documentCitations, searchResolvedCitations]);

  // Convert to react-pdf-highlighter format once
  const citationHighlights = React.useMemo(() => {
    console.log('[PDFViewer] Converting citations to highlights:', {
      extraCitations: extraCitations.map(c => ({ id: c.id, text: c.citedText, searchableText: c.searchableText, hasRects: c.rects?.length > 0 })),
      documentCitations: documentCitations.map(c => ({ id: c.id, text: c.citedText, searchableText: c.searchableText, hasRects: c.rects?.length > 0 })),
      combined: combinedCitations.map(c => ({ id: c.id, text: c.citedText, searchableText: c.searchableText, hasRects: c.rects?.length > 0 }))
    });
    return combinedCitations.map(convertCitationToHighlight);
  }, [combinedCitations, extraCitations, documentCitations]);

  // Make highlights inspectable in DevTools when developing
  if (process.env.NODE_ENV !== 'production' && typeof window !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).citationHighlights = citationHighlights;
  }

  // Combine AI-generated highlights with user highlights and citation highlights
  const allHighlights = [...userHighlights, ...aiHighlights, ...citationHighlights];
  const highlightScrollVersion = React.useMemo(
    () =>
      allHighlights
        .map((h) => `${h.id}:${h.position.pageNumber}:${h.position.rects.length}`)
        .join('|'),
    [allHighlights]
  );

  // Keep latest arrays in refs so scroll retry logic can read fresh data without
  // re-starting the retry effect on every highlight/citation state churn.
  const allHighlightsRef = useRef<IHighlight[]>(allHighlights);
  const combinedCitationsRef = useRef<Citation[]>(combinedCitations);

  useEffect(() => {
    allHighlightsRef.current = allHighlights;
  }, [allHighlights]);

  useEffect(() => {
    combinedCitationsRef.current = combinedCitations;
  }, [combinedCitations]);

  useEffect(() => {
    if (!currentPdfDocument) return;
    const transport = currentPdfDocument._transport || currentPdfDocument.transport;
    if (transport && transport.messageHandler === null) return;

    const candidates = combinedCitations.filter(
      citation => !(citation.rects?.length > 0) && (citation.searchableText || citation.citedText)
    );
    if (candidates.length === 0) return;

    let cancelled = false;

    const buildSearchTerms = (citation: Citation) => {
      const citedText = citation.citedText || '';
      const numericTerms = Array.from(citedText.matchAll(/\$?\d[\d,]*(?:\.\d+)?/g))
        .map(match => match[0].replace(/^\$/, ''))
        .filter(term => term.length > 1 && !/^20\d{2}$/.test(term));

      const textTerms = [
        citation.searchableText,
        citation.displayText,
        citedText.split(/\r?\n/).find(line => line.trim().length > 0 && line.trim().length <= 120),
        citedText,
      ].filter((term): term is string => !!term && term.trim().length > 1);

      return Array.from(new Set([...numericTerms, ...textTerms].map(term => term.trim()))).slice(0, 8);
    };

    const resolveMissingRects = async () => {
      const resolved: Citation[] = [];

      for (const citation of candidates) {
        const startPage = citation.startPageNumber || 1;
        const endPage = citation.endPageNumber || startPage;
        const terms = buildSearchTerms(citation);

        for (const term of terms) {
          try {
            const results = await searchMultiplePages(currentPdfDocument, term, startPage, endPage);
            const result = results[0];
            if (!result?.rects?.length) continue;

            const rects = result.rects.map(rect => ({
              ...rect,
              width: rect.x2 - rect.x1,
              height: rect.y2 - rect.y1,
              pageNumber: rect.pageNumber,
            }));

            resolved.push({
              ...citation,
              searchableText: term,
              rects,
            });
            break;
          } catch (error) {
            console.warn('[PDFViewer] Citation text search failed:', { citationId: citation.id, term, error });
          }
        }
      }

      if (cancelled || resolved.length === 0) return;

      setSearchResolvedCitations(prev => {
        const byId = new Map(prev.map(citation => [citation.id, citation]));
        resolved.forEach(citation => byId.set(citation.id, citation));
        return Array.from(byId.values());
      });
    };

    resolveMissingRects();

    return () => {
      cancelled = true;
    };
  }, [combinedCitations, currentPdfDocument]);
  
  // Memory management: Page visibility tracking
  const onVisiblePagesChanged = useCallback((pages?: number[]) => {
    const safePages = Array.isArray(pages) ? pages : [];
    setVisiblePages(safePages);
    
    // Only keep a buffer of pages in memory
    const pagesToKeep = new Set<number>();
    
    // Add currently visible pages
    safePages.forEach(page => pagesToKeep.add(page));
    
    // Add buffer pages (before and after visible pages)
    const halfBuffer = Math.floor(pageBufferSize / 2);
    safePages.forEach(page => {
      for (let i = 1; i <= halfBuffer; i++) {
        if (page - i > 0) pagesToKeep.add(page - i);
        if (page + i <= totalPages) pagesToKeep.add(page + i);
      }
    });
    
    // Update loaded pages state
    setLoadedPages(pagesToKeep);
    
  }, [pageBufferSize, totalPages]);
  
  // Handle PDF document loading completion
  const handleDocumentLoadSuccess = useCallback((pdfDocument: any) => {
    setTotalPages(pdfDocument.numPages);
    
    // Patch getPagesOverview to handle unloaded pages gracefully
    if (typeof window !== 'undefined' && (window as any).PDFViewerApplication) {
      const pdfViewer = (window as any).PDFViewerApplication.pdfViewer;
      if (pdfViewer && pdfViewer.getPagesOverview) {
        const originalGetPagesOverview = pdfViewer.getPagesOverview.bind(pdfViewer);
        pdfViewer.getPagesOverview = function() {
          try {
            // Check if all pages are loaded before calling original method
            const allPagesLoaded = this._pages && this._pages.every((pageView: any) => 
              pageView && pageView.pdfPage
            );
            
            if (!allPagesLoaded) {
              console.warn('[PDFViewer] getPagesOverview called but not all pages are loaded');
              // Return a safe default overview
              return this._pages.map((pageView: any, index: number) => {
                if (pageView && pageView.pdfPage) {
                  const viewport = pageView.pdfPage.getViewport({ scale: 1 });
                  return {
                    width: viewport.width,
                    height: viewport.height,
                    rotation: viewport.rotation || 0
                  };
                }
                // Return default dimensions for unloaded pages
                return {
                  width: 612, // Default US Letter width in points
                  height: 792, // Default US Letter height in points
                  rotation: 0
                };
              });
            }
            
            return originalGetPagesOverview();
          } catch (error) {
            console.error('[PDFViewer] Error in getPagesOverview:', error);
            // Return empty array as fallback
            return [];
          }
        };
      }
    }
    
    // Store cleanup function
    cleanupRef.current = () => {
      // Attempt to clean up PDF.js worker
      if (pdfDocument && typeof pdfDocument.cleanup === 'function') {
        pdfDocument.cleanup();
      }
      
      // Clear page caches and destroy document
      if (pdfDocument && typeof pdfDocument.destroy === 'function') {
        pdfDocument.destroy();
      }
      
      // Additional cleanup for any WebWorkers
      if (window.pdfjsLib && window.pdfjsLib.GlobalWorkerOptions) {
        // Force garbage collection on workers
        console.log('PDF.js workers scheduled for cleanup');
      }
    };
  }, []);
  
  // Define scrollToHighlight callback - IMPORTANT: must be defined before useEffect that uses it
  const scrollToHighlight = useCallback((incomingHighlightId: string | null | undefined) => {
    if (!incomingHighlightId) {
      return false;
    }

    let highlightId = incomingHighlightId;

    // Check temp-to-backend mapping first
    const tempToBackendMap = (window as any).citationTempToBackendMap as Map<string, string>;
    if (tempToBackendMap && tempToBackendMap.has(highlightId)) {
      const backendId = tempToBackendMap.get(highlightId);
      console.log('[PDFViewer] Using temp-to-backend mapping:', {
        tempId: highlightId,
        backendId: backendId
      });
      if (backendId) {
        highlightId = backendId;
      }
    }

    // First try direct match
    let highlight = allHighlightsRef.current.find(h => {
      // Check multiple ID fields to handle temp ID vs UUID mismatch
      const matches = h.id === highlightId || 
        (h.rawClaudeCitation && (h.rawClaudeCitation as any).id === highlightId) ||
        (h.rawClaudeCitation && (h.rawClaudeCitation as any).highlightId === highlightId) ||
        (h.rawClaudeCitation && (h.rawClaudeCitation as any).tempId === highlightId) ||
        (h.rawClaudeCitation && (h.rawClaudeCitation as any).tempHighlightId === highlightId);
      
      if (matches) {
        console.log('[PDFViewer] Found highlight match:', { 
          searchId: highlightId, 
          highlightId: h.id, 
          rawId: (h.rawClaudeCitation as any)?.id,
          rawHighlightId: (h.rawClaudeCitation as any)?.highlightId,
          hasRects: h.position.rects.length
        });
      }
      return matches;
    });
    
    // If not found and it's a temp ID, try fuzzy matching
    if (!highlight && highlightId.startsWith('cite-')) {
      console.log('[PDFViewer] Temp ID not found, trying fuzzy matching...');
      
      // Try to match by page and text content
      const searchForSimilar = () => {
        // Extract page number from existing highlights to narrow search
        for (const h of allHighlightsRef.current) {
          // Check if this might be a match based on content
          if (h.position.rects.length > 0 && h.content.text) {
            // If we have raw citation data with temp IDs, check those
            const raw = h.rawClaudeCitation as any;
            if (raw && (raw.tempId === highlightId || raw.tempHighlightId === highlightId)) {
              return h;
            }
          }
        }
        return null;
      };
      
      highlight = searchForSimilar();
      
      if (highlight) {
        console.log('[PDFViewer] Found highlight via fuzzy match:', {
          tempId: highlightId,
          foundId: highlight.id,
          page: highlight.position.pageNumber,
          rects: highlight.position.rects.length
        });
      }
    }
    
    if (!highlight) {
        console.warn('[PDFViewer] scrollToHighlight failed to find:', {
        searchId: highlightId,
        availableHighlights: allHighlightsRef.current.map(h => ({
          id: h.id,
          rawId: (h.rawClaudeCitation as any)?.id,
          rawHighlightId: (h.rawClaudeCitation as any)?.highlightId,
          page: h.position.pageNumber,
          hasRects: h.position.rects.length
        }))
      });
    } else {
      console.log('[PDFViewer] Find result for', highlightId, ':', { 
        page: highlight.position.pageNumber, 
        rects: highlight.position.rects.length 
      });
    }
    if (highlight) {
      const targetPageNumber = highlight.position?.pageNumber;
      if (!targetPageNumber || Number.isNaN(targetPageNumber)) {
        console.warn('[PDFViewer] Highlight missing valid pageNumber', { highlightId: highlight.id });
      } else {
        const existingSession = scrollSessionRef.current;
        const session =
          existingSession &&
          existingSession.targetId === highlight.id &&
          existingSession.pageNumber === targetPageNumber
            ? existingSession
            : {
                targetId: highlight.id,
                pageNumber: targetPageNumber,
                pageKickDone: false,
                helperKickDone: false,
                centerKickDone: false,
                sawHighlightElement: false,
              };
        scrollSessionRef.current = session;

        const pageSelector = `.PdfHighlighter .page[data-page-number='${targetPageNumber}']`;
        const pageEl = globalThis.document?.querySelector(pageSelector) as HTMLElement | null;
        const hasScrollTarget = !!pageEl;
        if (!session.pageKickDone) {
          console.log('[PDFViewer] Executing citation page kick', {
            targetPageNumber,
            highlightId: highlight.id,
          });
          // Set current page (state) so page number indicator etc updates
          setCurrentPage((prev) => (prev === targetPageNumber ? prev : targetPageNumber));
          session.pageKickDone = true;
          if (pageEl) {
            try {
              scrollElementIntoPdfView(pageEl, 'start');
            } catch (err) {
              console.warn('[PDFViewer] Page kick scroll failed', err);
            }
          }
        }
        const helperSafeToUse =
          !!scrollViewerRef.current &&
          hasScrollTarget &&
          pageEl.offsetParent !== null &&
          !!highlight.position?.boundingRect &&
          Array.isArray(highlight.position?.rects);

        // Prefer library helper only once per target when page container is mounted and visible.
        if (helperSafeToUse && !session.helperKickDone) {
          session.helperKickDone = true;
          try {
            scrollViewerRef.current(highlight);
            console.log('[PDFViewer] scroll helper invoked');
          } catch (err) {
            console.warn('[PDFViewer] Helper scroll failed', err);
          }
        }

        const highlightEl = getHighlightElement(highlight.id, targetPageNumber);
        if (highlightEl) {
          session.sawHighlightElement = true;
          if (!session.centerKickDone) {
            session.centerKickDone = true;
            try {
              centerElementInView(highlightEl);
            } catch (err) {
              console.warn('[PDFViewer] Failed to center highlight element', err);
            }
          }

          if (isElementVisibleInViewport(highlightEl)) {
            console.log('[PDFViewer] scrollToHighlight success via highlight element');
            return true;
          }

          // The target highlight is mounted and we attempted to center it.
          // Treat this as success to avoid repeated page-jump churn while the
          // browser settles layout/paint in virtualized PDF pages.
          const highlightPageAttr = (highlightEl.closest('.page[data-page-number]') as HTMLElement | null)
            ?.getAttribute('data-page-number');
          const onTargetPage = highlightPageAttr
            ? Number(highlightPageAttr) === targetPageNumber
            : false;
          if (highlightEl.isConnected && onTargetPage) {
            console.log('[PDFViewer] scrollToHighlight settled with mounted highlight element');
            return true;
          }

          // Highlight exists but has not settled into viewport yet.
          // Do not immediately snap back to page start; allow retry to re-check.
          return false;
        }

        // Wait for highlight layer paint after we already kicked page/helper once.
        return false;
      }
    }

    // No highlight yet: fall back to page-level scroll if we can resolve a citation.
    // If we already saw the target highlight element, avoid regressing to page-only
    // fallback while virtualized pages are re-rendering.
    const activeSession = scrollSessionRef.current;
    if (
      activeSession?.sawHighlightElement &&
      (activeSession.targetId === highlightId ||
        (tempToBackendMap && tempToBackendMap.get(highlightId) === activeSession.targetId))
    ) {
      return false;
    }

    const pageOnlyCitation = combinedCitationsRef.current.find(
      (c) =>
        c.id === highlightId ||
        c.highlightId === highlightId ||
        (tempToBackendMap && tempToBackendMap.get(c.id) === highlightId)
    );
    if (pageOnlyCitation?.startPageNumber) {
      const pageNumber = pageOnlyCitation.startPageNumber;
      setCurrentPage((prev) => (prev === pageNumber ? prev : pageNumber));
      const pageSelector = `.PdfHighlighter .page[data-page-number='${pageNumber}']`;
      const pageEl = globalThis.document?.querySelector(pageSelector) as HTMLElement | null;
      if (pageEl) {
        scrollElementIntoPdfView(pageEl, 'start');
        console.log('[PDFViewer] Scrolled to page via citation fallback', { highlightId, pageNumber });
        return true;
      }
    }

    // No highlight found or scroll target not ready yet
    return false;
  }, [
    centerElementInView,
    getHighlightElement,
    isElementVisibleInViewport,
    scrollElementIntoPdfView
  ]);
  
  // Handler for adding highlights
  const addHighlight = useCallback((highlight: IHighlight) => {
    setUserHighlights(prev => [...prev, highlight]);
    
    // If onCitationCreate callback exists, create a citation object
    if (onCitationCreate && document) {
      const citation = convertHighlightToCitation(highlight, document.metadata.id);
      onCitationCreate(citation);
    }
  }, [document, onCitationCreate]);
  
  // Handler for highlight click
  const handleHighlightClick = useCallback((highlight: IHighlight) => {
    if (onCitationClick) {
      // Find the corresponding citation if it exists
      const citation = documentCitations.find(c => c.highlightId === highlight.id);
      if (citation) {
        onCitationClick(citation);
      } else {
        onCitationClick(highlight);
      }
    }
  }, [documentCitations, onCitationClick]);
  
  // Set isBrowser to true once component mounts - always declare hooks in the same order
  useEffect(() => {
    setIsBrowser(true);
  }, []);
  
  // Get document URL from props or fetch it when document changes
  useEffect(() => {
    if (!isBrowser) return;
    
    if (propsPdfUrl) {
      setPdfUrl(propsPdfUrl);
      setErrorState(null);
    } else if (document) {
      const fetchDocumentUrl = async () => {
        setLoadingState("Retrieving document URL...");
        try {
          const url = await documentsApi.getDocumentUrl(document.metadata.id);
          setPdfUrl(url);
          setErrorState(null);
          setLoadingState(null);
        } catch (error) {
          console.error("Error fetching document URL:", error);
          setErrorState("Failed to retrieve document URL. Please try again later.");
          setLoadingState(null);
        }
      };
      
      fetchDocumentUrl();
    } else {
      setPdfUrl(null);
    }
  }, [document, propsPdfUrl, isBrowser]);
  
  // Keep the latest onCitationsLoaded in a ref so the fetch effect below only
  // re-runs when the document actually changes (inline callbacks from parents
  // would otherwise retrigger the expensive citations fetch on every render).
  const onCitationsLoadedRef = useRef(onCitationsLoaded);
  useEffect(() => {
    onCitationsLoadedRef.current = onCitationsLoaded;
  }, [onCitationsLoaded]);

  // Fetch citations when document changes. Runs in the background — it must
  // never blank out an already-rendered PDF (citation enrichment can be slow).
  useEffect(() => {
    if (!isBrowser || !document) return;

    const fetchCitations = async () => {
      try {
        const incoming = await documentsApi.getDocumentCitations(document.metadata.id);

        // Merge with existing citations, keyed by a signature so we can
        // attach rects from the enhanced version while keeping the original
        // (placeholder) id that chat messages reference.
        const mergeCitations = (prev: Citation[], next: Citation[]): Citation[] => {
          const bySig = new Map<string, Citation>();
          const tempToBackend = new Map<string, string>(); // Map temp IDs to backend IDs

          const getSig = (c: Citation) => {
            // Normalize cited text for better matching
            const normalizedText = (c.citedText || '').trim().replace(/\s+/g, ' ');
            return `${c.documentId}-${c.startPageNumber || 0}-${normalizedText}`;
          };

          // First, add all previous citations (which may include temp citations)
          prev.forEach(c => bySig.set(getSig(c), c));

          // Then process new citations from backend
          next.forEach(c => {
            const sig = getSig(c);
            const existing = bySig.get(sig);

            if (existing) {
              const hasRects = existing.rects?.length > 0;
              const newHasRects = c.rects?.length > 0;

              // If existing is a temp citation and new has rects, merge them
              if (existing.id.startsWith('cite-') && !hasRects && newHasRects) {
                // Map temp ID to backend ID
                tempToBackend.set(existing.id, c.id);
                tempToBackend.set(existing.highlightId || existing.id, c.id);
                
                // Keep the backend citation but preserve temp ID mapping
                const merged = {
                  ...c,
                  tempId: existing.id,
                  tempHighlightId: existing.highlightId
                };
                bySig.set(sig, merged);
                console.log('[PDFViewer] Mapped temp citation to backend:', {
                  tempId: existing.id,
                  backendId: c.id,
                  hasRects: c.rects.length,
                  page: c.startPageNumber
                });
              }
            } else {
              bySig.set(sig, c);
            }
          });

          // Store mapping for later use without wiping existing mappings that
          // may still be needed for in-flight citation clicks.
          const existingMap = (window as any).citationTempToBackendMap as Map<string, string> | undefined;
          const mergedMap = new Map<string, string>(existingMap || []);
          tempToBackend.forEach((backendId, tempId) => {
            mergedMap.set(tempId, backendId);
          });
          (window as any).citationTempToBackendMap = mergedMap;

          return Array.from(bySig.values());
        };

        const merged = mergeCitations(documentCitations, incoming);

        setDocumentCitations(merged);

        // Convert citations to highlights and notify parent
        const highlightsFromCitations = merged.map(convertCitationToHighlight);
        if (onCitationsLoadedRef.current) {
          onCitationsLoadedRef.current(highlightsFromCitations);
        }
      } catch (error) {
        console.error("Error fetching document citations:", error);
        // Don't set error state here as we still want to show the document even if citations fail
      }
    };

    fetchCitations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [document?.metadata?.id, isBrowser]);
  
  // After setting allHighlights in useEffect([citations, extraCitations]):
  useEffect(() => {
    console.log('[PDFViewer] Merged highlights:', allHighlights.map(h => ({ id: h.id, text: h.content.text, page: h.position.pageNumber, hasRects: h.position.rects.length > 0 })));
  }, [allHighlights]);

  // Keep one pending target and retry briefly until both highlight + viewer are ready.
  // This mirrors the core react-pdf-highlighter jump-to-highlight pattern
  // (scrollRef + deferred retries) to avoid race conditions between render and scroll.
  useEffect(() => {
    if (!highlightId) {
      pendingScrollHighlightIdRef.current = null;
      lastScrolledHighlightIdRef.current = null;
      lastScrollRefKickTargetRef.current = null;
      scrollSessionRef.current = null;
      return;
    }

    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    const visibilityCheckTimeouts: ReturnType<typeof setTimeout>[] = [];

    const scheduleVisibilityChecks = (target: string) => {
      [500, 1500, 3500, 6500].forEach((delay) => {
        const checkTimeoutId = setTimeout(() => {
          const targetEl = getHighlightElement(target);
          if (targetEl && isElementVisibleInViewport(targetEl)) {
            return;
          }

          lastScrolledHighlightIdRef.current = null;
          lastScrollRefKickTargetRef.current = null;
          scrollSessionRef.current = null;
          pendingScrollHighlightIdRef.current = target;
          scrollToHighlight(target);
        }, delay);

        visibilityCheckTimeouts.push(checkTimeoutId);
      });
    };

    // Prevent retry loops from repeatedly re-scrolling the same target on highlight/state churn,
    // but allow a fresh scroll after PDF/citation hydration re-renders the target offscreen.
    if (lastScrolledHighlightIdRef.current === highlightId) {
      const currentTarget = getHighlightElement(highlightId);
      if (currentTarget && isElementVisibleInViewport(currentTarget)) {
        scheduleVisibilityChecks(highlightId);
        return () => {
          visibilityCheckTimeouts.forEach(clearTimeout);
        };
      }
      lastScrolledHighlightIdRef.current = null;
      lastScrollRefKickTargetRef.current = null;
      scrollSessionRef.current = null;
    }

    if (pendingScrollHighlightIdRef.current !== highlightId) {
      lastScrollRefKickTargetRef.current = null;
      scrollSessionRef.current = null;
    }

    pendingScrollHighlightIdRef.current = highlightId;
    let attempts = 0;

    const tryScroll = () => {
      const target = pendingScrollHighlightIdRef.current;
      if (!target) {
        return;
      }

      const success = scrollToHighlight(target);
      if (success) {
        pendingScrollHighlightIdRef.current = null;
        lastScrolledHighlightIdRef.current = target;
        lastScrollRefKickTargetRef.current = null;
        scrollSessionRef.current = null;
        scheduleVisibilityChecks(target);
        flashHighlight(target);
        return;
      }

      attempts += 1;
      if (attempts < 45) {
        timeoutId = setTimeout(tryScroll, 120);
      }
    };

    tryScroll();

    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      visibilityCheckTimeouts.forEach(clearTimeout);
    };
  }, [highlightId, scrollToHighlight, highlightScrollVersion, getHighlightElement, isElementVisibleInViewport, flashHighlight]);
  
  // Reset each newly loaded PDF to fit one full page inside the viewer.
  useEffect(() => {
    if (!isBrowser) return;
    setRenderScale('page-fit');
  }, [document?.metadata.id, propsPdfUrl, isBrowser]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      console.log('PDFViewer unmounting, cleaning up resources');
      
      // Wait for any pending page loads before destroying
      if (currentPdfDocument && currentPdfDocument.loadingTask) {
        currentPdfDocument.loadingTask.promise.then(() => {
          cleanupRef.current();
        }).catch(() => {
          cleanupRef.current();
        });
      } else {
        cleanupRef.current();
      }
      
      // Clean up blob URLs
      cleanupBlobUrls();
      
      // Clear memory
      setUserHighlights([]);
      setDocumentCitations([]);
      setPdfUrl(null);
    };
  }, []);
  
  // Handle when PDF document is set
  useEffect(() => {
    if (currentPdfDocument) {
      handleDocumentLoadSuccess(currentPdfDocument);
    }
  }, [currentPdfDocument, handleDocumentLoadSuccess]);

  // Skip rendering until we're in the browser
  if (!isBrowser) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 text-primary animate-spin mx-auto" />
          <p className="mt-2 text-sm text-muted-foreground font-avenir-pro">Loading PDF viewer...</p>
        </div>
      </div>
    );
  }

  if (isLoading || loadingState) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 text-primary animate-spin mx-auto" />
          <p className="mt-2 text-sm text-muted-foreground font-avenir-pro">{loadingState || "Loading document..."}</p>
        </div>
      </div>
    );
  }

  // Use the error prop if provided, otherwise use the internal error state
  if (errorState) {
    // Show a user-friendly error if the PDF cannot be loaded
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
          <h3 className="mt-2 text-lg font-semibold text-foreground">Unable to load PDF</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            The original PDF file could not be retrieved. Interactive highlighting and citation features are unavailable.
          </p>
          <p className="mt-2 text-sm text-muted-foreground/80">
            If you need to view the document text, please contact support or try re-uploading the original PDF.
          </p>
        </div>
      </div>
    );
  }

  if (!document || !pdfUrl) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <File className="mx-auto h-12 w-12 text-muted-foreground/70" />
          <h3 className="mt-2 text-sm font-medium text-foreground">No document loaded</h3>
          <p className="mt-1 text-sm text-muted-foreground">Upload a document to view it here</p>
        </div>
      </div>
    );
  }

  // Render highlight element with popup
  const renderHighlight = (
    highlight: IHighlight,
    index: number,
    setTip: (highlight: IHighlight, callback: () => JSX.Element) => void,
    hideTip: () => void,
    viewportToScaled: (rect: LTWHP) => any,
    screenshot: (position: any) => string,
    isScrolledTo: boolean
  ) => {
    const isTextHighlight = !Boolean(highlight.content && highlight.content.image);
    
    // Determine highlight type and color
    const isAIHighlight = highlight.isAICitation || aiHighlights.some(h => h.id === highlight.id);
    const highlightColor = isAIHighlight ? 'bg-accent/30' : 'bg-primary/30';
    
    const triggerHighlightClick = () => handleHighlightClick(highlight);
    
    const popupContent = (
      <div 
        className={`${isAIHighlight ? 'bg-accent text-accent-foreground' : 'bg-primary text-primary-foreground'} text-sm p-2 rounded shadow cursor-pointer`}
        onClick={triggerHighlightClick}
      >
        {isAIHighlight 
          ? "AI Citation: " + (highlight.comment?.text || "Referenced in conversation") 
          : (highlight.comment?.text || "User Highlight")}
      </div>
    );
    
    return (
      <Popup
        popupContent={popupContent}
        onMouseOver={popupContent => setTip(highlight, () => popupContent)}
        onMouseOut={hideTip}
        key={index}
      >
        <div
          onClick={triggerHighlightClick}
          data-highlight-id={highlight.id}
          className="cursor-pointer"
        >
          {isTextHighlight ? (
            // Using any type to avoid type errors with the Highlight component
            <Highlight 
              isScrolledTo={isScrolledTo} 
              position={highlight.position as any}
              comment={highlight.comment}
            />
          ) : (
            // Using any type to avoid type errors with the AreaHighlight component
            <AreaHighlight
              isScrolledTo={isScrolledTo}
              highlight={highlight as any}
              onChange={() => {}}  // Required prop, unused for static highlights
            />
          )}
        </div>
      </Popup>
    );
  };

  return (
    <div className="relative flex h-full min-h-0 w-full flex-col bg-background">
      {document && (
        <div className="workspace-panel-bar flex-shrink-0 border-b border-border px-4 py-3">
          <h2 className="truncate text-base font-avenir-pro-demi text-foreground">{document.metadata.filename}</h2>
          <div className="mt-1 flex flex-col sm:flex-row sm:flex-wrap sm:space-x-6">
            <div className="mt-1 flex items-center text-xs text-muted-foreground">
              <File className="mr-1.5 h-4 w-4 flex-shrink-0 text-muted-foreground/80" />
              {document.metadata.mimeType}
            </div>
            {document.confidenceScore !== undefined && (
              <div className="mt-1 flex items-center text-xs text-muted-foreground">
                <span className="mr-1.5">Confidence:</span>
                {Math.round(document.confidenceScore * 100)}%
              </div>
            )}
          </div>
        </div>
      )}
      
      {pdfUrl && (
        <div className="relative min-h-0 flex-1 overflow-hidden">
          <PdfLoader 
            url={pdfUrl} 
            beforeLoad={<div className="p-4">Loading PDF...</div>}
            onError={(error) => {
              console.error('Error loading PDF:', error);
              if (error.message.includes('worker') && workerUrl === '/pdf.worker.min.js') {
                console.warn('[PDFViewer] Local worker failed. Falling back to 2.16.105 CDN worker');
                setWorkerUrl('https://unpkg.com/pdfjs-dist@2.16.105/build/pdf.worker.min.js');
              } else {
                setErrorState(error.message);
              }
            }}
            // Update workerSrc and cMapUrl to stable version
            workerSrc={workerUrl}
            cMapUrl="https://unpkg.com/pdfjs-dist@2.16.105/cmaps/"
            cMapPacked={true}
          >
            {(pdfDocument) => {
              // Update document in state after render without using hooks
              // This is a safe approach that doesn't violate hook rules
              // We use a regular function and setTimeout to defer the state update
              if (pdfDocument) {
                // Use setTimeout to move state update out of render phase
                setTimeout(() => {
                  setCurrentPdfDocument(pdfDocument);
                }, 0);
              }
              
              return (
                <PdfHighlighter
                  pdfDocument={pdfDocument}
                  enableAreaSelection={(event) => event.altKey}
                  onScrollChange={onVisiblePagesChanged as any}
                  scrollRef={(scrollTo: any) => {
                    scrollViewerRef.current = scrollTo;
                    const target = pendingScrollHighlightIdRef.current;
                    if (target && lastScrollRefKickTargetRef.current !== target) {
                      lastScrollRefKickTargetRef.current = target;
                      const success = scrollToHighlight(target);
                      if (success) {
                        pendingScrollHighlightIdRef.current = null;
                        lastScrolledHighlightIdRef.current = target;
                        lastScrollRefKickTargetRef.current = null;
                        scrollSessionRef.current = null;
                      }
                    }
                  }}
                  onSelectionFinished={(
                    position,
                    content,
                    hideTipAndSelection,
                    transformSelection
                  ) => {
                    return (
                      <div className="workspace-summary-block border border-border bg-card p-2">
                        <div className="flex justify-between mb-2">
                          <div className="text-foreground">Add Highlight</div>
                          <button 
                            className="workspace-primary-btn px-3 py-1 text-sm font-avenir-pro" 
                            onClick={() => {
                              const highlightId = `highlight-${Date.now()}`;
                              addHighlight({
                                id: highlightId,
                                content,
                                position,
                                comment: {
                                  text: "User highlight",
                                  emoji: "✍️",
                                },
                              });
                              hideTipAndSelection();
                            }}
                          >
                            Save
                          </button>
                        </div>
                      </div>
                    );
                  }}
                  highlights={allHighlights}
                  highlightTransform={renderHighlight as any}
                  pdfScaleValue={renderScale}
                />
              );
            }}
          </PdfLoader>
        </div>
      )}
      
      {/* Performance controls for large PDFs */}
      {totalPages > 50 && (
        <div className="workspace-summary-block absolute bottom-4 right-4 z-10 border border-border p-2 text-xs">
          <div className="mb-1 font-medium text-foreground">Performance Options</div>
          <div className="flex space-x-2">
            <button 
              className={`rounded-full px-3 py-1 ${renderScale === 'page-fit' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}
              onClick={() => setRenderScale('page-fit')}
            >
              Fit
            </button>
            <button 
              className={`rounded-full px-3 py-1 ${renderScale === '1' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}
              onClick={() => setRenderScale('1')}
            >
              Low
            </button>
            <button 
              className={`rounded-full px-3 py-1 ${renderScale === '1.5' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}
              onClick={() => setRenderScale('1.5')}
            >
              Medium
            </button>
            <button 
              className={`rounded-full px-3 py-1 ${renderScale === '2' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}
              onClick={() => setRenderScale('2')}
            >
              High
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
