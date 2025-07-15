---
Title: Citation → Highlight → Scroll Data Flow
Date: 2025-07-10
---

# Citation / Highlight Workflow (FDAS)

> A developer-oriented reference that tracks how a citation ID created during chat streaming becomes a yellow rectangle in the PDF viewer – and why navigation occasionally fails.

---

## 1. Streaming-time Citation Creation
| Stage | File / Method | Notes |
|-------|---------------|-------|
| **Claude tool streaming** | `src/hooks/useStreamingChatWithCitations.ts` | As deltas arrive the hook builds **placeholder citations** via `citationService.handleStreamingCitation()`.
| Placeholder shape | `cite-<timestamp>-<rand>` ID, _no_ `rects` / `startPageNumber`. Stored in a `pendingCitations` `Map` keyed by chat-block index. |

## 2. CitationContext – single source of truth
| Action | File / Method |
|--------|---------------|
| `addCitations()` merge | `src/context/CitationContext.tsx` | Merges arrays by signature `documentId-page-citedText`, preserves the first ID it sees, patches in missing `rects` later. |
| Navigation API | `openCitation(id)` | Dispatches `CustomEvent<'citation-navigation'>` with the citation object. |

## 3. Viewer Wrapper (`CitationEnabledPDFViewer`)
| Action | File / Method |
|--------|---------------|
| Placeholder injection | `localCitations` `useState` + update inside `handleCitationNavigation` | Ensures the clicked placeholder arrives at the viewer immediately. |
| Props passed to viewer | `extraCitations={localCitations}`, `highlightId={navigatingToCitation}` |

## 4. PDF Viewer (`PDFViewer`)
| Concern | Implementation |
|---------|----------------|
| **Merge logic** | `combinedCitations = extraCitations ⊕ backendCitations` (by ID) |
| Highlight conversion | `lib/pdf/citationService.convertCitationToHighlight` – scales rects, assigns `id = citation.id`, keeps the original UUID. |
| Scroll effect | `useEffect([highlightId, allHighlights])` waits until a highlight with that ID exists **and** helper ref ready, then runs `scrollToHighlight()` which uses the library helper or DOM fallback. |

## 5. Backend Citations
* Endpoint: `GET /api/documents/{id}/citations`  
  (implemented in `src/lib/api/documents.ts::getDocumentCitations`).
* Returns **enhanced citations** with new UUIDs + `rects` + `startPageNumber`.
* Merge code adds their `rects` onto the existing placeholder (matching by signature).

---

## Current Failure Modes
| # | Symptom | Root Cause |
|---|---------|-----------|
| 1 | Console shows `found: false`, no scrolling | Placeholder never reached viewer; highlight ID absent from `allHighlights`. |
| 2 | Page scrolls but lands on p. 1 | Placeholder had no `startPageNumber`; library picked default = 1. |
| 3 | Yellow rectangle missing after scroll | Backend rects not merged (signature mismatch – whitespace/case differences). |
| 4 | Retry loop exhausts attempts before helper ready | Fixed interval retry starts too early. |
| 5 | Highlight offset / invisible | Absolute rects scaled assuming 612×792; real page size differs. |

---

## Immediate Fixes Implemented
1. **`extraCitations` Prop** – Viewer now accepts placeholders from wrapper.  
2. **Guard in Scroll Effect** – Waits until exact highlight ID exists before attempting scroll.  
3. **Merge-with-Patch Logic** – Back-end rects patch placeholders, retaining original ID.

These changes remove the most common “found: false” loop while keeping API-compatible behaviour.

---

## Recommended Next Steps
1. **Guarantee page number in placeholder**  
   *During streaming set `startPageNumber` when Claude supplies it.*
2. **Standardise IDs**  
   *Pass placeholder UUID to backend so the enhanced citation re-uses it – removes dual-ID complexity.*
3. **Wait for viewer readiness**  
   *Subscribe to `scrollViewerRef` callback instead of fixed retry count.*
4. **Dynamic page-size scaling**  
   *Feed actual `viewport.width/height` into `convertCitationToHighlight`.*

---

_Last updated: 2025-07-10_ 