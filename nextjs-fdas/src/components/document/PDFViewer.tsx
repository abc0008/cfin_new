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
  renderingQuality = 'medium',
  pageBufferSize = 5,
  extraCitations = []
}: PDFViewerProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [userHighlights, setUserHighlights] = useState<IHighlight[]>([]);
  const [pdfUrl, setPdfUrl] = useState<string | null>(propsPdfUrl || null);
  const [errorState, setErrorState] = useState<string | null>(error || null);
  const [loadingState, setLoadingState] = useState<string | null>(null);
  const [documentCitations, setDocumentCitations] = useState<Citation[]>([]);
  const [totalPages, setTotalPages] = useState<number>(0);
  const [visiblePages, setVisiblePages] = useState<number[]>([]);
  const [loadedPages, setLoadedPages] = useState<Set<number>>(new Set());
  const [renderScale, setRenderScale] = useState<number>(
    renderingQuality === 'low' ? 1.0 : 
    renderingQuality === 'medium' ? 1.5 : 2.0
  );
  const [isBrowser, setIsBrowser] = useState(false);
  
  const [currentPdfDocument, setCurrentPdfDocument] = useState<any>(null);
  const scrollViewerRef = useRef<((highlight: IHighlight) => void) | null>(null);
  const cleanupRef = useRef<() => void>(() => {});
  
  const [scrollState, setScrollState] = useState<'IDLE' | 'WAIT_HIGHLIGHT' | 'WAIT_READY' | 'SCROLL'>('IDLE');

  // Use pdf.js 2.16.x which matches react-pdf-highlighter's internal version.
  // Provide local worker first, with CDN fallback **of the same version**.
  const [workerUrl, setWorkerUrl] = useState('/pdf.worker.min.js');

  // Merge backend citations with any extra ones from props
  const combinedCitations = React.useMemo(() => {
    const byId = new Map<string, Citation>();
    [...extraCitations, ...documentCitations].forEach(c => {
      if (!byId.has(c.id)) {
        byId.set(c.id, c);
      }
    });
    return Array.from(byId.values());
  }, [extraCitations, documentCitations]);

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
  
  // Memory management: Page visibility tracking
  const onVisiblePagesChanged = useCallback((pages: number[]) => {
    setVisiblePages(pages);
    
    // Only keep a buffer of pages in memory
    const pagesToKeep = new Set<number>();
    
    // Add currently visible pages
    pages.forEach(page => pagesToKeep.add(page));
    
    // Add buffer pages (before and after visible pages)
    const halfBuffer = Math.floor(pageBufferSize / 2);
    pages.forEach(page => {
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
  const scrollToHighlight = useCallback((highlightId: string) => {
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
    let highlight = allHighlights.find(h => {
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
        for (const h of allHighlights) {
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
        availableHighlights: allHighlights.map(h => ({
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
      console.log('[PDFViewer] Executing scroll to page', highlight.position.pageNumber);
      // Set current page (state) so page number indicator etc updates
      setCurrentPage(highlight.position.pageNumber);

      // Prefer library helper if available
      if (scrollViewerRef.current) {
        scrollViewerRef.current(highlight);
        console.log('[PDFViewer] scrollToHighlight success via helper');
        return true;
      }

      // Fallback: manually scroll the .page element into view
      try {
        const pageSelector = `.PdfHighlighter .page[data-page-number='${highlight.position.pageNumber}']`;
        const pageEl = globalThis.document?.querySelector(pageSelector);
        if (pageEl) {
          (pageEl as HTMLElement).scrollIntoView({ behavior: 'smooth', block: 'center' });
          console.log('[PDFViewer] scrollToHighlight success via DOM scroll');
          return true;
        }
      } catch (err) {
        console.warn('[PDFViewer] Fallback DOM scroll failed', err);
      }
    }
    // No highlight found or scroll target not ready yet
    return false;
  }, [allHighlights, userHighlights]);
  
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
  
  // Fetch citations when document changes
  useEffect(() => {
    if (!isBrowser || !document) return;
    
    const fetchCitations = async () => {
      try {
        setLoadingState("Loading document citations...");
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

          // Store the mapping for later use
          (window as any).citationTempToBackendMap = tempToBackend;

          return Array.from(bySig.values());
        };

        const merged = mergeCitations(documentCitations, incoming);

        setDocumentCitations(merged);

        // Convert citations to highlights and notify parent
        const highlightsFromCitations = merged.map(convertCitationToHighlight);
        if (onCitationsLoaded) {
          onCitationsLoaded(highlightsFromCitations);
        }
        
        setLoadingState(null);
      } catch (error) {
        console.error("Error fetching document citations:", error);
        // Don't set error state here as we still want to show the document even if citations fail
        setLoadingState(null);
      }
    };
    
    fetchCitations();
  }, [document, onCitationsLoaded, isBrowser, highlightId]);
  
  // After setting allHighlights in useEffect([citations, extraCitations]):
  useEffect(() => {
    console.log('[PDFViewer] Merged highlights:', allHighlights.map(h => ({ id: h.id, text: h.content.text, page: h.position.pageNumber, hasRects: h.position.rects.length > 0 })));
  }, [allHighlights]);

  // Replace the scrolling useEffect with state machine
  useEffect(() => {
    if (highlightId && scrollState === 'IDLE') {
      console.log('[PDFViewer] highlightId prop changed to:', highlightId, 'triggering scroll');
      setScrollState('WAIT_HIGHLIGHT');
    }
  }, [highlightId]);

  // Fix type error by checking if rawClaudeCitation exists and has id
  useEffect(() => {
    if (scrollState === 'WAIT_HIGHLIGHT') {
      const highlight = allHighlights.find(h => 
        h.id === highlightId || 
        (h.rawClaudeCitation && 'id' in h.rawClaudeCitation && h.rawClaudeCitation.id === highlightId) ||
        (h.rawClaudeCitation && 'highlightId' in h.rawClaudeCitation && (h.rawClaudeCitation as any).highlightId === highlightId)
      );
      
      if (highlight) {
        console.log('[PDFViewer] Found highlight in WAIT_HIGHLIGHT state:', {
          searchId: highlightId,
          foundId: highlight.id,
          page: highlight.position.pageNumber,
          hasRects: highlight.position.rects.length > 0
        });
        setScrollState('WAIT_READY');
      } else if (highlightId) {
        // If highlight not found, check if we have a citation in extraCitations
        const tempCitation = extraCitations.find(c => 
          c.id === highlightId || 
          c.highlightId === highlightId
        );
        
        if (tempCitation && tempCitation.startPageNumber) {
          console.log('[PDFViewer] Citation not in highlights, but found in extraCitations. Navigating to page:', tempCitation.startPageNumber);
          // Navigate directly to the page
          setCurrentPage(tempCitation.startPageNumber);
          setScrollState('IDLE');
          
          // Manually scroll to the page
          setTimeout(() => {
            const pageSelector = `.PdfHighlighter .page[data-page-number='${tempCitation.startPageNumber}']`;
            const pageEl = globalThis.document?.querySelector(pageSelector);
            if (pageEl) {
              (pageEl as HTMLElement).scrollIntoView({ behavior: 'smooth', block: 'center' });
              console.log('[PDFViewer] Scrolled to page via extraCitations fallback');
            }
          }, 100);
        }
      }
    }
  }, [allHighlights, scrollState, highlightId, extraCitations]);

  useEffect(() => {
    if (scrollState === 'WAIT_READY' && scrollViewerRef.current) {
      setScrollState('SCROLL');
      const success = scrollToHighlight(highlightId);
      if (success) {
        setScrollState('IDLE');
      } else {
        // Retry logic if needed
        setTimeout(() => setScrollState('WAIT_HIGHLIGHT'), 500);
      }
    }
  }, [scrollState, scrollViewerRef, highlightId, allHighlights]);
  
  // Update render scale when renderingQuality changes
  useEffect(() => {
    if (!isBrowser) return;
    setRenderScale(
      renderingQuality === 'low' ? 1.0 : 
      renderingQuality === 'medium' ? 1.5 : 2.0
    );
  }, [renderingQuality, isBrowser]);
  
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

  useEffect(() => {
    const handleCitationNavigation = (e: CustomEvent<{ citation: Citation }>) => {
      // Ensure detail exists
      if (!e.detail || !e.detail.citation) return;
      const newCitation = e.detail.citation;
      console.log('[PDFViewer] Received citation-navigation event:', {
        citationId: newCitation.id,
        highlightId: newCitation.highlightId,
        hasRects: newCitation.rects?.length > 0,
        page: newCitation.startPageNumber
      });
      
      if (newCitation) {
        // Convert to highlight format
        const dummyViewport = { width: 612, height: 792 };
        const newHighlight = convertCitationToHighlight(newCitation, dummyViewport);
        
        // Check if already exists (by any of its IDs)
        const exists = allHighlights.some(h => 
          h.id === newHighlight.id ||
          h.id === newCitation.id ||
          h.id === newCitation.highlightId ||
          (h.rawClaudeCitation && (h.rawClaudeCitation as any).id === newCitation.id)
        );
        
        console.log('[PDFViewer] Citation exists in highlights:', exists);
        
        if (!exists) {
          console.warn('[PDFViewer] Citation not found in highlights, cannot add dynamically to prop-based array');
        }
        
        // Try to scroll using the original citation ID (which might be temp ID)
        // The scrollToHighlight function will handle ID matching
        scrollToHighlight(newCitation.id);
        
        // Also try with highlightId if different from id
        if (newCitation.highlightId && newCitation.highlightId !== newCitation.id) {
          console.log('[PDFViewer] Also trying to scroll with highlightId:', newCitation.highlightId);
          scrollToHighlight(newCitation.highlightId);
        }
      }
    };
    window.addEventListener('citation-navigation', handleCitationNavigation as EventListener);
    return () => window.removeEventListener('citation-navigation', handleCitationNavigation as EventListener);
  }, [allHighlights, scrollToHighlight]); // Dependencies needed to avoid stale closures
  
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
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto" />
          <h3 className="mt-2 text-lg font-semibold text-gray-900">Unable to load PDF</h3>
          <p className="mt-2 text-sm text-gray-500">
            The original PDF file could not be retrieved. Interactive highlighting and citation features are unavailable.
          </p>
          <p className="mt-2 text-sm text-gray-400">
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
          <File className="h-12 w-12 text-gray-400 mx-auto" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No document loaded</h3>
          <p className="mt-1 text-sm text-gray-500">Upload a document to view it here</p>
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
    <div className="h-full bg-gray-50 flex flex-col relative">
      {document && (
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">{document.metadata.filename}</h2>
          <div className="mt-1 flex flex-col sm:flex-row sm:flex-wrap sm:mt-0 sm:space-x-6">
            <div className="mt-2 flex items-center text-sm text-gray-500">
              <File className="flex-shrink-0 mr-1.5 h-5 w-5 text-gray-400" />
              {document.metadata.mimeType}
            </div>
            {document.confidenceScore !== undefined && (
              <div className="mt-2 flex items-center text-sm text-gray-500">
                <span className="mr-1.5">Confidence:</span>
                {Math.round(document.confidenceScore * 100)}%
              </div>
            )}
          </div>
        </div>
      )}
      
      {pdfUrl && (
        <div className="flex-1 overflow-auto">
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
                  }}
                  onSelectionFinished={(
                    position,
                    content,
                    hideTipAndSelection,
                    transformSelection
                  ) => {
                    return (
                      <div className="bg-white p-2 border border-gray-300 rounded shadow-md">
                        <div className="flex justify-between mb-2">
                          <div>Add Highlight</div>
                          <button 
                            className="text-primary hover:text-primary/80 px-3 py-1 rounded text-sm font-avenir-pro" 
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
                  pdfScaleValue={renderScale.toString()}
                />
              );
            }}
          </PdfLoader>
        </div>
      )}
      
      {/* Performance controls for large PDFs */}
      {totalPages > 50 && (
        <div className="absolute bottom-4 right-4 bg-white rounded-md shadow p-2 text-xs z-10 border border-gray-200">
          <div className="mb-1 font-medium">Performance Options</div>
          <div className="flex space-x-2">
            <button 
              className={`px-2 py-1 rounded ${renderingQuality === 'low' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}
              onClick={() => setRenderScale(1.0)}
            >
              Low
            </button>
            <button 
              className={`px-2 py-1 rounded ${renderingQuality === 'medium' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}
              onClick={() => setRenderScale(1.5)}
            >
              Medium
            </button>
            <button 
              className={`px-2 py-1 rounded ${renderingQuality === 'high' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}
              onClick={() => setRenderScale(2.0)}
            >
              High
            </button>
          </div>
        </div>
      )}
    </div>
  );
}