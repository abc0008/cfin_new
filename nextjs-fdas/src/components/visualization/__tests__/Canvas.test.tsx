import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import Canvas from '../Canvas';

jest.mock('../../charts/ChartRenderer', () => {
  return function MockChartRenderer({ data }: any) {
    return <div data-testid="chart-renderer">{data.config.title}</div>;
  };
});

jest.mock('../../tables/TableRenderer', () => {
  return function MockTableRenderer({ data }: any) {
    return <div data-testid="table-renderer">{data.config.title}</div>;
  };
});

const chartBlock = {
  block_type: 'chart',
  title: 'Revenue Chart',
  content: {
    chartType: 'bar',
    config: {
      title: 'Revenue Chart',
      xAxisKey: 'metric',
    },
    chartConfig: {
      value: { label: 'Value' },
    },
    data: [{ metric: 'Revenue', value: 10 }],
  },
};

const tableBlock = {
  block_type: 'table',
  title: 'Financial Table',
  content: {
    tableType: 'simple',
    config: {
      title: 'Financial Table',
      columns: [{ key: 'metric', label: 'Metric' }],
      pagination: false,
    },
    data: [{ metric: 'Revenue' }],
  },
};

const messages = [
  {
    id: 'assistant-with-visuals',
    role: 'assistant',
    content: '',
    timestamp: new Date().toISOString(),
    referencedDocuments: [],
    referencedAnalyses: [],
    analysis_blocks: [chartBlock, tableBlock],
  },
];

describe('Canvas', () => {
  test('renders charts and tables from assistant analysis blocks', () => {
    render(<Canvas analysisResults={[]} messages={messages} />);

    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Charts (1)' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Tables (1)' })).toBeInTheDocument();
    expect(screen.getByTestId('chart-renderer')).toHaveTextContent('Revenue Chart');
    expect(screen.getByTestId('table-renderer')).toHaveTextContent('Financial Table');
  });

  test('switches between chart and table tabs', () => {
    render(<Canvas analysisResults={[]} messages={messages} />);

    fireEvent.click(screen.getByRole('tab', { name: 'Tables (1)' }));

    expect(screen.getByRole('tab', { name: 'Tables (1)' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByTestId('table-renderer')).toHaveTextContent('Financial Table');
    expect(screen.queryByTestId('chart-renderer')).not.toBeInTheDocument();
  });

  test('keeps existing visualizations visible when the latest analysis has an error', () => {
    render(
      <Canvas
        analysisResults={[]}
        messages={messages}
        error="Invalid API key"
      />
    );

    expect(screen.getByRole('alert')).toHaveTextContent('Latest analysis failed: Invalid API key');
    expect(screen.getByTestId('chart-renderer')).toHaveTextContent('Revenue Chart');
    expect(screen.getByTestId('table-renderer')).toHaveTextContent('Financial Table');
  });

  test('renders a full error state when no visualization data exists', () => {
    render(<Canvas analysisResults={[]} messages={[]} error="Invalid API key" />);

    expect(screen.getByRole('alert')).toHaveTextContent('Invalid API key');
    expect(screen.queryByTestId('chart-renderer')).not.toBeInTheDocument();
  });
});
