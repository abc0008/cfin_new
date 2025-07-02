import { Citation, ClaudeCitation, CitationRect } from '@/types/citation';
import { IHighlight } from 'react-pdf-highlighter';
import { findTextPdfCoordinates, searchMultiplePages } from './textSearch';
import { pdfToViewport, viewportToScaled } from './coordinates';

declare module 'react-pdf-highlighter' {
  interface IHighlight {
    isAICitation?: boolean;
    rawClaudeCitation?: ClaudeCitation;
  }
}

export const convertCitationToHighlight = (citation: Citation): IHighlight => {
  // Handle empty rects by using a placeholder
  const boundingRect = citation.rects[0] || {
    x1: 0, y1: 0, x2: 0, y2: 0, width: 0, height: 0, pageNumber: 1
  };

  // Convert CitationRect to the format expected by react-pdf-highlighter
  const convertRect = (rect: CitationRect) => ({
    x1: rect.x1,
    y1: rect.y1,
    x2: rect.x2,
    y2: rect.y2,
    width: rect.width,
    height: rect.height,
    pageNumber: rect.pageNumber
  });

  return {
    id: citation.highlightId,
    content: {
      text: citation.citedText
    },
    position: {
      boundingRect: convertRect(boundingRect),
      rects: citation.rects.length > 0 ? citation.rects.map(convertRect) : [convertRect(boundingRect)],
      pageNumber: citation.startPageNumber || 1
    },
    comment: {
      text: citation.citedText,
      emoji: "📍"
    },
    isAICitation: true,
    rawClaudeCitation: {
      type: citation.type,
      cited_text: citation.citedText,
      document_index: 0,
      document_title: citation.documentTitle,
      start_page_number: citation.startPageNumber,
      end_page_number: citation.endPageNumber,
      start_char_index: citation.startCharIndex,
      end_char_index: citation.endCharIndex,
      start_block_index: citation.startBlockIndex,
      end_block_index: citation.endBlockIndex
    }
  };
};

export const searchAndHighlightText = async (
  pdfDocument: any, // PDFDocumentProxy
  citedText: string,
  startPageNumber?: number,
  endPageNumber?: number,
  viewport?: any // PDFPageViewport
): Promise<IHighlight | null> => {
  try {
    // Search for the text in the specified page range
    const searchResults = await searchMultiplePages(
      pdfDocument,
      citedText,
      startPageNumber || 1,
      endPageNumber || startPageNumber
    );

    if (searchResults.length === 0) {
      console.warn(`Could not find text: "${citedText}"`);
      return null;
    }

    // Use the first result
    const result = searchResults[0];
    
    // Convert to viewport coordinates if viewport is provided
    let rects = result.rects;
    if (viewport) {
      rects = result.rects.map(rect => {
        const viewportRect = pdfToViewport(rect, viewport);
        return {
          ...viewportRect,
          x1: viewportRect.left,
          y1: viewportRect.top,
          x2: viewportRect.left + viewportRect.width,
          y2: viewportRect.top + viewportRect.height,
          pageNumber: rect.pageNumber
        };
      });
    }

    // Create a highlight object
    const highlight: IHighlight = {
      id: `search-${Date.now()}`,
      content: {
        text: citedText
      },
      position: {
        boundingRect: rects[0] ? {
          ...rects[0],
          width: rects[0].x2 - rects[0].x1,
          height: rects[0].y2 - rects[0].y1
        } : {
          ...result.boundingRect,
          width: result.boundingRect.x2 - result.boundingRect.x1,
          height: result.boundingRect.y2 - result.boundingRect.y1
        },
        rects: rects.map(rect => ({
          ...rect,
          width: rect.x2 - rect.x1,
          height: rect.y2 - rect.y1
        })),
        pageNumber: result.pageNumber
      },
      comment: {
        text: citedText,
        emoji: "🔍"
      }
    };

    return highlight;
  } catch (error) {
    console.error('Error searching for text:', error);
    return null;
  }
};

export const getCitationSignature = (citation: Citation): string => {
  return `${citation.documentId}-${citation.startPageNumber || 0}-${citation.citedText}`;
};

export const deduplicateCitations = (citations: Citation[]): Citation[] => {
  const seen = new Set<string>();
  return citations.filter(citation => {
    const signature = getCitationSignature(citation);
    if (seen.has(signature)) {
      return false;
    }
    seen.add(signature);
    return true;
  });
};

export const handleStreamingCitation = (
  delta: { type: 'citations_delta'; citation: ClaudeCitation },
  currentBlockIndex: number,
  pendingCitations: Map<number, Citation[]>,
  documentMap: Map<number, string>
): void => {
  // Import the transform function
  const { transformClaudeCitation } = require('./citationTransform');
  
  const citations = pendingCitations.get(currentBlockIndex) || [];
  
  // Transform the citation to handle field name differences
  const newCitation = transformClaudeCitation(
    delta.citation, 
    documentMap,
    citations.length
  );
  
  // Check if we have a valid document ID
  if (!newCitation.documentId) {
    console.warn(`No document found for citation:`, delta.citation);
    return;
  }
  
  // Deduplicate by signature
  const signature = getCitationSignature(newCitation);
  if (!citations.some(c => getCitationSignature(c) === signature)) {
    citations.push(newCitation);
    pendingCitations.set(currentBlockIndex, citations);
    console.log(`Added citation ${newCitation.id} to block ${currentBlockIndex}`, newCitation);
  }
};

export const convertHighlightToCitation = (
  highlight: IHighlight,
  documentId: string
): Omit<Citation, 'id'> => {
  // Extract page number from position
  const pageNumber = highlight.position.pageNumber || 1;
  
  // Convert rects to CitationRect format
  const rects: CitationRect[] = highlight.position.rects.map((rect: any) => ({
    x1: rect.x1,
    y1: rect.y1,
    x2: rect.x2,
    y2: rect.y2,
    width: rect.width || (rect.x2 - rect.x1),
    height: rect.height || (rect.y2 - rect.y1),
    pageNumber: pageNumber
  }));

  return {
    highlightId: highlight.id,
    documentId: documentId,
    documentTitle: '', // This will need to be filled by the caller
    type: 'page_location', // Default to page location for user-created highlights
    citedText: highlight.content?.text || '',
    rects: rects,
    startPageNumber: pageNumber,
    endPageNumber: pageNumber
  };
};