import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import { CitationEnabledPDFViewer } from '../CitationEnabledPDFViewer';
import { Citation } from '@/types/citation';
import { ProcessedDocument } from '@/types';

jest.mock('../PDFViewer', () => ({
  PDFViewer: (props: any) => (
    <div
      data-testid="pdf-viewer-proxy"
      data-highlight-id={props.highlightId || ''}
      data-extra-citations={props.extraCitations?.length || 0}
    />
  ),
}));

jest.mock('@/context/CitationContext', () => ({
  useCitation: () => ({
    openCitation: jest.fn().mockResolvedValue(undefined),
  }),
}));

jest.mock('@/hooks/useCitationPrefetch', () => ({
  useCitationPrefetch: () => ({
    prefetchedPages: new Set<number>(),
  }),
}));

jest.mock('@/hooks/usePerformanceMonitor', () => ({
  usePerformanceMonitor: () => ({
    measureCitationLoad: async (_id: string, fn: () => Promise<void>) => fn(),
    startTimer: jest.fn(),
    endTimer: jest.fn().mockReturnValue(0),
  }),
}));

const mockDocument: ProcessedDocument = {
  metadata: {
    id: 'doc-evt-1',
    filename: 'event-test.pdf',
    uploadTimestamp: new Date().toISOString(),
    fileSize: 1000,
    mimeType: 'application/pdf',
    userId: 'user-1',
  },
  contentType: 'other',
  extractionTimestamp: new Date().toISOString(),
  periods: [],
  extractedData: {},
  confidenceScore: 1,
  processingStatus: 'completed',
  citations: [],
};

describe('CitationEnabledPDFViewer', () => {
  beforeEach(() => {
    if (!(window as any).requestAnimationFrame) {
      (window as any).requestAnimationFrame = (cb: FrameRequestCallback) =>
        setTimeout(cb, 0);
    }
  });

  test('handles citation-navigation event by forwarding highlightId and extra citations', async () => {
    render(
      <CitationEnabledPDFViewer
        document={mockDocument}
        pdfUrl="http://localhost/mock.pdf"
      />
    );

    const citation: Citation = {
      id: 'cite-event-1',
      highlightId: 'cite-event-1',
      documentId: 'doc-evt-1',
      documentTitle: 'Event Doc',
      type: 'page_location',
      citedText: 'Net income',
      rects: [],
      startPageNumber: 2,
      endPageNumber: 2,
    };

    await act(async () => {
      window.dispatchEvent(
        new CustomEvent('citation-navigation', {
          detail: {
            citation,
            documentUrl: 'http://localhost/mock.pdf',
          },
        })
      );
    });

    await waitFor(() => {
      const proxy = screen.getByTestId('pdf-viewer-proxy');
      expect(proxy).toHaveAttribute('data-highlight-id', 'cite-event-1');
      expect(proxy).toHaveAttribute('data-extra-citations', '1');
    });
  });
});
