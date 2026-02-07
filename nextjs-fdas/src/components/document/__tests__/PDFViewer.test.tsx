import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import { PDFViewer } from '../PDFViewer';
import { Citation, ProcessedDocument } from '@/types';

jest.mock('@/lib/api/documents', () => {
  const getDocumentCitations = jest.fn().mockResolvedValue([]);
  return {
    documentsApi: {
      getDocumentUrl: jest.fn().mockResolvedValue('blob:mock-pdf'),
      getDocumentCitations,
    },
    cleanupBlobUrls: jest.fn(),
  };
});

jest.mock('react-pdf-highlighter', () => {
  const React = require('react');
  const scrollToMock = jest.fn();
  const hiddenHighlightIds = new Set<string>();
  const mockPdfDocument = {
    numPages: 10,
    cleanup: jest.fn(),
    destroy: jest.fn(),
  };

  return {
    PdfLoader: ({ children }: any) => (
      <div data-testid="pdf-loader">{children(mockPdfDocument)}</div>
    ),
    PdfHighlighter: ({ scrollRef, highlights, onScrollChange }: any) => {
      const pageRef = React.useRef<HTMLDivElement | null>(null);
      const firstPageNumber = highlights?.[0]?.position?.pageNumber || 1;

      React.useEffect(() => {
        scrollRef(scrollToMock);
      }, [scrollRef]);

      React.useEffect(() => {
        if (typeof onScrollChange === 'function') {
          onScrollChange(undefined);
        }
      }, [onScrollChange]);

      React.useEffect(() => {
        if (pageRef.current) {
          Object.defineProperty(pageRef.current, 'offsetParent', {
            configurable: true,
            get: () => globalThis.document?.body || null,
          });
        }
      }, [firstPageNumber]);

      return (
        <div
          className="PdfHighlighter"
          data-testid="pdf-highlighter"
          data-highlight-count={highlights?.length || 0}
        >
          <div
            ref={pageRef}
            className="page"
            data-page-number={String(firstPageNumber)}
          />
          {(highlights || []).map((highlight: any) => {
            if (hiddenHighlightIds.has(highlight.id)) {
              return <div key={highlight.id} data-hidden-highlight-id={highlight.id} />;
            }
            return (
              <div
                key={highlight.id}
                data-highlight-id={highlight.id}
              >
                <div
                  className="Highlight__part"
                  data-highlight-part-id={`part-${highlight.id}`}
                  ref={(node) => {
                    if (node) {
                      node.getBoundingClientRect = () =>
                        ({
                          x: 100,
                          y: 120,
                          top: 120,
                          left: 100,
                          right: 180,
                          bottom: 136,
                          width: 80,
                          height: 16,
                          toJSON: () => ({}),
                        } as DOMRect);
                    }
                  }}
                />
              </div>
            );
          })}
        </div>
      );
    },
    Highlight: ({ children }: any) => <div>{children}</div>,
    Popup: ({ children }: any) => <div>{children}</div>,
    AreaHighlight: ({ children }: any) => <div>{children}</div>,
    __scrollToMock: scrollToMock,
    __setHiddenHighlightIds: (ids: string[]) => {
      hiddenHighlightIds.clear();
      ids.forEach((id) => hiddenHighlightIds.add(id));
    },
    __clearHiddenHighlightIds: () => hiddenHighlightIds.clear(),
  };
});

const mockDocument: ProcessedDocument = {
  metadata: {
    id: 'doc-1',
    filename: 'sample.pdf',
    uploadTimestamp: new Date().toISOString(),
    fileSize: 1000,
    mimeType: 'application/pdf',
    userId: 'user-1',
  },
  contentType: 'other',
  extractionTimestamp: new Date().toISOString(),
  periods: [],
  extractedData: {},
  confidenceScore: 0.9,
  processingStatus: 'completed',
  citations: [],
};

const makeCitation = (overrides: Partial<Citation> = {}): Citation => ({
  id: 'backend-citation-1',
  highlightId: 'backend-citation-1',
  documentId: 'doc-1',
  documentTitle: 'Sample Doc',
  type: 'page_location',
  citedText: 'Revenue',
  rects: [
    {
      x1: 100,
      y1: 140,
      x2: 220,
      y2: 160,
      width: 120,
      height: 20,
      pageNumber: 3,
    },
  ],
  startPageNumber: 3,
  endPageNumber: 3,
  ...overrides,
});

describe('PDFViewer citation navigation', () => {
  const originalScrollIntoView = HTMLElement.prototype.scrollIntoView;

  beforeEach(() => {
    const highlighter = require('react-pdf-highlighter');
    highlighter.__scrollToMock.mockReset();
    highlighter.__clearHiddenHighlightIds();
    (window as any).citationTempToBackendMap = undefined;
    HTMLElement.prototype.scrollIntoView = jest.fn();
  });

  afterEach(() => {
    jest.useRealTimers();
    HTMLElement.prototype.scrollIntoView = originalScrollIntoView;
    globalThis.document
      .querySelectorAll('[data-highlight-part-id^="stale-"]')
      .forEach((node) => node.parentElement?.remove());
  });

  test('scrolls to highlight when citation id exists in highlights', async () => {
    const citation = makeCitation();

    render(
      <PDFViewer
        document={mockDocument}
        pdfUrl="http://localhost/mock.pdf"
        extraCitations={[citation]}
        highlightId={citation.id}
      />
    );

    const highlighter = require('react-pdf-highlighter');

    await waitFor(() => {
      const helperCalls = highlighter.__scrollToMock.mock.calls.length;
      const domCalls = (HTMLElement.prototype.scrollIntoView as jest.Mock).mock.calls.length;
      expect(helperCalls + domCalls).toBeGreaterThan(0);
    });

    const renderedHighlight = screen
      .getByTestId('pdf-highlighter')
      .querySelector(`[data-highlight-id="${citation.id}"]`);
    expect(renderedHighlight).not.toBeNull();

    if (highlighter.__scrollToMock.mock.calls.length > 0) {
      const highlightArg = highlighter.__scrollToMock.mock.calls[0][0];
      expect(highlightArg.id).toBe(citation.id);
      expect(highlightArg.position.pageNumber).toBe(3);
    }
  });

  test('handles undefined visible-pages callback payload without throwing', async () => {
    render(
      <PDFViewer
        document={mockDocument}
        pdfUrl="http://localhost/mock.pdf"
      />
    );

    expect(screen.getByText('Loading document citations...')).toBeInTheDocument();
  });

  test('resolves temp citation ids using temp-to-backend mapping before scrolling', async () => {
    const backendCitation = makeCitation({
      id: 'backend-citation-xyz',
      highlightId: 'backend-citation-xyz',
    });

    (window as any).citationTempToBackendMap = new Map<string, string>([
      ['cite-temp-123', 'backend-citation-xyz'],
    ]);

    render(
      <PDFViewer
        document={mockDocument}
        pdfUrl="http://localhost/mock.pdf"
        extraCitations={[backendCitation]}
        highlightId="cite-temp-123"
      />
    );

    const highlighter = require('react-pdf-highlighter');

    await waitFor(() => {
      const helperCalls = highlighter.__scrollToMock.mock.calls.length;
      const domCalls = (HTMLElement.prototype.scrollIntoView as jest.Mock).mock.calls.length;
      expect(helperCalls + domCalls).toBeGreaterThan(0);
    });

    const renderedHighlight = screen
      .getByTestId('pdf-highlighter')
      .querySelector('[data-highlight-id="backend-citation-xyz"]');
    expect(renderedHighlight).not.toBeNull();

    if (highlighter.__scrollToMock.mock.calls.length > 0) {
      const highlightArg = highlighter.__scrollToMock.mock.calls[0][0];
      expect(highlightArg.id).toBe('backend-citation-xyz');
    }
  });

  test('falls back to DOM page scroll when helper throws', async () => {
    const citation = makeCitation();
    const highlighter = require('react-pdf-highlighter');
    highlighter.__scrollToMock.mockImplementationOnce(() => {
      throw new Error('offsetParent is not set -- cannot scroll');
    });

    render(
      <PDFViewer
        document={mockDocument}
        pdfUrl="http://localhost/mock.pdf"
        extraCitations={[citation]}
        highlightId={citation.id}
      />
    );

    await waitFor(() => {
      expect(HTMLElement.prototype.scrollIntoView).toHaveBeenCalled();
    });
  });

  test('kicks page scroll once while waiting for highlight rect DOM', async () => {
    jest.useFakeTimers();
    const citation = makeCitation({
      id: 'pending-rect-dom',
      highlightId: 'pending-rect-dom',
    });
    const highlighter = require('react-pdf-highlighter');
    highlighter.__setHiddenHighlightIds(['pending-rect-dom']);

    render(
      <PDFViewer
        document={mockDocument}
        pdfUrl="http://localhost/mock.pdf"
        extraCitations={[citation]}
        highlightId={citation.id}
      />
    );

    await waitFor(() => {
      expect(highlighter.__scrollToMock).toHaveBeenCalledTimes(1);
    });

    const initialHelperCalls = highlighter.__scrollToMock.mock.calls.length;
    const initialDomCalls = (HTMLElement.prototype.scrollIntoView as jest.Mock).mock.calls.length;

    await act(async () => {
      jest.advanceTimersByTime(3000);
    });

    expect(highlighter.__scrollToMock).toHaveBeenCalledTimes(initialHelperCalls);
    expect(HTMLElement.prototype.scrollIntoView).toHaveBeenCalledTimes(initialDomCalls);
  });

  test('prefers visible rendered rect when stale duplicate highlight id exists', async () => {
    const citation = makeCitation();

    const staleWrapper = globalThis.document.createElement('div');
    staleWrapper.setAttribute('data-highlight-id', citation.id);
    const stalePart = globalThis.document.createElement('div');
    stalePart.className = 'Highlight__part';
    stalePart.setAttribute('data-highlight-part-id', `stale-${citation.id}`);
    stalePart.getBoundingClientRect = () =>
      ({
        x: 10,
        y: -980,
        top: -980,
        left: 10,
        right: 40,
        bottom: -960,
        width: 30,
        height: 20,
        toJSON: () => ({}),
      } as DOMRect);
    staleWrapper.appendChild(stalePart);
    globalThis.document.body.prepend(staleWrapper);

    render(
      <PDFViewer
        document={mockDocument}
        pdfUrl="http://localhost/mock.pdf"
        extraCitations={[citation]}
        highlightId={citation.id}
      />
    );

    await waitFor(() => {
      const highlighter = require('react-pdf-highlighter');
      const helperCalls = highlighter.__scrollToMock.mock.calls.length;
      const domCalls = (HTMLElement.prototype.scrollIntoView as jest.Mock).mock.calls.length;
      expect(helperCalls + domCalls).toBeGreaterThan(0);

      const instances = (HTMLElement.prototype.scrollIntoView as jest.Mock).mock.instances as HTMLElement[];
      expect(
        instances.some((el) => el?.getAttribute?.('data-highlight-part-id') === `stale-${citation.id}`)
      ).toBe(false);
    });
  });
});
