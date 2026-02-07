import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FollowUpQuestions } from '../FollowUpQuestions';
import { conversationApi } from '@/lib/api/conversation';

jest.mock('@/lib/api/conversation', () => ({
  conversationApi: {
    generateFollowUpQuestions: jest.fn(),
  },
}));

describe('FollowUpQuestions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('dedupes duplicate StrictMode follow-up requests for same conversation/message seed', async () => {
    (conversationApi.generateFollowUpQuestions as jest.Mock).mockImplementation(
      async () => ['Question A?', 'Question B?', 'Question C?']
    );

    render(
      <React.StrictMode>
        <FollowUpQuestions
          conversationId="conv-1"
          seedKey="assistant-msg-1"
          onQuestionClick={jest.fn()}
        />
      </React.StrictMode>
    );

    await waitFor(() => {
      expect(screen.getByText('Question A?')).toBeInTheDocument();
    });

    expect(conversationApi.generateFollowUpQuestions).toHaveBeenCalledTimes(1);
    expect(conversationApi.generateFollowUpQuestions).toHaveBeenCalledWith('conv-1', 3);
  });

  test('allows a new follow-up fetch for a different message seed', async () => {
    (conversationApi.generateFollowUpQuestions as jest.Mock)
      .mockResolvedValueOnce(['Seed One'])
      .mockResolvedValueOnce(['Seed Two']);

    const { rerender } = render(
      <FollowUpQuestions
        key="assistant-msg-1"
        conversationId="conv-2"
        seedKey="assistant-msg-1"
        onQuestionClick={jest.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Seed One')).toBeInTheDocument();
    });

    rerender(
      <FollowUpQuestions
        key="assistant-msg-2"
        conversationId="conv-2"
        seedKey="assistant-msg-2"
        onQuestionClick={jest.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Seed Two')).toBeInTheDocument();
    });

    expect(conversationApi.generateFollowUpQuestions).toHaveBeenCalledTimes(2);
  });
});
