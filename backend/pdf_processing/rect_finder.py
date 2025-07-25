"""Utility functions for mapping cited text to bounding rectangles in PDF pages.

We keep this logic in a separate module so it can be imported from both
routes and services without creating heavy dependencies elsewhere.

All coordinates returned are in **PDF space** (origin top-left, unscaled)
so the frontend can convert them via pdf.js viewport scaling.
"""
from __future__ import annotations

from typing import List, Dict
import re

import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)

__all__ = ["find_rects_for_text"]


def _normalise_whitespace(text: str) -> str:
    """Collapse runs of whitespace so the search is more robust."""
    return re.sub(r"\s+", " ", text.strip())


def find_rects_for_text(
    pdf_path: str | None = None,
    pdf_bytes: bytes | None = None,
    *,
    page_number: int,
    cited_text: str,
    max_hits: int = 1,
) -> List[Dict[str, float]]:
    """Return bounding boxes for *cited_text* on *page_number*.

    At least one of ``pdf_path`` or ``pdf_bytes`` must be provided.
    The first *max_hits* matches are returned.  If no match is found an
    empty list is returned.

    The rectangle dicts follow the shape already used in the CitationRect
    Pydantic model:
    ``{"x1", "y1", "x2", "y2", "width", "height", "pageNumber"}``
    """
    if pdf_path is None and pdf_bytes is None:
        raise ValueError("Either pdf_path or pdf_bytes must be supplied")

    cited_text_norm = _normalise_whitespace(cited_text)

    logger.debug("🔍 find_rects_for_text(page=%s) – searching for: '%s' (normalized from %d to %d chars)", 
                 page_number, cited_text_norm[:50] + "..." if len(cited_text_norm) > 50 else cited_text_norm, 
                 len(cited_text), len(cited_text_norm))
    if not cited_text_norm:
        return []

    # Open the document
    if pdf_bytes is not None:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    else:
        doc = fitz.open(pdf_path)  # type: ignore[arg-type]

    try:
        # Decide which pages to scan. If *page_number* > 0 we only scan that
        # specific page (1-indexed coming in, convert to 0-indexed for PyMuPDF).
        pages_to_scan = [page_number - 1] if page_number > 0 else list(range(doc.page_count))

        # Collect all rects from the selected pages
        all_rects = []
        for pg in pages_to_scan:
            # Guard against out-of-range page numbers
            if pg < 0 or pg >= doc.page_count:
                continue
            page = doc.load_page(pg)
            # PyMuPDF Page objects expose `search_for`, but the type stubs may not
            # include it, so we silence the type checker.
            page_rects = page.search_for(cited_text_norm)  # type: ignore[attr-defined]
            for r in page_rects:
                all_rects.append({
                    "x1": r.x0,
                    "y1": r.y0,
                    "x2": r.x1,
                    "y2": r.y1,
                    "width": r.width,
                    "height": r.height,
                    "pageNumber": pg + 1
                })
        # Merge overlapping rects
        merged_rects = merge_overlapping_rects(all_rects)
        
        if merged_rects:
            logger.debug("✅ Found %d rect(s) for '%s' on page(s) %s", 
                        len(merged_rects), cited_text_norm[:30] + "..." if len(cited_text_norm) > 30 else cited_text_norm,
                        list(set(r["pageNumber"] for r in merged_rects)))
        else:
            logger.debug("❌ No rects found for '%s'", cited_text_norm[:50] + "..." if len(cited_text_norm) > 50 else cited_text_norm)
            
        return merged_rects[:max_hits]
    finally:
        doc.close()

def merge_overlapping_rects(rects: List[Dict[str, float]]) -> List[Dict[str, float]]:
    if not rects:
        return []
    # Group by page
    rects_by_page = {}
    for r in rects:
        page = r["pageNumber"]
        if page not in rects_by_page:
            rects_by_page[page] = []
        rects_by_page[page].append(r)
    merged = []
    for page_rects in rects_by_page.values():
        page_merged = []
        page_rects.sort(key=lambda r: (r["y1"], r["x1"]))
        current = page_rects[0]
        for next_r in page_rects[1:]:
            # Only merge if the rectangles **overlap** (not just touch/are adjacent).
            # We require at least 1-px overlap on **both** axes. This prevents the
            # entire table row being merged into a single giant rect when searching
            # for multiple numbers on the same line.

            horizontally_overlaps = current["x1"] < next_r["x2"] and next_r["x1"] < current["x2"]
            vertically_overlaps = current["y1"] < next_r["y2"] and next_r["y1"] < current["y2"]

            if horizontally_overlaps and vertically_overlaps:
                current["x1"] = min(current["x1"], next_r["x1"])
                current["y1"] = min(current["y1"], next_r["y1"])
                current["x2"] = max(current["x2"], next_r["x2"])
                current["y2"] = max(current["y2"], next_r["y2"])
                current["width"] = current["x2"] - current["x1"]
                current["height"] = current["y2"] - current["y1"]
            else:
                page_merged.append(current)
                current = next_r
        page_merged.append(current)
        merged.extend(page_merged)
    return merged 