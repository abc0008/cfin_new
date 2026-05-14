import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MessageRenderer } from '../MessageRenderer';
import { Citation, Message } from '@/types';

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

describe('MessageRenderer citations', () => {
  test('renders inline citation markers as valid links and dispatches citation clicks', () => {
    const onCitationClick = jest.fn();
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

    render(<MessageRenderer message={message} onCitationClick={onCitationClick} />);

    const link = screen.getByRole('link', { name: /citation 1/i });
    expect(link).toHaveAttribute('href', '#citation-citation-total-loans-45000');

    fireEvent.click(link);

    expect(onCitationClick).toHaveBeenCalledWith(citation);
  });

  test('appends link markers when final content has citations but no inline markers', () => {
    const message: Message = {
      id: 'msg-2',
      sessionId: 'session-1',
      role: 'assistant',
      content: 'Total Loans Gross ended at 45000.',
      timestamp: new Date().toISOString(),
      referencedDocuments: ['doc-1'],
      referencedAnalyses: [],
      citations: [citation],
    };

    render(<MessageRenderer message={message} />);

    expect(screen.getByRole('link', { name: /citation 1/i })).toHaveAttribute(
      'href',
      '#citation-citation-total-loans-45000'
    );
  });
});
