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
    // Check memory cache first
    const cached = citations.get(citationId);
    if (cached) {
      return cached;
    }

    // Check persistent cache
    const cachedCitation = cache.getCitation(citationId);
    if (cachedCitation) {
      setCitations(prev => new Map(prev).set(citationId, cachedCitation));
      return cachedCitation;
    }

    try {
      const response = await fetch(`/api/citations/${citationId}`);
      if (!response.ok) {
        throw new Error(`Failed to load citation: ${response.statusText}`);
      }
      
      const citation: Citation = await response.json();
      
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
    // Check if document is already cached
    const cached = documents.get(documentId);
    if (cached) {
      return cached;
    }

    try {
      const response = await fetch(`/api/documents/${documentId}`);
      if (!response.ok) {
        throw new Error(`Failed to load document: ${response.statusText}`);
      }
      
      const document: ProcessedDocument = await response.json();
      
      // Cache the document
      setDocuments(prev => new Map(prev).set(documentId, document));
      
      return document;
    } catch (error) {
      console.error('Error loading document:', error);
      throw error;
    }
  }, [documents]);

  const getDocumentUrl = useCallback((documentId: string): string => {
    return `/api/documents/${documentId}/file`;
  }, []);

  const openCitation = useCallback(async (citationId: string): Promise<void> => {
    try {
      // Load citation if not cached
      let citation = citations.get(citationId);
      if (!citation) {
        citation = await loadCitation(citationId);
      }

      // Load document if not cached
      if (!documents.has(citation.documentId)) {
        await loadDocument(citation.documentId);
      }

      // Set active document
      setActiveDocumentId(citation.documentId);

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

      // TODO: Emit event for PDF viewer to handle navigation
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

  const addCitations = useCallback((newCitations: Citation[]) => {
    setCitations(prev => {
      const updated = new Map(prev);
      newCitations.forEach(citation => {
        updated.set(citation.id, citation);
      });
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

  return (
    <CitationContext.Provider value={value}>
      {children}
    </CitationContext.Provider>
  );
};

export default CitationContext;