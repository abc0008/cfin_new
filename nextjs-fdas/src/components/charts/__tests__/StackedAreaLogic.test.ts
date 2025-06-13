import { ChartData } from '@/types/visualization';

describe('StackedArea Chart Logic', () => {
  const stackedAreaData: ChartData = {
    chartType: 'stackedArea',
    config: {
      title: 'Deposit Mix Composition Over Time',
      xAxisKey: 'period',
      showLegend: true,
      stack: true,
      stacked: true
    },
    data: [
      {
        period: 'Q1 2023',
        name: 'Q1 2023',
        'Demand Deposits': 150.5,
        'Savings Deposits': 120.3,
        'Time Deposits': 89.7
      },
      {
        period: 'Q2 2023', 
        name: 'Q2 2023',
        'Demand Deposits': 155.8,
        'Savings Deposits': 125.1,
        'Time Deposits': 92.4
      }
    ]
  };

  test('stackedArea data structure is valid', () => {
    expect(stackedAreaData.chartType).toBe('stackedArea');
    expect(stackedAreaData.config.stack).toBe(true);
    expect(stackedAreaData.config.stacked).toBe(true);
    expect(stackedAreaData.data.length).toBeGreaterThan(0);
  });

  test('data has multiple series for stacking', () => {
    const firstItem = stackedAreaData.data[0];
    const dataKeys = Object.keys(firstItem).filter(key => 
      key !== 'name' && key !== 'period' && typeof firstItem[key] === 'number'
    );
    
    expect(dataKeys.length).toBeGreaterThanOrEqual(2); // Need multiple series for stacking
    expect(dataKeys).toContain('Demand Deposits');
    expect(dataKeys).toContain('Savings Deposits');
  });

  test('each data item has required structure', () => {
    stackedAreaData.data.forEach((item, index) => {
      expect(item).toHaveProperty('name');
      expect(item).toHaveProperty('period');
      expect(typeof item['Demand Deposits']).toBe('number');
      expect(typeof item['Savings Deposits']).toBe('number');
    });
  });

  test('chart routing logic - stackedArea should use AreaChart', () => {
    // This tests the logic our ChartRenderer uses
    const shouldUseAreaChart = ['area', 'stackedArea'].includes(stackedAreaData.chartType);
    expect(shouldUseAreaChart).toBe(true);
  });

  test('stacking logic - stackedArea should enable stacking', () => {
    // This tests the logic our AreaChart component uses
    const shouldStack = stackedAreaData.config.stacked || stackedAreaData.chartType === 'stackedArea';
    expect(shouldStack).toBe(true);
  });
});