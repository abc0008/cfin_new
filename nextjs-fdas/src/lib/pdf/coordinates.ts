import type { LTWHP, Scaled } from '@/types'; // Assuming these are defined or re-exported in local types
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
