"use client";

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { Citation, CitationPayload } from '@/types/citation';
import { ProcessedDocument } from '@/types';
import { getCitationCache } from '@/lib/cache/citationCache';

interface CitationContextType {
  citations: Map<string, Citation>;
  documents: Map<string, ProcessedDocument>;
  activeDocumentId: string | null;
  loadCitation: (citationId: string) => Promise<Citation>;
  openCitation: (citationId: string) => Promise<void>;
  setActiveDocument: (documentId: string | null) => void;
  getDocumentUrl: (documentId: string) => string;
  loadDocument: (documentId: string) => Promise<ProcessedDocument>;
  addCitations: (citations: Citation[]) => void;
}

const CitationContext = createContext<CitationContextType | undefined>(undefined);

export const useCitation = () => {
  const context = useContext(CitationContext);
  if (!context) {
    throw new Error('useCitation must be used within a CitationProvider');
  }
  return context;
};

interface CitationProviderProps {
  children: ReactNode;
}

export const CitationProvider: React.FC<CitationProviderProps> = ({ children }) => {
  const [citations, setCitations] = useState<Map<string, Citation>>(new Map());
  const [documents, setDocuments] = useState<Map<string, ProcessedDocument>>(new Map());
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);
  const cache = getCitationCache();

  const loadCitation = useCallback(async (citationId: string): Promise<Citation> => {
    // Debug: trace every attempt to load a citation
    console.log('[CitationContext] loadCitation start', { citationId });
    // Check memory cache first
    const cached = citations.get(citationId);
    if (cached) {
      console.log('[CitationContext] loadCitation hit ‑ memory cache', { citationId, hasRects: cached.rects?.length || 0 });
      return cached;
    }

    // Check persistent cache
    const cachedCitation = cache.getCitation(citationId);
    if (cachedCitation) {
      console.log('[CitationContext] loadCitation hit ‑ persistent cache', { citationId, hasRects: cachedCitation.rects?.length || 0 });
      setCitations(prev => new Map(prev).set(citationId, cachedCitation));
      return cachedCitation;
    }

    console.log('[CitationContext] loadCitation fetching from API', { citationId });
    try {
      // Use backend API URL
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/api/citations/${citationId}`);
      if (!response.ok) {
        throw new Error(`Failed to load citation: ${response.statusText}`);
      }
      
      const citation: Citation = await response.json();
      console.log('[CitationContext] loadCitation fetched', { citationId, hasRects: citation.rects?.length || 0 });
      
      // Cache the citation in both memory and persistent cache
      setCitations(prev => new Map(prev).set(citationId, citation));
      cache.setCitation(citation);
      
      return citation;
    } catch (error) {
      console.error('Error loading citation:', error);
      throw error;
    }
  }, [citations]);

  const loadDocument = useCallback(async (documentId: string): Promise<ProcessedDocument> => {
    console.log('[CitationContext] loadDocument start', { documentId });
    // Check if document is already cached
    const cached = documents.get(documentId);
    if (cached) {
      console.log('[CitationContext] loadDocument hit ‑ memory cache', { documentId });
      return cached;
    }

    console.log('[CitationContext] loadDocument fetching from API', { documentId });
    try {
      // Use backend API URL
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}`);
      if (!response.ok) {
        throw new Error(`Failed to load document: ${response.statusText}`);
      }
      
      const document: ProcessedDocument = await response.json();
      console.log('[CitationContext] loadDocument fetched', { documentId });
      
      // Cache the document
      setDocuments(prev => new Map(prev).set(documentId, document));
      
      return document;
    } catch (error) {
      console.error('Error loading document:', error);
      throw error;
    }
  }, [documents]);

  const getDocumentUrl = useCallback((documentId: string): string => {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return `${API_BASE_URL}/api/documents/${documentId}/file`;
  }, []);

  const openCitation = useCallback(async (citationId: string): Promise<void> => {
    console.log('[CitationContext] openCitation start', { 
      citationId,
      isTempId: citationId.startsWith('cite-'),
      cachedCitations: Array.from(citations.keys())
    });
    try {
      // Load citation if not cached
      let citation = citations.get(citationId);
      
      // If not found by ID and it's a temp ID, search by various methods
      if (!citation && citationId.startsWith('cite-')) {
        console.log('[CitationContext] Temp ID not found, searching by various methods...');
        
        // Method 1: Search by highlightId
        for (const [id, cit] of Array.from(citations)) {
          if (cit.highlightId === citationId || cit.id === citationId) {
            citation = cit;
            console.log('[CitationContext] Found citation by highlightId match:', {
              searchId: citationId,
              foundId: cit.id,
              highlightId: cit.highlightId,
              hasRects: cit.rects?.length > 0
            });
            break;
          }
        }
        
        // Method 2: If still not found, search by signature for similar citations
        if (!citation) {
          // Extract key info from the temp ID to find matching backend citation
          for (const [id, cit] of Array.from(citations)) {
            // Check if this is a backend citation (UUID format) with rects
            if (!id.startsWith('cite-') && cit.rects && cit.rects.length > 0) {
              // Compare by document and page to find potential matches
              const tempCit = citations.get(citationId);
              if (tempCit && 
                  cit.documentId === tempCit.documentId && 
                  cit.startPageNumber === tempCit.startPageNumber &&
                  textSimilarity(cit.citedText, tempCit.citedText) > 0.8) {
                citation = cit;
                console.log('[CitationContext] Found backend citation by similarity:', {
                  searchId: citationId,
                  foundId: cit.id,
                  hasRects: cit.rects.length,
                  page: cit.startPageNumber
                });
                break;
              }
            }
          }
        }
      }
      
      if (!citation) {
        console.log('[CitationContext] openCitation – citation not in cache, loading…', {
          citationId,
          availableIds: Array.from(citations.keys())
        });
        // Only try to load from API if it's not a temp ID
        if (!citationId.startsWith('cite-')) {
          citation = await loadCitation(citationId);
        } else {
          throw new Error(`Temp citation ${citationId} not found in cache and cannot be loaded from API`);
        }
      }

      // Load document if not cached
      if (!documents.has(citation.documentId)) {
        console.log('[CitationContext] openCitation – document not in cache, loading…', { documentId: citation.documentId });
        await loadDocument(citation.documentId);
      }

      // Set active document
      setActiveDocumentId(citation.documentId);

      console.log('[CitationContext] openCitation loaded', { citationId, documentId: citation.documentId, page: citation.startPageNumber, rectCount: citation.rects?.length || 0 });

      // Navigate based on citation type
      if (citation.type === 'page_location' && citation.startPageNumber) {
        // TODO: Integrate with PDF viewer to navigate to page
        console.log(`Navigate to page ${citation.startPageNumber} in document ${citation.documentId}`);
        
        // If rects are available, highlight the specific areas
        if (citation.rects.length > 0) {
          console.log('Highlight rects:', citation.rects);
          // TODO: Apply highlights to PDF viewer
        }
      } else if (citation.type === 'char_location') {
        // TODO: Navigate to character position
        console.log(`Navigate to character position ${citation.startCharIndex}-${citation.endCharIndex}`);
      } else if (citation.type === 'content_block_location') {
        // TODO: Navigate to content block
        console.log(`Navigate to content block ${citation.startBlockIndex}-${citation.endBlockIndex}`);
      }

      // Emit event for PDF viewer to handle navigation
      console.log('[CitationContext] Dispatching citation-navigation event:', {
        originalId: citationId,
        citationId: citation.id,
        highlightId: citation.highlightId,
        hasRects: citation.rects?.length > 0,
        page: citation.startPageNumber,
        documentUrl: getDocumentUrl(citation.documentId)
      });
      window.dispatchEvent(new CustomEvent('citation-navigation', {
        detail: { citation, documentUrl: getDocumentUrl(citation.documentId) }
      }));

    } catch (error) {
      console.error('Error opening citation:', error);
      throw error;
    }
  }, [citations, documents, loadCitation, loadDocument, getDocumentUrl]);

  const setActiveDocument = useCallback((documentId: string | null) => {
    setActiveDocumentId(documentId);
  }, []);

  // Replace getSignature with a more robust version that matches citationService
  const getSignature = (c: Citation) => {
    // This should match the signature generation in citationService.ts
    const normalizedText = (c.citedText || '')
      .trim()
      .replace(/\r\n/g, '\n')  // Normalize line endings first
      .replace(/\s+/g, ' ')    // Normalize whitespace
      .toLowerCase()           // Case insensitive
      .substring(0, 100);      // Limit length for comparison
    return `${c.documentId}-${c.startPageNumber || 0}-${normalizedText}`;
  };

  const addCitations = useCallback((newCitations: Citation[]) => {
    console.log('[CitationContext] addCitations called', { count: newCitations.length });
    setCitations(prev => {
      const updated = new Map(prev);

      // Build reverse index by signature for fast lookup
      const bySignature = new Map<string, string>(); // signature -> citationId
      updated.forEach((cit, id) => bySignature.set(getSignature(cit), id));

      // Replace the merging logic in addCitations with guarded version
      newCitations.forEach(citation => {
        const sig = getSignature(citation);
        let existingId = bySignature.get(sig);
        if (!existingId) {
          // Fallback: fuzzy match on citedText (e.g., >80% similarity)
          for (const [existingSig, id] of Array.from(bySignature)) {
            const existingCit = updated.get(id);
            if (existingCit && textSimilarity(existingCit.citedText, citation.citedText) > 0.8) {
              existingId = id;
              break;
            }
          }
        }
        if (existingId) {
          const existing = updated.get(existingId);
          if (existing) {
            const existingHasRects = existing.rects && existing.rects.length > 0;
            const newHasRects = citation.rects && citation.rects.length > 0;
            if (!existingHasRects && newHasRects) {
              console.log('[CitationContext] Merging citation with rects:', {
                existingId: existing.id,
                existingHighlightId: existing.highlightId,
                newId: citation.id,
                newHighlightId: citation.highlightId,
                rectCount: citation.rects.length,
                preservedId: existing.id
              });
              const merged: Citation = {
                ...existing,
                ...citation,
                id: existing.id,
                highlightId: existing.highlightId || citation.highlightId,
                rects: citation.rects,
              };
              updated.set(existingId, merged);
            } // else keep existing
          } else {
            // Rare: existingId but no entry, add new
            updated.set(citation.id, citation);
          }
        } else {
          // No match, add as new
          console.log('[CitationContext] Adding new citation:', {
            id: citation.id,
            highlightId: citation.highlightId,
            isTempId: citation.id.startsWith('cite-'),
            hasRects: citation.rects?.length > 0
          });
          updated.set(citation.id, citation);
        }
      });

      console.log('[CitationContext] addCitations merged', { total: updated.size });
      return updated;
    });

    // Also add to persistent cache
    cache.addCitations(newCitations);
  }, [cache]);

  const value: CitationContextType = {
    citations,
    documents,
    activeDocumentId,
    loadCitation,
    openCitation,
    setActiveDocument,
    getDocumentUrl,
    loadDocument,
    addCitations,
  };

  // Expose context in development for easier debugging via DevTools console
  if (process.env.NODE_ENV !== 'production' && typeof window !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).citationCtx = value;
  }

  return (
    <CitationContext.Provider value={value}>
      {children}
    </CitationContext.Provider>
  );
};

export default CitationContext;

const textSimilarity = (a: string, b: string): number => {
  // Normalize both texts
  const normalize = (text: string) => text
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')  // Normalize whitespace
    .replace(/[.,;:!?'"]/g, '')  // Remove punctuation
    .substring(0, 100);  // Compare first 100 chars
  
  const normA = normalize(a);
  const normB = normalize(b);
  
  // Check exact match first
  if (normA === normB) return 1;
  
  // Check if one contains the other
  if (normA.includes(normB) || normB.includes(normA)) return 0.9;
  
  // Check if they share significant substring (at least 20 chars)
  const minLength = Math.min(normA.length, normB.length);
  if (minLength >= 20) {
    for (let i = 0; i <= normA.length - 20; i++) {
      const substr = normA.substring(i, i + 20);
      if (normB.includes(substr)) return 0.8;
    }
  }
  
  return 0;
};