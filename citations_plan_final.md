Synthesized Implementation Plan for PDF Citations with Deep Links

Phase 1: Backend Infrastructure (2-3 days)

1.1 Database Schema Updates
- Extend citations table with new columns:
  - type (enum: page_location, char_location, content_block_location)
  - start_page_number, end_page_number (nullable integers)
  - start_char_index, end_char_index (nullable integers)
  - start_block_index, end_block_index (nullable integers)
  - cited_text (text)
  - rects (JSONB array replacing single bounding_box)
  - highlight_id (UUID string)
  - document_title (string)
- Create Alembic migration to:
  - Add new columns
  - Migrate existing bounding_box → rects array
  - Drop old bounding_box column

1.2 Pydantic Model Updates
- Update backend/models/citation.py:
  - Add CitationRect model with PDF coordinates
  - Ensure all models use alias_generator=to_camel
  - Add rects: List[CitationRect] field
  - Include all location type fields from Anthropic spec

1.3 Files API Integration
- Update claude_file_client.py:
  - Add beta header support: anthropic-beta: files-api-2025-04-14
  - Implement file upload with proper error handling
  - Store file_id in document records for reuse
- Modify document processing to use Files API:
{
    "type": "document",
    "source": {"type": "file", "file_id": file_id},
    "title": filename,
    "context": metadata_json,
    "citations": {"enabled": True}
}

1.4 Citation Parsing Service
- Implement parse_citations method to:
  - Extract citations from content blocks
  - Map document_index to database document IDs
  - Generate unique highlight_id for each citation
  - Return both rendered text with markers and citation objects
  - Handle all three citation types (page, char, content_block)

Phase 2: Frontend Infrastructure (2-3 days)

2.1 Type Definitions
- Create comprehensive src/types/citation.ts:
interface CitationRect {
  x1: number; y1: number; x2: number; y2: number;
  width: number; height: number; pageNumber: number;
}

interface Citation {
  id: string;
  highlightId: string;
  documentId: string;
  type: 'page_location' | 'char_location' | 'content_block_location';
  citedText: string;
  rects: CitationRect[];
  // ... location fields
}

2.2 Citation Context
- Implement React context for global citation management
- Cache citations by ID for efficient access
- Provide openCitation method for navigation

2.3 Message Renderer Enhancement
- Parse citation markers [1], [2] in message text
- Convert to clickable elements with proper accessibility
- Trigger citation navigation on click

2.4 Coordinate Conversion Utilities
- Implement findTextPdfCoordinates for text search in PDFs
- Add viewportToScaled conversion for react-pdf-highlighter
- Handle PDF user space → viewport → scaled coordinate pipeline

Phase 3: PDF Viewer Integration (1-2 days)

3.1 Citation to Highlight Conversion
- Enhance citationService.ts:
  - Store raw Anthropic citation in IHighlight
  - Convert citation rects to highlight positions
  - Handle missing rects with client-side text search

3.2 PDF Navigation
- Implement openCitation handler:
  - Load correct document if not active
  - Scroll to citation page
  - Apply highlight rectangles
  - Fallback to text search if no rects

3.3 Text Search Fallback
- Use PDF.js findText API for citations without rects
- Convert found positions to highlight rectangles
- Cache results for performance

Phase 4: Streaming & Polish (1 day)

4.1 Streaming Support
- Handle citations_delta events in SSE stream
- Update UI incrementally as citations arrive
- Maintain citation order and deduplication

4.2 Performance Optimizations
- Cache file_ids to avoid re-uploading PDFs
- Use cache_control on document blocks
- Implement citation deduplication by signature

4.3 Error Handling
- Handle large PDFs exceeding Anthropic limits
- Detect scanned PDFs without extractable text
- Graceful degradation when citations unavailable

Implementation Priority & Approach

1. Start with L-0 rect array fix - Quick win, prevents crashes
2. Implement basic page-level citations (L-1) - MVP functionality
3. Add precise highlighting (L-2) - Enhanced user experience
4. Complete streaming support (L-3) - Production readiness

Key Technical Decisions

1. Coordinate Strategy: Use client-side text search as primary approach (simpler than server-side pdfminer)
2. Citation Markers: Use [1] format in messages for clickability
3. Storage: Always store rects as array, even if single rectangle
4. Caching: Reuse file_ids and implement citation caching

Testing Requirements

- Unit tests for citation parsing and coordinate conversion
- Integration tests for Files API upload/retrieval
- E2E tests for citation click → PDF highlight flow
- Performance tests with large PDFs
- Accessibility testing for citation markers

Deliverables

1. Database migration script
2. Updated backend models and services
3. Frontend citation components and utilities
4. Enhanced PDF viewer with citation support
5. Comprehensive test suite
6. Updated documentation with citation workflow

This plan synthesizes the best aspects of all four proposals while addressing gaps and ensuring a robust implementation of the citations feature.