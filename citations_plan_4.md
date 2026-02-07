<Summary_Plan_4>
<Summary>
Integrate Anthropic API citations with PDF highlighting
- Added type definitions for Anthropic API citations (ClaudeCitation) and augmented IHighlight to store raw citation data.
- Implemented `findTextPdfCoordinates` utility to locate text on a PDF page and return its coordinates in PDF user space.
- Modified `PDFViewer.tsx` to process `anthropicCitations` prop:
  - Uses `findTextPdfCoordinates` to get PDF coordinates for cited text.
  - Converts PDF coordinates to Scaled Coordinates suitable for `react-pdf-highlighter`.
  - Creates `IHighlight` objects from these citations and adds them to the displayed highlights.
  - Uses `renderScale` state for robust viewport acquisition during coordinate conversion.
- Updated `MessageRenderer.tsx` to parse assistant messages for citation markers (e.g., `[1]`) and render them as clickable elements that trigger an `onCitationClick` callback with the application's `Citation` object.
- The overall system now supports displaying Anthropic page-based citations as highlights in the PDF and allows users to click on citation markers in the chat to scroll to the corresponding highlight.
</Summary>

<Edit_1_MessageRenderer.tsx>
# Edit 1: MessageRenderer.tsx

nextjs-fdas/src/components/chat/MessageRenderer.tsx

Key edit: 
@@ -146,10 +146,90 @@ function MessageRendererBase({ message, onCitationClick }: MessageRendererProps)
```
   // Apply duplicate detection and removalAdd commentMore actions
  processedContent = detectDuplicateText(processedContent);

  // Helper function to parse content and embed clickable citations
  const renderContentWithCitations = (
    contentToRender: string,
    citations: Citation[] | undefined,
    handleCitationClick: ((citation: Citation) => void) | undefined
  ) => {
    if (!citations || citations.length === 0 || !handleCitationClick || !contentToRender) {
      // If no citations or no handler, or no content, render plain content (potentially markdown)
      // Using MarkdownRenderer for assistant messages if they might contain markdown.
      // If they are plain text, then simple div per line or direct text is fine.
      return <MarkdownRenderer content={contentToRender} />;
    }

    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    // Regex to find placeholders like [1], [2], etc.
    // Using string.replace with a callback function to build the parts array
    contentToRender.replace(/\[(\d+)\]/g, (match, p1, offset) => {
      const citationNumber = parseInt(p1, 10);
      const citationIndex = citationNumber - 1; // Citations are 1-indexed in text

      // Add text part before the current match
      if (offset > lastIndex) {
        parts.push(
          <MarkdownRenderer
            key={`text-${lastIndex}`}
            content={contentToRender.substring(lastIndex, offset)}
          />
        );
      }

      if (citations[citationIndex]) {
        const citation = citations[citationIndex];
        parts.push(
          <span
            key={`citation-${citation.id || citationIndex}`}
            className="text-primary hover:text-primary/80 underline cursor-pointer font-semibold mx-0.5 px-0.5 rounded-sm focus:outline-none focus:ring-2 focus:ring-primary"
            onClick={(e) => {
              e.stopPropagation(); // Prevent any parent onClick if MessageRenderer is part of a larger clickable area
              handleCitationClick(citation);
            }}
            role="button"
            tabIndex={0}
            onKeyPress={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.stopPropagation();
                handleCitationClick(citation);
              }
            }}
            aria-label={`Citation ${citationNumber}, Text: ${citation.text.substring(0, 30)}...`}
          >
            {`[${citationNumber}]`}
          </span>
        );
      } else {
        // If citation not found (e.g., malformed content), render the marker as text
        parts.push(match);
      }
      lastIndex = offset + match.length;
      return match; // Required by .replace(), not used for output array
    });

    // Add any remaining text after the last citation marker
    if (lastIndex < contentToRender.length) {
      parts.push(
        <MarkdownRenderer
          key={`text-${lastIndex}-end`}
          content={contentToRender.substring(lastIndex)}
        />
      );
    }

    // If no markers were found, parts will be empty, return original content via MarkdownRenderer
    if (parts.length === 0 && contentToRender) {
        return <MarkdownRenderer content={contentToRender} />;
    }

    return <>{parts}</>;
  };

  // For assistant messages, use whitespace-pre-wrap to preserve formatting
  return (
    <div className="message-content whitespace-pre-wrap">
      {processedContent}
      {renderContentWithCitations(processedContent, message.citations, onCitationClick)}
    </div>
  );
}

```
</Edit_1_MessageRenderer.tsx>

<Edit_2_citationService.ts>
Edit 2: citationService.ts
nextjs-fdas/src/lib/pdf/citationService.ts

Key edit: 

```

+1
Lines changed: 1 addition & 0 deletions
Original file line number	Diff line number	Diff line change
@@ -113,5 +113,6 @@ export const filterCitationsBySource = (
declare module 'react-pdf-highlighter' {
  interface IHighlight {
    isAICitation?: boolean;
    rawClaudeCitation?: import('@/types').ClaudeCitation; // Store original API citation for reference
  }
}
```
</Edit_2_citationService.ts>

<Edit_3_coordinates.ts>
Edit 3: coordinates.ts

nextjs-fdas/src/lib/pdf/coordinates.ts

Key edit: 
@@ -0,0 +1,34 @@
```
import type { LTWHP, Scaled } from '@/types'; // Assuming these are defined or re-exported in local typesAdd commentMore actions
                                         // Or import directly from 'react-pdf-highlighter' if path is known e.g. 'react-pdf-highlighter/dist/types'

// Copied from react-pdf-highlighter/src/lib/coordinates.ts
// "viewport" rectangle is { top, left, width, height }

// "scaled" means that data structure stores (0, 1) coordinates.
// for clarity reasons I decided not to store actual (0, 1) coordinates, but
// provide width and height, so user can compute ratio himself if needed

interface ViewportDimensions {
  width: number;
  height: number;
}

export const viewportToScaled = (
  rect: LTWHP, // Viewport coordinates like { left, top, width, height, pageNumber? }
  { width, height }: ViewportDimensions, // Viewport dimensions
): Scaled => { // Scaled is { x1, y1, x2, y2, width (viewport), height (viewport), pageNumber? }
  return {
    x1: rect.left,
    y1: rect.top,
    x2: rect.left + rect.width,
    y2: rect.top + rect.height,
    width, // Viewport width at the time of scaling
    height, // Viewport height at the time of scaling
    pageNumber: rect.pageNumber,
  };
};

// We might also need scaledToViewport if we ever go the other way,
// but for now, viewportToScaled is the primary one.
// The react-pdf-highlighter library also has pdfToViewport and scaledToViewport (which uses usePdfCoordinates flag)
// For now, this minimal copy should suffice for the current step.
```
</Edit_3_coordinates.ts>

<Edit_4_textSearch.ts>
Edit 4: textSearch

nextjs-fdas/src/lib/pdf/textSearch.ts

Key edit: 
@@ -0,0 +1,164 @@

```
// Using 'any' for PDFJSPage and PDFJSTextContentItem as direct import might be complexAdd commentMore actions
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
```
</Edit_4_textSearch.ts>
</Summary_Plan_4>