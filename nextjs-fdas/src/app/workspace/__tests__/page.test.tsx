import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Workspace from '../page';

jest.mock('next/dynamic', () => {
  return (importer: any) => {
    const React = require('react');
    return function DynamicMock(props: any) {
      const [Comp, setComp] = React.useState<any>(null);
      React.useEffect(() => {
        Promise.resolve(importer()).then((mod: any) => setComp(() => mod.default || mod.CitationEnabledPDFViewer || mod));
      }, []);
      if (!Comp) return <div data-testid="pdf-viewer-loading" />;
      return <Comp {...props} />;
    };
  };
});

jest.mock('@/context/CitationContext', () => ({
  useCitation: () => ({
    citations: new Map(),
    addCitations: jest.fn(),
    openCitation: jest.fn(),
  }),
}));

jest.mock('@/lib/api/conversation', () => ({
  conversationApi: {
    createConversation: jest.fn().mockResolvedValue({ id: 'sess-1' }),
    sendMessage: jest.fn().mockResolvedValue({ content: 'ok' }),
  },
}));

jest.mock('@/lib/api/analysis', () => ({
  analysisApi: {
    runBasicFinancialAnalysis: jest.fn().mockResolvedValue({
      id: 'analysis-1',
      documentIds: ['doc-1'],
      analysisType: 'basic_financial',
      timestamp: new Date().toISOString(),
      metrics: [],
      visualizationData: { charts: [], tables: [] },
      analysisText: 'summary',
    }),
    runAnalysis: jest.fn().mockResolvedValue({}),
  },
}));

jest.mock('@/components/analysis/AnalysisControls', () => ({
  AnalysisControls: () => <div data-testid="analysis-controls" />,
}));

jest.mock('@/components/visualization/Canvas', () => () => <div data-testid="canvas" />);

jest.mock('../../../components/document/UploadForm', () => ({
  UploadForm: ({ onUploadSuccess }: any) => (
    <button
      type="button"
      onClick={() =>
        onUploadSuccess({
          metadata: {
            id: 'doc-1',
            filename: 'test.pdf',
            uploadTimestamp: new Date().toISOString(),
            fileSize: 100,
            mimeType: 'application/pdf',
            userId: 'u1',
          },
          contentType: 'other',
          extractionTimestamp: new Date().toISOString(),
          periods: [],
          extractedData: {},
          confidenceScore: 1,
          processingStatus: 'completed',
          citations: [],
        })
      }
    >
      Complete Upload
    </button>
  ),
}));

jest.mock('../../../components/chat/StreamingChatInterface', () => ({
  StreamingChatInterface: ({ onNavigateToHighlight }: any) => (
    <button
      type="button"
      onClick={() =>
        onNavigateToHighlight({
          id: 'citation-id-1',
          highlightId: 'highlight-id-1',
          documentId: 'doc-1',
          startPageNumber: 2,
        })
      }
    >
      Trigger Citation Click
    </button>
  ),
}));

jest.mock('../../../components/document/CitationEnabledPDFViewer', () => ({
  CitationEnabledPDFViewer: ({ highlightId, document }: any) => (
    <div data-testid="pdf-viewer" data-highlight-id={highlightId || ''} data-doc-id={document?.metadata?.id || ''} />
  ),
}));

describe('Workspace citation navigation', () => {
  test('clicking a chat citation routes to PDF viewer highlight id', async () => {
    render(<Workspace />);

    fireEvent.click(screen.getByRole('button', { name: /upload document/i }));
    fireEvent.click(screen.getByRole('button', { name: /complete upload/i }));

    await waitFor(() => {
      expect(screen.getByTestId('pdf-viewer')).toHaveAttribute('data-doc-id', 'doc-1');
    });

    fireEvent.click(screen.getByRole('button', { name: /trigger citation click/i }));

    await waitFor(() => {
      expect(screen.getByTestId('pdf-viewer')).toHaveAttribute('data-highlight-id', 'highlight-id-1');
    });
  });
});
