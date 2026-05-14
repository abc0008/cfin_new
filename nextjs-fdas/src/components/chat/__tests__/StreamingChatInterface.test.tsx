import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { StreamingChatInterface } from '../StreamingChatInterface';
import { Citation, Message } from '@/types';

const mockOpenCitation = jest.fn().mockResolvedValue(undefined);

jest.mock('@/context/CitationContext', () => ({
  useCitation: () => ({
    openCitation: mockOpenCitation,
  }),
}));

jest.mock('@/hooks/useStreamingChatWithCitations', () => ({
  useStreamingChatWithCitations: () => ({
    isConnected: false,
    isStreaming: false,
    streamingText: '',
    streamingMessageId: null,
    toolsInProgress: [],
    completedVisualizations: [],
    streamingCitations: [],
    sendStreamingMessage: jest.fn(),
    sendStreamingMessageHTTP: jest.fn(),
  }),
}));

jest.mock('../FollowUpQuestions', () => ({
  FollowUpQuestions: () => null,
}));

jest.mock('../MarkdownRenderer', () => ({
  MarkdownRenderer: ({ content }: { content: string }) => <span>{content}</span>,
}));

const citation: Citation = {
  id: 'citation-total-loans-45000',
  highlightId: 'citation-total-loans-45000',
  documentId: 'doc-1',
  documentTitle: 'Bank Report',
  type: 'page_location',
  citedText: '45000',
  displayText: 'Total Loans Gross 2025Q1: 45000',
  rects: [
    {
      x1: 709,
      y1: 208,
      x2: 735,
      y2: 222,
      width: 26,
      height: 14,
      pageNumber: 1,
    },
  ],
  startPageNumber: 1,
  endPageNumber: 1,
};

const message: Message = {
  id: 'msg-1',
  sessionId: 'session-1',
  role: 'assistant',
  content: 'Total Loans Gross ended at 45000 [1].',
  timestamp: new Date().toISOString(),
  referencedDocuments: ['doc-1'],
  referencedAnalyses: [],
  citations: [citation],
};

describe('StreamingChatInterface citation navigation', () => {
  const originalScrollIntoView = HTMLElement.prototype.scrollIntoView;

  beforeEach(() => {
    mockOpenCitation.mockClear();
    HTMLElement.prototype.scrollIntoView = jest.fn();
  });

  afterEach(() => {
    HTMLElement.prototype.scrollIntoView = originalScrollIntoView;
  });

  test('live streamed citation links route the workspace and load citation rect data', () => {
    const onNavigateToHighlight = jest.fn();

    render(
      <StreamingChatInterface
        messages={[message]}
        onSendMessage={jest.fn().mockResolvedValue(undefined)}
        activeDocuments={['doc-1']}
        conversationId="session-1"
        onNavigateToHighlight={onNavigateToHighlight}
      />
    );

    fireEvent.click(screen.getByRole('link', { name: /citation 1/i }));

    expect(onNavigateToHighlight).toHaveBeenCalledWith(citation);
    expect(mockOpenCitation).toHaveBeenCalledWith(citation.id);
  });
});
