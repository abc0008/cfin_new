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
  // CRITICAL FIX: Always use the first/only document if document_index is 0 or undefined
  let documentId = (claudeCitation as any).documentId;
  
  if (!documentId) {
    // If document_index is provided, try to get from map
    if (claudeCitation.document_index !== undefined) {
      documentId = documentMap.get(claudeCitation.document_index);
    }
    
    // If still no documentId and we have any documents, use the first one
    // This handles the common case where there's only one document
    if (!documentId && documentMap.size > 0) {
      // For single document case or when document_index is 0
      if (documentMap.size === 1 || claudeCitation.document_index === 0) {
        documentId = Array.from(documentMap.values())[0];
      }
    }
  }
  
  documentId = documentId || '';

  console.log('[citationTransform] transformClaudeCitation:', {
    claudeCitation,
    document_index: claudeCitation.document_index,
    documentMap: Array.from(documentMap.entries()),
    resolvedDocumentId: documentId,
    mapSize: documentMap.size
  });

  // Use IDs from backend, don't generate temporary ones
  const id = (claudeCitation as any).id || '';
  const highlightId = (claudeCitation as any).highlightId || '';

  return {
    id,
    highlightId,
    documentId,
    documentTitle: claudeCitation.document_title || '',
    type: (claudeCitation.type || 'page_location') as Citation['type'],
    citedText: claudeCitation.cited_text || (claudeCitation as any).citedText || '',
    rects: (claudeCitation as any).rects || [],  // Use rects from backend if available
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