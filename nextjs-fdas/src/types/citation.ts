export interface CitationRect {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  width: number;
  height: number;
  pageNumber: number;
}

export interface Citation {
  id: string;
  highlightId: string;
  documentId: string;
  documentTitle: string;
  type: 'page_location' | 'char_location' | 'content_block_location';
  citedText: string;
  rects: CitationRect[];
  startPageNumber?: number;
  endPageNumber?: number;
  startCharIndex?: number;
  endCharIndex?: number;
  startBlockIndex?: number;
  endBlockIndex?: number;
  messageId?: string;
  analysisId?: string;
}

export interface ClaudeCitation {
  type: string;
  cited_text: string;
  document_index: number;
  document_title: string;
  start_page_number?: number;
  end_page_number?: number;
  start_char_index?: number;
  end_char_index?: number;
  start_block_index?: number;
  end_block_index?: number;
}

export interface CitationPayload {
  id: string;
  documentId: string;
  type: 'page_location' | 'char_location' | 'content_block_location';
  citedText: string;
  documentTitle: string;
  highlightId: string;
  rects: CitationRect[];
  startPageNumber?: number;
  endPageNumber?: number;
  startCharIndex?: number;
  endCharIndex?: number;
  startBlockIndex?: number;
  endBlockIndex?: number;
  page?: number; // Legacy field for backward compatibility
  text?: string;  // Legacy field for backward compatibility
}

export interface CitationApiResponse {
  text: string;
  citations: Citation[];
}

export interface DocumentBlock {
  type: 'document';
  source: {
    type: 'file';
    file_id: string;
  };
  title: string;
  context: string;
  citations: {
    enabled: boolean;
  };
}