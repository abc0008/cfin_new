// Define types if not exported from react-pdf-highlighter
export interface LTWHP {
  left: number;
  top: number;
  width: number;
  height: number;
  pageNumber: number;
}

export interface Scaled {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  width: number;
  height: number;
  pageNumber: number;
}

interface ViewportDimensions {
  width: number;
  height: number;
}

export const viewportToScaled = (
  rect: LTWHP,
  viewport: ViewportDimensions
): Scaled => {
  return {
    x1: rect.left / viewport.width,
    y1: rect.top / viewport.height,
    x2: (rect.left + rect.width) / viewport.width,
    y2: (rect.top + rect.height) / viewport.height,
    width: viewport.width,
    height: viewport.height,
    pageNumber: rect.pageNumber
  };
};

export const pdfToViewport = (
  pdfRect: { x1: number; y1: number; x2: number; y2: number },
  viewport: any // PDFPageViewport from pdfjs
): LTWHP => {
  const [x1, y1] = viewport.convertToViewportPoint(pdfRect.x1, pdfRect.y1);
  const [x2, y2] = viewport.convertToViewportPoint(pdfRect.x2, pdfRect.y2);
  
  return {
    left: Math.min(x1, x2),
    top: Math.min(y1, y2),
    width: Math.abs(x2 - x1),
    height: Math.abs(y2 - y1),
    pageNumber: viewport.pageNumber
  };
};

export const scaledToViewport = (
  scaled: Scaled,
  viewport: ViewportDimensions
): LTWHP => {
  return {
    left: scaled.x1 * viewport.width,
    top: scaled.y1 * viewport.height,
    width: (scaled.x2 - scaled.x1) * viewport.width,
    height: (scaled.y2 - scaled.y1) * viewport.height,
    pageNumber: scaled.pageNumber
  };
};

export const citationRectToScaled = (
  rect: { x1: number; y1: number; x2: number; y2: number; pageNumber: number },
  viewport: ViewportDimensions
): Scaled => {
  return {
    x1: rect.x1 / viewport.width,
    y1: rect.y1 / viewport.height,
    x2: rect.x2 / viewport.width,
    y2: rect.y2 / viewport.height,
    width: viewport.width,
    height: viewport.height,
    pageNumber: rect.pageNumber
  };
};