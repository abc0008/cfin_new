'use client';

import { useEffect, useRef, useCallback } from 'react';
import { Citation } from '@/types/citation';
import { useCitation } from '@/context/CitationContext';
import { documentsApi } from '@/lib/api/documents';

interface UseCitationPrefetchOptions {
  documentId?: string;
  currentPage: number;
  totalPages: number;
  prefetchRadius?: number; // Number of pages to prefetch around current page
  enabled?: boolean;
}

export function useCitationPrefetch({
  documentId,
  currentPage,
  totalPages,
  prefetchRadius = 3,
  enabled = true
}: UseCitationPrefetchOptions) {
  const { addCitations } = useCitation();
  const prefetchedPages = useRef<Set<number>>(new Set());
  const prefetchQueue = useRef<number[]>([]);
  const isPrefetching = useRef(false);

  const prefetchPageCitations = useCallback(async (pageNumber: number) => {
    if (!documentId || !enabled) return;
    
    try {
      // In a real implementation, this would fetch citations for a specific page
      // For now, we'll use the document citations endpoint
      const citations = await documentsApi.getDocumentCitations(documentId);
      
      // Filter citations for the specific page
      const pageCitations = citations.filter(c => 
        c.startPageNumber === pageNumber || 
        (c.startPageNumber && c.endPageNumber && 
         pageNumber >= c.startPageNumber && 
         pageNumber <= c.endPageNumber)
      );
      
      if (pageCitations.length > 0) {
        addCitations(pageCitations);
      }
      
      prefetchedPages.current.add(pageNumber);
    } catch (error) {
      console.error(`Error prefetching citations for page ${pageNumber}:`, error);
    }
  }, [documentId, enabled, addCitations]);

  const processPrefetchQueue = useCallback(async () => {
    if (isPrefetching.current || prefetchQueue.current.length === 0) {
      return;
    }

    isPrefetching.current = true;

    while (prefetchQueue.current.length > 0) {
      const page = prefetchQueue.current.shift();
      if (page && !prefetchedPages.current.has(page)) {
        await prefetchPageCitations(page);
        // Add a small delay to avoid overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }

    isPrefetching.current = false;
  }, [prefetchPageCitations]);

  useEffect(() => {
    if (!enabled || !documentId || currentPage < 1 || currentPage > totalPages) {
      return;
    }

    // Calculate pages to prefetch
    const pagesToPrefetch: number[] = [];
    
    // Add current page first (highest priority)
    if (!prefetchedPages.current.has(currentPage)) {
      pagesToPrefetch.push(currentPage);
    }

    // Add nearby pages
    for (let i = 1; i <= prefetchRadius; i++) {
      // Pages after current
      const nextPage = currentPage + i;
      if (nextPage <= totalPages && !prefetchedPages.current.has(nextPage)) {
        pagesToPrefetch.push(nextPage);
      }

      // Pages before current
      const prevPage = currentPage - i;
      if (prevPage >= 1 && !prefetchedPages.current.has(prevPage)) {
        pagesToPrefetch.push(prevPage);
      }
    }

    // Add to queue and process
    prefetchQueue.current = Array.from(new Set([...prefetchQueue.current, ...pagesToPrefetch]));
    processPrefetchQueue();

  }, [currentPage, totalPages, documentId, enabled, prefetchRadius, processPrefetchQueue]);

  // Clear cache when document changes
  useEffect(() => {
    prefetchedPages.current.clear();
    prefetchQueue.current = [];
  }, [documentId]);

  return {
    prefetchedPages: prefetchedPages.current.size,
    isPrefetching: isPrefetching.current
  };
}