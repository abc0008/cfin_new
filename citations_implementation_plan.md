Below is a **step-by-step implementation blueprint** for bringing a fully-working, hyperlinkable citation experience to **cfin\_new**.
It is organised in four layers so you can tackle it incrementally and still ship value early.

| Layer   | Goal                            | Scope (main files)                                                    | Ship-ready when …                                                                      |
| ------- | ------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **L-0** | [ ] Fix today's rect-array mismatch | `backend/app/routes/documents.py`, `backend/utils/citation_mapper.py` | backend always returns `rects: List[Rect]`; UI stops crashing on single-rect citations |
| **L-1** | [ ] End-to-end page-level citations | Conversation + Analysis flows, DB & API models, UI click-through      | user can click the "¹" marker in an answer and the PDF opens on the right page         |
| **L-2** | [ ] Fine-grained highlight boxes    | server-side text-→-bbox mapping § or client search fallback           | clicking the marker scrolls *and* draws a yellow box around the cited sentence/number  |
| **L-3** | [ ] Streaming & RAG reuse           | streaming deltas, reuse citations across turns, perf tuning           | citations appear progressively in streaming chat and still work when revisited         |

The table shows "definition of done" for each layer so you can release in slices.

---

## 1  Data-model groundwork (applies to L-0 → L-3)

### 1.1  Backend Pydantic models & aliasing

- [ ] Create **`backend/models/citation.py`**

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

class CitationRect(BaseModel):
    left: float
    top: float
    width: float
    height: float
    pageNumber: int = Field(..., alias="page_number")

class CitationPayload(BaseModel):
    id: str
    documentId: str = Field(..., alias="document_id")
    type: Literal["page_location", "char_location", "content_block_location"]
    startPage: Optional[int] = Field(None, alias="start_page_number")
    endPage: Optional[int] = Field(None, alias="end_page_number")
    startChar: Optional[int] = Field(None, alias="start_char_index")
    endChar: Optional[int] = Field(None, alias="end_char_index")
    startBlock: Optional[int] = Field(None, alias="start_block_index")
    endBlock: Optional[int] = Field(None, alias="end_block_index")
    citedText: str = Field(..., alias="cited_text")
    rects: List[CitationRect] = Field(default_factory=list)
```

*Why?*

* Matches Anthropic spec ("page\_location", "char\_location"…) 
* `rects` **always list** (fix for single-dict bug).

### 1.2  DB migration

- [ ] `alembic revision --autogenerate -m "citations v2"`

*Changes*

| Column                                                                    | Old  | New              |
| ------------------------------------------------------------------------- | ---- | ---------------- |
| `bounding_box`                                                            | JSON | **dropped**      |
| `rects`                                                                   | –    | JSONB (array)    |
| `start_page`,`end_page`,`start_char`,`end_char`,`start_block`,`end_block` | –    | integer/nullable |
| `cited_text`                                                              | –    | text             |

Seeds: migrate existing `bounding_box` → `rects=[bounding_box]` so no data loss.

### 1.3  Frontend typings

- [ ] `nextjs-fdas/src/types/citation.ts`

```ts
export interface CitationRect { left:number; top:number; width:number; height:number; pageNumber:number }
export interface Citation {
  id: string;
  documentId: string;
  type: "page_location"|"char_location"|"content_block_location";
  startPage?: number;
  endPage?: number;
  startChar?: number;
  endChar?: number;
  startBlock?: number;
  endBlock?: number;
  citedText: string;
  rects: CitationRect[];
}
```

Add Zod schema mirroring this (optional → `.optional()`).

---

## 2  L-0 – Rect-array hot-fix (one-day task)

- [ ] *File:* `backend/repositories/citation_repository.py` (new helper).
Replace the old `citation_to_api_schema()` logic in the document router:

```python
def citation_to_api_schema(db_obj: CitationModel) -> CitationPayload:
    rects = db_obj.rects or []
    # if older single-dict payload, wrap in list
    if rects and isinstance(rects, dict):
        rects = [rects]
    return CitationPayload.from_orm({**db_obj.__dict__, "rects": rects})
```

Result: `rects` is always a list – fulfilling the minimal bug fix flagged in the audit.

Frontend already expects an array, so nothing else to do.

---

## 3  L-1 – Page-level clickable citations (MVP)

### 3.1  Creating citations with Claude

#### 3.1.1  Build document blocks

- [ ] In `ClaudeService._prepare_documents()`

```python
def build_claude_doc_blocks(doc_records: List[Document]) -> List[Dict[str, Any]]:
    blocks = []
    for idx, doc in enumerate(doc_records):
        with open(doc.file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        blocks.append(
            {
              "type": "document",
              "source": {
                  "type": "base64",
                  "media_type": "application/pdf",
                  "data": b64,
              },
              "title": doc.filename,
              "context": json.dumps({ "docId": doc.id }),
              "citations": { "enabled": True },
            }
        )
    return blocks
```

*Key*: `citations.enabled=true` 
We stop concatenating text; instead we give Claude the PDFs themselves (with the native Anthropic extraction).

#### 3.1.2  Call messages API

- [ ] Replace existing `ClaudeService.generate_response` call site in `AnalysisService.run_analysis` & `ConversationService.process_user_message`:

```python
anthropic.messages.create(
    model=self.model_name,
    max_tokens=self.max_tokens,
    messages=[
        {"role": "user", "content": doc_blocks + [{"type": "text", "text": user_query}]}
    ],
)
```

### 3.2  Parsing the response

- [ ] Add `ClaudeService.parse_citations(message)`:

```python
def parse_citations(content_blocks, document_map) -> Tuple[str, List[CitationPayload]]:
    """
    Returns rendered_markdown, citations[]
    - Replaces each citation with [^{n}] marker in text.
    """
    rendered_parts = []
    citations: List[CitationPayload] = []
    counter = 1
    for blk in content_blocks:
        if blk["type"] == "text":
            text = blk["text"]
            for cit in blk.get("citations", []):
                cid = str(uuid4())
                doc_db_id = document_map[cit["document_index"]]
                payload = CitationPayload(
                    id=cid,
                    documentId=doc_db_id,
                    **cit,  # page or char indices
                )
                citations.append(payload)
                marker = f"<sup><a href=\"#{cid}\">[{counter}]</a></sup>"
                text += marker
                counter += 1
            rendered_parts.append(text)
    return "".join(rendered_parts), citations
```

Persist each `CitationPayload` to DB, linked to the analysis or message.

### 3.3  API surface

- [ ] *Conversation:* extend `MessageResponse` with `citations: CitationPayload[]` (already modelled).
- [ ] *Analysis:* add `citations: CitationPayload[]` top-level.

Both emitted using `by_alias=True`, thus camelCase (`documentId`, `startPage` …).

### 3.4  Frontend rendering

1. **Global citation cache**
   - [ ] `src/context/CitationContext.tsx` – holds a map `id → Citation`.

2. **Markdown / Chat renderer**
   - [ ] Enhance `MarkdownRenderer.tsx` (and Chat bubble) to parse `<a href="#cid">`.
   - [ ] On `onClick`, call `openCitation(citationId)` from context.

3. **PDFViewer integration**

- [ ] ```tsx
const openCitation = async (cid: string) => {
  const data = citationCache[cid] ?? await citationsApi.getById(cid);
  setActiveDocument(data.documentId);         // ensures correct PDF is loaded
  if (data.type === "page_location") {
    pdfHighlighter.scrollToPage(data.startPage);
  }
}
```

Because `rects` are empty so far, we just scroll to page – still delivering a useful MVP.

---

## 4  L-2 – Precise highlight boxes

Two options; pick one or do both and fall back.

### 4.1  Server-side bbox mapping (accurate, heavier)

*Algorithm*

1. After Claude response, we have `cited_text`, `startPage`.
2. Use **pdfminer.six** to extract the text of that page, locate `cited_text` string offsets.
3. Use pdfminer's LTChar coordinates to collect bounding boxes for the range (similar to react-pdf-highlighter's client code ✧ we saw in `/src/lib/get-client-rects.ts` ).
4. Save these boxes into `CitationPayload.rects`.

- [ ] *Files:* new `backend/pdf_processing/coordinates.py`.

### 4.2  Client-side search (fast, fallback)

- [ ] If `rects` array is empty, inside `PdfHighlighter` call `findText()` (built-in to PDF.js) for `citedText`.  When found, convert selection → rects via the same helper already in the highlighter lib (`getClientRects`) , then call `addHighlight()` with a transient yellow style.

Both approaches yield the same data shape (`rects` list).  So the viewer component only has to test `if (rects.length)` to decide whether to run search.

---

## 5  L-3 – Streaming, reuse & polish

- [ ] *Streaming*: Claude emits `citations_delta` events .  Extend the SSE handler in `ClaudeService.stream_response()` to capture deltas and push incremental markers to the client (same `<sup>` trick).

- [ ] *Reuse across turns*: when users refer again to the same numbers, Claude may duplicate citations.  De-duplicate in `parse_citations()` by `(documentId, startPage, startChar, citedText)` signature.

- [ ] *Performance*: cache base64 PDFs (or better, store plain text when available) to avoid re-encoding for every request.

---

## 6  Risk & compatibility checks

| Risk                                       | Mitigation                                                                                                                                 |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Large PDFs exceed Anthropic 4 MB limit** | keep existing Claude text-extraction fallback for oversized docs; disable citations in that case.                                          |
| **Scanned PDFs (no text)**                 | citations won't work (Anthropic limitation). Detect via `doc.is_scanned`; show tooltip "Citation unavailable for scanned docs."            |
| **Token explosion**                        | pass only *pages likely relevant* (rough heuristic: those containing numeric tables detected during preprocessing) when citations enabled. |
| **Old clients**                            | Front-end already tolerant to unknown keys; new fields are additive.                                                                       |

---

## 7  Timeline & effort

| Task                         | Dev days                               |
| ---------------------------- | -------------------------------------- |
| L-0 quick fix                | 0.5                                    |
| L-1 backend Claude rewrite   | 2                                      |
| L-1 frontend click-through   | 1                                      |
| DB migration & tests         | 1                                      |
| L-2 precise rect mapping     | 2–3 (server) or 1 (client-side search) |
| L-3 streaming polish         | 1                                      |
| **Total (MVP L-1): 4½ days** |                                        |

---

### Deliverables recap

- [ ] **Backend**: new citation model, DB migration, Claude doc-block builder, parser, REST endpoint `/api/citations/{id}`.
- [ ] **Frontend**: Citation context, updated types/Zod, PDFViewer hook, renderer hyperlinking.
- [ ] **Docs**: update README (citations section), add ADR in `/docs/adr/002-citations.md`.

With this plan you will move from partial rect inconsistencies to a robust, first-class citation workflow that **links every figure in the AI answer directly to its exact location in the PDF**—and the architecture remains clean, matching Anthropic's native format and your React highlighter toolkit.
