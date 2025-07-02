'use client';

import React, { useEffect, useState } from 'react';
import { PDFViewer } from './PDFViewer';
import { useCitation } from '@/context/CitationContext';
import { Citation } from '@/types/citation';
import { useCitationPrefetch } from '@/hooks/useCitationPrefetch';
import { usePerformanceMonitor } from '@/hooks/usePerformanceMonitor';
import { CitationSearchProgress } from '@/components/ui/citation-progress';

interface CitationNavigationEvent extends CustomEvent {
  detail: {
    citation: Citation;
    documentUrl: string;
  };
}

export function CitationEnabledPDFViewer(props: React.ComponentProps<typeof PDFViewer>) {
  const { openCitation } = useCitation();
  const { measureCitationLoad, measureSearch, startTimer, endTimer } = usePerformanceMonitor();
  const [navigatingToCitation, setNavigatingToCitation] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [searchProgress, setSearchProgress] = useState(0);
  const [foundCitations, setFoundCitations] = useState(0);
  
  // Prefetch citations for nearby pages
  const { prefetchedPages } = useCitationPrefetch({
    documentId: props.document?.metadata.id,
    currentPage,
    totalPages,
    enabled: true
  });

  useEffect(() => {
    const handleCitationNavigation = async (event: Event) => {
      const citationEvent = event as CitationNavigationEvent;
      const { citation } = citationEvent.detail;
      
      // If this viewer is showing the citation's document, scroll to it
      if (props.document?.metadata.id === citation.documentId) {
        startTimer(`nav_${citation.id}`);
        setNavigatingToCitation(citation.highlightId);
        
        // Record navigation performance
        setTimeout(() => {
          const duration = endTimer(`nav_${citation.id}`);
          if (duration > 0) {
            console.log(`Citation navigation took ${duration.toFixed(2)}ms`);
          }
        }, 500);
      }
    };

    window.addEventListener('citation-navigation', handleCitationNavigation);
    
    return () => {
      window.removeEventListener('citation-navigation', handleCitationNavigation);
    };
  }, [props.document?.metadata.id, startTimer, endTimer]);

  // Handle citation clicks using CitationContext with performance monitoring
  const handleCitationClick = async (citationOrHighlight: Citation | any) => {
    if ('highlightId' in citationOrHighlight && 'documentId' in citationOrHighlight) {
      // It's a Citation object - measure load time
      await measureCitationLoad(citationOrHighlight.id, async () => {
        await openCitation(citationOrHighlight.id);
      });
    } else if (props.onCitationClick) {
      // Fall back to original handler for IHighlight objects
      props.onCitationClick(citationOrHighlight);
    }
  };

  // Enhanced props with performance callbacks
  const enhancedProps = {
    ...props,
    highlightId: navigatingToCitation || props.highlightId,
    onCitationClick: handleCitationClick,
    onCitationsLoaded: (citations: any[]) => {
      setFoundCitations(citations.length);
      if (props.onCitationsLoaded) {
        props.onCitationsLoaded(citations);
      }
    }
  };

  return (
    <>
      <PDFViewer {...enhancedProps} />
      <CitationSearchProgress
        isSearching={isSearching}
        searchProgress={searchProgress}
        totalDocuments={totalPages}
        currentDocument={currentPage}
        foundCitations={foundCitations}
      />
    </>
  );
}