import { Citation, ClaudeCitation } from '@/types/citation';

/**
 * Transform a Claude citation (with snake_case fields) to the frontend Citation format
 */
export const transformClaudeCitation = (
  claudeCitation: ClaudeCitation,
  documentMap: Map<number, string>,
  citationIndex?: number
): Citation => {
  // Get document ID from map or use the provided one
  const documentId = (claudeCitation as any).documentId || 
    documentMap.get(claudeCitation.document_index) || 
    '';

  // Generate IDs if not provided
  const id = (claudeCitation as any).id || 
    `cite-${Date.now()}-${citationIndex || Math.random()}`;
  const highlightId = (claudeCitation as any).highlightId || 
    `hl-${Date.now()}-${citationIndex || Math.random()}`;

  return {
    id,
    highlightId,
    documentId,
    documentTitle: claudeCitation.document_title || '',
    type: (claudeCitation.type || 'page_location') as Citation['type'],
    citedText: claudeCitation.cited_text || (claudeCitation as any).citedText || '',
    rects: [],  // TODO: Parse from backend when available
    // Handle both snake_case and camelCase field names
    startPageNumber: claudeCitation.start_page_number || 
      (claudeCitation as any).startPageNumber || 
      undefined,
    endPageNumber: claudeCitation.end_page_number || 
      (claudeCitation as any).endPageNumber || 
      undefined,
    startCharIndex: claudeCitation.start_char_index || 
      (claudeCitation as any).startCharIndex || 
      undefined,
    endCharIndex: claudeCitation.end_char_index || 
      (claudeCitation as any).endCharIndex || 
      undefined,
    startBlockIndex: claudeCitation.start_block_index || 
      (claudeCitation as any).startBlockIndex || 
      undefined,
    endBlockIndex: claudeCitation.end_block_index || 
      (claudeCitation as any).endBlockIndex || 
      undefined,
  };
};

/**
 * Transform an array of citations from the API response
 */
export const transformCitations = (
  citations: any[],
  documentMap?: Map<number, string>
): Citation[] => {
  if (!citations || !Array.isArray(citations)) {
    return [];
  }
  
  const defaultMap = documentMap || new Map<number, string>();
  
  return citations.map((citation, index) => {
    // Handle both ClaudeCitation format and already transformed format
    if (citation.highlightId && citation.documentId) {
      // Already in Citation format
      return citation as Citation;
    }
    
    // Transform from ClaudeCitation format
    return transformClaudeCitation(citation, defaultMap, index);
  });
};