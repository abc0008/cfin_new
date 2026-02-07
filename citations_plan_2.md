ummary

The repo already contains core models and UI code for citations.
Backend Pydantic models define different citation types and text blocks.
The SQLAlchemy Citation table stores a page number and bounding box but lacks multi‑rect support.
Frontend TypeScript types describe citations with a rects array used by PDFViewer and other components, with matching Zod schemas for runtime validation.
PDFViewer loads citations from the API and converts them into react-pdf-highlighter highlights when a document is opened.
Helper functions translate between citations and highlights.

citations_implementation_plan.md lays out a multi‑layer roadmap. It starts by defining new backend and frontend citation shapes, replacing the single bounding box with an array of rectangles and adding explicit start/end coordinates.
Layer L‑0 introduces a helper ensuring the API always returns a rects list.
Layer L‑1 describes uploading PDFs via the Files API, enabling citations, parsing the citation blocks from Claude’s response, persisting them, and exposing clickable markers in the UI.
Layer L‑2 adds precise highlight boxes either server‑side via pdfminer or client‑side text search.
Layer L‑3 covers streaming citation deltas and deduplication across turns.

The project README also emphasizes “Linked PDF annotations and highlighting (inspired by react-pdf-highlighter)" as a key feature.

Implementation Plan

Model & Database Updates
Extend backend/models/citation.py to match the plan’s CitationRect and CitationPayload structures.
Add fields for start/end page, char, and block indices plus a list of rects.
Run an Alembic migration to:
Drop the old bounding_box column.
Add rects JSONB, start/end coordinate columns, highlight_id (string), and cited_text.
Migrate existing data by wrapping any bounding_box values in a single‑element rects array.
Repository & API Adjustments
Create citation_repository.py (as proposed in L‑0) with a helper converting ORM citations to the new Pydantic CitationPayload, ensuring rects is always an array.
Update document_repository and conversation_repository to store and retrieve citations using the new schema.
Expose /api/citations/{id} and update /api/documents/{document_id}/citations to return the new format.
Claude Integration
Modify ClaudeService._prepare_documents to build document blocks using the Files API and set citations: {enabled: True} as described in the plan.
Replace previous text‑concatenation calls in AnalysisService.run_analysis and ConversationService.process_user_message with the new anthropic.messages.create invocation that sends these document blocks.
Implement ClaudeService.parse_citations to walk through content blocks, create CitationPayload objects, insert <sup> markers, and return both rendered text and the citation list.
Store the resulting citations and associate them with messages or analyses.
Frontend Typings & Context
Add src/types/citation.ts mirroring the CitationPayload interface (id, documentId, type, start/end coords, rects).
Ensure corresponding Zod schema is added for validation.
Implement a CitationContext (global map id → citation) so chat messages can resolve citation references.
Update MarkdownRenderer and chat components to detect <a href="#cid"> markers and call openCitation(cid).
PDF Viewer Integration
Extend PDFViewer with an openCitation handler. When invoked, ensure the referenced document is loaded, then:
If the citation has page numbers, scroll to that page via PdfHighlighter.
If rects are present, highlight them directly; otherwise, use PDF.js findText to locate citedText and draw temporary highlights.
Bounding Box Generation
Server option: implement backend/pdf_processing/coordinates.py to locate text within the PDF using pdfminer and derive bounding boxes as in the plan.
Client fallback: if a citation lacks rects, let PDFViewer run findText() and convert the selection using getClientRects from the highlighter library.
Streaming & Deduplication
Enhance ClaudeService.stream_response to capture citations_delta events and forward them incrementally so the UI can display markers as text streams in.
De‑duplicate citations by (documentId, startPage, startChar, citedText) when adding them to the cache.
Testing & Documentation
Update existing citation tests (test_citation_integration.py, test_citations_with_pdf.py) to expect the new schema.
Document the new API contract and frontend usage in README and add an ADR as suggested by the plan.
This staged approach builds on the current foundation—Pydantic and Zod models, database tables, API routes, and a React PDF viewer—to deliver fully linked citations that scroll to and highlight the cited text in the PDF.

<Important_Notes>
Summary

backend/models/citation.py already defines Pydantic models for three kinds of citations, mapping fields like startCharIndex or startPageNumber and storing a list of citations within each content block.
Front‑end types mirror those fields, with each Citation containing highlightId, page number and bounding rectangles for PDF highlights.
The helper citationService.ts converts between a Citation and react-pdf-highlighter’s IHighlight type so citations can be rendered in the viewer.
pdf_highlighter_repo.txt shows the structure of the react-pdf-highlighter library, including components such as PdfHighlighter, PdfLoader, and utility functions for bounding‑box calculations.
citations_implementation_plan.md lays out a phased approach for fully linking citations to PDF pages and highlights, starting with correcting the rectangle array bug, then adding page-level citations, then bounding boxes, and finally streaming support
</Important_Notes>