// Using 'any' for PDFJSPage and PDFJSTextContentItem as direct import might be complex
// depending on how pdfjs-dist is structured and re-exported in the project.
// These should ideally be replaced with actual types from pdfjs-dist if easily available.
type PDFJSPage = any; // Should be pdfjsDist.PDFPageProxy
type PDFJSTextContentItem = any; // Should be pdfjsDist.TextItem

export interface PdfRect {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  pageNumber: number;
}

interface TextItemWithOffset {
  item: PDFJSTextContentItem;
  itemIndex: number;
  pageCharOffset: number; // Character offset of this item's start within the concatenated page text
}

/**
 * Finds the PDF user space coordinates of a given text string on a PDF page.
 * @param page PDF.js page proxy
 * @param searchText The text to search for
 * @returns A promise that resolves to an object containing bounding box and rects in PDF coordinates, or null if not found.
 */
export async function findTextPdfCoordinates(
  page: PDFJSPage,
  searchText: string
): Promise<{ boundingRect: PdfRect; rects: PdfRect[]; pageNumber: number } | null> {
  if (!searchText || searchText.trim() === "") {
    return null;
  }

  const textContent = await page.getTextContent();
  if (!textContent || !textContent.items || textContent.items.length === 0) {
    return null;
  }

  const pageNumber = page.pageNumber;
  let fullPageText = "";
  const itemsWithOffsets: TextItemWithOffset[] = [];

  textContent.items.forEach((item: PDFJSTextContentItem, index: number) => {
    itemsWithOffsets.push({
      item,
      itemIndex: index,
      pageCharOffset: fullPageText.length,
    });
    fullPageText += item.str;
    if (item.hasEOL) {
      fullPageText += "\n"; // Add newline for EOL, helps with matching text that might span lines
    }
  });

  // Normalize whitespace in both fullPageText and searchText for more robust matching.
  // Replace multiple spaces/newlines with a single space.
  const normalizedFullPageText = fullPageText.replace(/\s+/g, " ").trim();
  const normalizedSearchText = searchText.replace(/\s+/g, " ").trim();

  if (normalizedSearchText.length === 0) return null;

  let matchStartIndex = normalizedFullPageText.indexOf(normalizedSearchText);
  if (matchStartIndex === -1) {
    // Fallback: try without newline EOLs if initial match fails
    fullPageText = "";
    itemsWithOffsets.length = 0; // Clear array
    textContent.items.forEach((item: PDFJSTextContentItem, index: number) => {
      itemsWithOffsets.push({
        item,
        itemIndex: index,
        pageCharOffset: fullPageText.length,
      });
      fullPageText += item.str;
    });
    const nonEOLFullPageText = fullPageText.replace(/\s+/g, " ").trim();
    matchStartIndex = nonEOLFullPageText.indexOf(normalizedSearchText);
    if (matchStartIndex === -1) {
      console.warn(`Cited text "${normalizedSearchText}" not found on page ${pageNumber}.`);
      return null;
    }
  }


  const matchEndIndex = matchStartIndex + normalizedSearchText.length;

  const foundPdfRects: PdfRect[] = [];
  let currentOverallCharIndex = 0;

  for (const { item, pageCharOffset } of itemsWithOffsets) {
    const itemText = item.str.replace(/\s+/g, " ").trim(); // Normalize item text similarly for length calculation
    const itemEndPageCharOffset = pageCharOffset + itemText.length;

    // Check if this item overlaps with the search text
    const overlapStart = Math.max(pageCharOffset, matchStartIndex);
    const overlapEnd = Math.min(itemEndPageCharOffset, matchEndIndex);

    if (overlapStart < overlapEnd) { // This item is part of the found text
      // For simplicity, we'll highlight the entire item if any part of it is in the match.
      // More precise sub-item highlighting is complex and might be a future enhancement.
      const transform = item.transform;
      const itemWidth = item.width;
      const itemHeight = item.height; // This is typically the font's bounding box height (ascent + descent)

      // tx and ty are the origin of the text item (usually baseline start) in PDF user space
      const tx = transform[4];
      const ty = transform[5];

      // Calculate bounding box in PDF user space (origin bottom-left, Y up)
      // item.height is often ascent+descent. ty is baseline.
      // A common approximation for bounding box:
      // y1 (bottom) = ty - descent (approx item.height * 0.2, but can vary greatly)
      // y2 (top)    = ty + ascent (approx item.height * 0.8)
      // For text highlighting, using ty as bottom and ty + itemHeight as top might be too high.
      // Let's assume ty is the bottom-left y of the text's visual box for now, and item.height is the height.
      // This might need adjustment based on how PDF.js renders and what looks good for highlights.
      const x1 = tx;
      const y1 = ty; // Assuming ty is bottom of the text line box for the item
      const x2 = tx + itemWidth;
      const y2 = ty + itemHeight; // Assuming item.height is the height of this text line box

      foundPdfRects.push({
        x1,
        y1,
        x2,
        y2,
        pageNumber,
      });
    }
    if (itemEndPageCharOffset >= matchEndIndex) break; // Optimization: stop if past the match
  }

  if (foundPdfRects.length === 0) {
    // This can happen if normalization causes issues or text is only whitespace
    console.warn(`Cited text "${normalizedSearchText}" produced no rects on page ${pageNumber} despite index match.`);
    return null;
  }

  // Calculate overall bounding box from the collected PdfRects
  const overallBoundingRect: PdfRect = foundPdfRects.reduce(
    (acc, rect) => {
      return {
        x1: Math.min(acc.x1, rect.x1),
        y1: Math.min(acc.y1, rect.y1),
        x2: Math.max(acc.x2, rect.x2),
        y2: Math.max(acc.y2, rect.y2),
        pageNumber,
      };
    },
    {
      x1: Infinity,
      y1: Infinity,
      x2: -Infinity,
      y2: -Infinity,
      pageNumber,
    }
  );

  return {
    boundingRect: overallBoundingRect,
    rects: foundPdfRects,
    pageNumber,
  };
}
