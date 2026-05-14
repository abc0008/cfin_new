import React from 'react';
import { render, screen } from '@testing-library/react';
import { MarkdownRenderer } from '../MarkdownRenderer';

jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children, components }: { children: string; components?: any }) => {
    const Paragraph = components?.p || 'p';
    return <Paragraph>{children}</Paragraph>;
  },
}));

jest.mock('react-syntax-highlighter', () => ({
  Prism: ({ children }: { children: React.ReactNode }) => <pre>{children}</pre>,
}));

jest.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({
  nord: {},
}));

jest.mock('remark-gfm', () => jest.fn());

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

describe('MarkdownRenderer', () => {
  test('does not duplicate rendered message text', () => {
    render(<MarkdownRenderer content="Plain duplicated sentence." />);

    expect(screen.getAllByText('Plain duplicated sentence.')).toHaveLength(1);
  });

  test('can render inline markdown without message-level copy actions', () => {
    render(
      <MarkdownRenderer
        content="Inline **value**"
        inline
        showMessageActions={false}
      />
    );

    expect(screen.getByText('Inline **value**')).toBeInTheDocument();
    expect(screen.queryByText('Copy message')).not.toBeInTheDocument();
  });
});
