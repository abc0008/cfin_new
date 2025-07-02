export interface PdfRect {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  pageNumber: number;
}

export interface TextItemWithOffset {
  item: any; // PDFTextItem from pdfjs
  itemIndex: number;
  pageCharOffset: number;
}

export interface TextSearchResult {
  boundingRect: PdfRect;
  rects: PdfRect[];
  pageNumber: number;
}

export async function findTextPdfCoordinates(
  page: any, // PDFPageProxy
  searchText: string
): Promise<TextSearchResult | null> {
  if (!searchText?.trim()) return null;

  const textContent = await page.getTextContent();
  if (!textContent?.items?.length) return null;

  const pageNumber = page.pageNumber;
  let fullPageText = "";
  const itemsWithOffsets: TextItemWithOffset[] = [];

  // Build full page text and track item positions
  textContent.items.forEach((item: any, index: number) => {
    itemsWithOffsets.push({
      item,
      itemIndex: index,
      pageCharOffset: fullPageText.length
    });
    fullPageText += item.str;
    if (item.hasEOL) fullPageText += "\n";
  });

  // Normalize and search
  const normalizedPageText = fullPageText.replace(/\s+/g, " ").trim();
  const normalizedSearchText = searchText.replace(/\s+/g, " ").trim();
  
  const matchIndex = normalizedPageText.toLowerCase().indexOf(normalizedSearchText.toLowerCase());
  if (matchIndex === -1) return null;

  // Find items that contain the match
  const matchEnd = matchIndex + normalizedSearchText.length;
  const foundRects: PdfRect[] = [];

  // Map normalized position back to original text position
  let normalizedPos = 0;
  let originalPos = 0;
  const normalizedToOriginal = new Map<number, number>();

  for (let i = 0; i < fullPageText.length; i++) {
    if (/\s/.test(fullPageText[i])) {
      // Skip consecutive whitespace in normalized version
      if (i === 0 || !/\s/.test(fullPageText[i - 1])) {
        normalizedToOriginal.set(normalizedPos, i);
        normalizedPos++;
      }
    } else {
      normalizedToOriginal.set(normalizedPos, i);
      normalizedPos++;
    }
  }

  // Get original text positions for the match
  const origMatchStart = normalizedToOriginal.get(matchIndex) || 0;
  const origMatchEnd = normalizedToOriginal.get(matchEnd - 1) || fullPageText.length;

  for (const { item, pageCharOffset } of itemsWithOffsets) {
    const itemStart = pageCharOffset;
    const itemEnd = itemStart + item.str.length;
    
    // Check overlap with match
    if (itemEnd > origMatchStart && itemStart <= origMatchEnd) {
      const transform = item.transform;
      const x1 = transform[4];
      const y1 = transform[5];
      const x2 = x1 + item.width;
      const y2 = y1 + item.height;
      
      foundRects.push({ x1, y1, x2, y2, pageNumber });
    }
  }

  if (foundRects.length === 0) return null;

  // Calculate overall bounding box
  const boundingRect = foundRects.reduce((acc, rect) => ({
    x1: Math.min(acc.x1, rect.x1),
    y1: Math.min(acc.y1, rect.y1),
    x2: Math.max(acc.x2, rect.x2),
    y2: Math.max(acc.y2, rect.y2),
    pageNumber
  }), {
    x1: Infinity,
    y1: Infinity,
    x2: -Infinity,
    y2: -Infinity,
    pageNumber
  });

  return { boundingRect, rects: foundRects, pageNumber };
}

export async function searchMultiplePages(
  pdfDocument: any, // PDFDocumentProxy
  searchText: string,
  startPage: number = 1,
  endPage?: number
): Promise<TextSearchResult[]> {
  const results: TextSearchResult[] = [];
  const numPages = pdfDocument.numPages;
  const lastPage = endPage ? Math.min(endPage, numPages) : numPages;

  for (let pageNum = startPage; pageNum <= lastPage; pageNum++) {
    try {
      const page = await pdfDocument.getPage(pageNum);
      const result = await findTextPdfCoordinates(page, searchText);
      if (result) {
        results.push(result);
      }
    } catch (error) {
      console.error(`Error searching page ${pageNum}:`, error);
    }
  }

  return results;
}

export function mergeAdjacentRects(rects: PdfRect[], threshold: number = 5): PdfRect[] {
  if (rects.length <= 1) return rects;

  // Sort rects by position (top to bottom, left to right)
  const sorted = [...rects].sort((a, b) => {
    if (Math.abs(a.y1 - b.y1) < threshold) {
      return a.x1 - b.x1;
    }
    return a.y1 - b.y1;
  });

  const merged: PdfRect[] = [];
  let current = { ...sorted[0] };

  for (let i = 1; i < sorted.length; i++) {
    const rect = sorted[i];
    
    // Check if rects are on the same line and adjacent
    if (Math.abs(rect.y1 - current.y1) < threshold &&
        rect.x1 - current.x2 < threshold) {
      // Merge horizontally
      current.x2 = Math.max(current.x2, rect.x2);
      current.y2 = Math.max(current.y2, rect.y2);
    } else {
      // Start new rect
      merged.push(current);
      current = { ...rect };
    }
  }
  
  merged.push(current);
  return merged;
}