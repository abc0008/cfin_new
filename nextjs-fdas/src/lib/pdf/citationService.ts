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

export const convertCitationToHighlight = (citation: Citation, viewport?: any): IHighlight => {
  // Use real viewport dimensions
  const PAGE_WIDTH = viewport?.width || 612;
  const PAGE_HEIGHT = viewport?.height || 792;

  const toScaledRect = (rect: CitationRect) => {
    // Some backend citations only give width/height + pageNumber. Default missing
    // coordinates to 0 so we at least jump to the correct page.
    const hasCoords = typeof rect.x1 === 'number' && typeof rect.y1 === 'number';
    const x1Abs = hasCoords ? rect.x1 : 0;
    const y1Abs = hasCoords ? rect.y1 : 0;
    const x2Abs = rect.x2 ?? (hasCoords ? x1Abs + (rect.width ?? 0) : 0);
    const y2Abs = rect.y2 ?? (hasCoords ? y1Abs + (rect.height ?? 0) : 0);

    // React-pdf-highlighter expects viewport coordinates (in PDF points) not
    // values normalised to 0-1.  Pass through the absolute values so the
    // overlay is the correct size on the rendered page.
    return {
      x1: x1Abs,
      y1: y1Abs,
      x2: x2Abs,
      y2: y2Abs,
      left: x1Abs,
      top: y1Abs,
      width: x2Abs - x1Abs,
      height: y2Abs - y1Abs,
      pageNumber: rect.pageNumber,
    };
  };

  // If no rects, log warning but create minimal highlight
  if (citation.rects.length === 0) {
    console.warn('Citation has no rects, using placeholder');
  }

  // Use first rect or fall back to placeholder at (0,0)
  const boundingRect = citation.rects.length > 0
    ? toScaledRect(citation.rects[0])
    : {
        x1: 0,
        y1: 0,
        x2: 100,
        y2: 15,
        left: 0,
        top: 0,
        width: 100,
        height: 15,
        pageNumber: citation.startPageNumber || 1,
      };

  // Convert all rects (or placeholder) for React component
  const convertRect = (rect: CitationRect) => toScaledRect(rect);

  return {
    // Always use the stable citation UUID as the main highlight id so the
    // chat-panel click (which passes citation.id) matches a highlight.
    id: citation.id,
    content: {
      text: citation.citedText
    },
    position: {
      boundingRect: boundingRect,
      rects: citation.rects.length > 0 ? citation.rects.map(toScaledRect) : [boundingRect],
      pageNumber: citation.startPageNumber || 1
    },
    comment: {
      text: citation.citedText,
      emoji: "" // No pin icon; we rely on rect highlight only
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
      end_block_index: citation.endBlockIndex,
      highlightId: citation.highlightId as unknown
    } as any
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