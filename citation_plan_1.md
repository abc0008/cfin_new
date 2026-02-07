mplementation Plan

1. Review current models and schemas
The backend already has a Citation Pydantic model with union types for char_location, page_location, and content_block_location.
The document model stores citations and basic bounding‑box data.
Citations are persisted in the DB with columns page, text, section and bounding_box.
The frontend Zod schema defines Citation with highlightId, page, and rects fields.
Conversion helpers already map between citations and react-pdf-highlighter highlights.
These structures form the basis for the new feature.

2. Enhance backend citation model
Extend the citations table to store the citation type, location indices, and an array of rectangles:
Add columns type, start_page_number, end_page_number,
start_char_index, end_char_index, start_block_index, end_block_index,
rects (JSON array), and highlight_id.
Remove the old bounding_box column as suggested in the plan.
Create an Alembic migration to add these fields and migrate any existing data (wrap single bounding boxes into rects).
Update Pydantic Citation models to include the new fields and to
always expose rects as a list.
Modify document_repository.citation_to_api_schema so returned citations include these fields and always supply an array for rects (see the L‑0 fix).
3. Integrate Claude’s citation output
When uploading or analyzing PDFs, use the Files API and enable citations in the document block:
{
    "type": "document",
    "source": {"type": "file", "file_id": claude_file_id},
    "title": filename,
    "citations": {"enabled": True}
}
(from PDF support docs)

In ClaudeService (or the LangGraph service), parse each content block’s citations list according to the official response format:
{
    "type": "page_location",
    "cited_text": "...",
    "document_index": 0,
    "start_page_number": 5,
    "end_page_number": 6
}
Convert these citations into the new Citation DB schema. Assign a highlight_id (UUID) so the frontend can reference the exact highlight.
Save citation rectangles if available in the API response. For PDFs that do not return rectangles, attempt server‑side text search using pdfminer to compute bounding boxes as proposed in the L‑2 section.
4. API endpoints
/api/documents/{id}/citations already returns a list of Citation objects.
Extend the API to fetch a single citation by ID (/api/documents/{id}/citations/{citation_id}) which is already scaffolded in document.py.
Add an endpoint /api/citations/{id} if direct access without document context is useful.
5. Frontend state and rendering
Update frontend types to match the new citation model if any fields change.
Implement a CitationContext to cache citation data globally so that the chat component and PDF viewer can coordinate.
In the chat/analysis renderer, replace each citation in the AI text with a superscript link:
<Text>
  {block.text}
  {block.citations?.map((c, i) =>
    <sup key={c.id}><a href={`#${c.id}`}>[{i+1}]</a></sup>
  )}
</Text>
(derived from the parsing step in the plan)

On link click, open the corresponding PDF in PDFViewer and scroll to the highlight:
const openCitation = async (id: string) => {
  const citation = await citationsApi.getById(id);
  setActiveDocument(citation.documentId);
  pdfHighlighter.scrollToHighlight(id);
}

PDFViewer already supports scrolling to a highlight ID and displaying highlights using react-pdf-highlighter. Use convertCitationToHighlight to convert server citations into highlighter objects.
When citations lack rectangles, the client can run a text search via the highlighter library (fallback from the plan).
6. Files API integration and caching
Reuse claude_file_id when the same PDF is analyzed again to avoid re‑uploading and reduce latency (already stored in DocumentRepository.update_document_content).
Consider using cache_control when sending document blocks so that large PDFs are cached server-side.
7. Streaming support (optional)
Capture citations_delta events during streaming responses and append them to the current text block, then send incremental updates to the frontend.
8. Testing
Unit tests for citation parsing and database insertion.
Endpoint tests verifying that citations are returned in the new format.
Frontend integration tests ensuring clicking a citation in the chat opens the PDF at the correct page.
Manual testing with example PDFs (e.g., test.pdf included in the repo) to verify highlight placement.
9. Documentation
Update README sections on “Document Processing” to highlight the citation workflow and reference react-pdf-highlighter usage. The repository already advertises linked PDF annotations as a feature.
Provide an ADR or developer doc summarizing the architecture for citations (as suggested at the end of the implementation plan).
By following these steps, the system will leverage the Files API and Claude’s PDF citation output to create hyperlinkable citations. Users will be able to click a citation in chat or analysis results and automatically view the highlighted portion in the PDF via the React PDF Highlighter integration. This delivers a seamless end‑to‑end citation experience across backend and frontend.

<Important_Notes>
Summary

backend/models/citation.py already defines Pydantic models for three kinds of citations, mapping fields like startCharIndex or startPageNumber and storing a list of citations within each content block.
Front‑end types mirror those fields, with each Citation containing highlightId, page number and bounding rectangles for PDF highlights.
The helper citationService.ts converts between a Citation and react-pdf-highlighter’s IHighlight type so citations can be rendered in the viewer.
pdf_highlighter_repo.txt shows the structure of the react-pdf-highlighter library, including components such as PdfHighlighter, PdfLoader, and utility functions for bounding‑box calculations.
citations_implementation_plan.md lays out a phased approach for fully linking citations to PDF pages and highlights, starting with correcting the rectangle array bug, then adding page-level citations, then bounding boxes, and finally streaming support
</Important_Notes>