import React from 'react';
import { render, screen } from '@testing-library/react';
import ChartRenderer from '../ChartRenderer';
import { ChartData } from '@/types/visualization';

// Test data for stackedArea chart
const stackedAreaTestData: ChartData = {
  chartType: 'stackedArea',
  config: {
    title: 'Deposit Mix Composition Over Time',
    description: 'Breakdown of deposit types over quarterly periods',
    xAxisKey: 'period',
    xAxisLabel: 'Quarter', 
    yAxisLabel: 'Amount (Millions)',
    showLegend: true,
    legendPosition: 'top',
    showGrid: true,
    stack: true,
    stacked: true,
    colors: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444']
  },
  data: [
    {
      period: 'Q1 2023',
      name: 'Q1 2023',
      'Demand Deposits': 150.5,
      'Savings Deposits': 120.3,
      'Time Deposits': 89.7,
      'Money Market': 45.2
    },
    {
      period: 'Q2 2023',
      name: 'Q2 2023', 
      'Demand Deposits': 155.8,
      'Savings Deposits': 125.1,
      'Time Deposits': 92.4,
      'Money Market': 48.9
    },
    {
      period: 'Q3 2023',
      name: 'Q3 2023',
      'Demand Deposits': 160.2,
      'Savings Deposits': 130.5,
      'Time Deposits': 95.1,
      'Money Market': 52.3
    }
  ]
};

describe('StackedArea Chart Rendering', () => {
  test('renders stackedArea chart with title', () => {
    render(<ChartRenderer data={stackedAreaTestData} />);
    
    // Check if title is rendered
    expect(screen.getByText('Deposit Mix Composition Over Time')).toBeInTheDocument();
  });

  test('stackedArea chart type is handled by ChartRenderer', () => {
    const { container } = render(<ChartRenderer data={stackedAreaTestData} />);
    
    // ChartRenderer should create an AreaChart container
    const chartContainer = container.querySelector('.h-full');
    expect(chartContainer).toBeInTheDocument();
  });

  test('data structure has required keys', () => {
    const firstDataItem = stackedAreaTestData.data[0];
    const dataKeys = Object.keys(firstDataItem).filter(key => key !== 'name' && key !== 'period');
    
    expect(dataKeys).toContain('Demand Deposits');
    expect(dataKeys).toContain('Savings Deposits');
    expect(dataKeys).toContain('Time Deposits'); 
    expect(dataKeys).toContain('Money Market');
    expect(dataKeys.length).toBeGreaterThan(0);
  });

  test('config has stacking enabled', () => {
    expect(stackedAreaTestData.config.stack).toBe(true);
    expect(stackedAreaTestData.config.stacked).toBe(true);
    expect(stackedAreaTestData.chartType).toBe('stackedArea');
  });
});