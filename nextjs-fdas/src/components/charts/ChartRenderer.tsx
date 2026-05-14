import React from 'react';
import type { ChartData } from '@/types/visualization';
import BarChart from './BarChart';
import LineChart from './LineChart';
import PieChart from './PieChart';
import ScatterChart from './ScatterChart';
import AreaChart from './AreaChart';
import MultiBarChart from './MultiBarChart';

interface ChartRendererProps {
  data: ChartData | null;
  className?: string;
  onDataPointClick?: (dataPoint: any) => void;
  loading?: boolean;
  error?: Error | null;
}

/**
 * ChartRenderer component acts as a pure dispatcher for different chart types
 * It renders the appropriate chart component based on the chartType in the data
 */
const ChartRenderer: React.FC<ChartRendererProps> = ({ 
  data, 
  className = '',
  onDataPointClick,
  loading = false,
  error = null
}) => {
  if (loading) {
    return (
      <div role="status" aria-label="Loading chart" className={`h-full flex items-center justify-center ${className}`}>
        <span className="text-sm text-muted-foreground">Loading chart…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className={`h-full flex items-center justify-center ${className}`}>
        <span className="text-sm text-red-600">{error.message}</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div role="status" aria-label="No chart data" className={`h-full flex items-center justify-center ${className}`}>
        <span className="text-sm text-muted-foreground">No chart data available.</span>
      </div>
    );
  }

  // Extract chart type from data
  const { chartType } = data;
  const supportedChartTypes = new Set(['bar', 'multiBar', 'line', 'pie', 'area', 'stackedArea', 'scatter']);

  console.log('ChartRenderer - Data received:', {
    chartType,
    hasData: !!data.data,
    dataLength: Array.isArray(data.data) ? data.data.length : 'not array',
    hasConfig: !!data.config,
    hasChartConfig: !!data.chartConfig,
    firstDataItem: Array.isArray(data.data) && data.data.length > 0 ? data.data[0] : null,
    chartConfigKeys: data.chartConfig ? Object.keys(data.chartConfig) : []
  });

  if (!supportedChartTypes.has(chartType)) {
    return (
      <div role="alert" className={`h-full flex items-center justify-center ${className}`}>
        <span className="text-sm text-red-600">Unsupported chart type: {chartType}</span>
      </div>
    );
  }

  const visualHeight =
    typeof data.config?.height === 'number' && data.config.height > 0
      ? data.config.height
      : chartType === 'pie'
        ? 270
        : 240;

  // Render the appropriate chart component based on chartType
  switch (chartType) {
    case 'bar':
      return (
        <figure aria-label={data.config?.title || 'Bar Chart'} className={`flex w-full justify-center ${className}`}>
          <div className="w-full max-w-5xl">
            <BarChart data={data} height={visualHeight} onDataPointClick={onDataPointClick} />
          </div>
        </figure>
      );
    
    case 'multiBar':
      return (
        <figure aria-label={data.config?.title || 'Multi Bar Chart'} className={`flex w-full justify-center ${className}`}>
          <div className="w-full max-w-5xl">
            <MultiBarChart data={data} height={visualHeight} onDataPointClick={onDataPointClick} />
          </div>
        </figure>
      );
    
    case 'line':
      return (
        <figure aria-label={data.config?.title || 'Line Chart'} className={`flex w-full justify-center ${className}`}>
          <div className="w-full max-w-5xl">
            <LineChart data={data} height={visualHeight} onDataPointClick={onDataPointClick} />
          </div>
        </figure>
      );
    
    case 'pie':
      return (
        <figure aria-label={data.config?.title || 'Pie Chart'} className={`flex w-full justify-center ${className}`}>
          <div className="w-full max-w-3xl">
            <PieChart data={data} height={visualHeight} onDataPointClick={onDataPointClick} />
          </div>
        </figure>
      );
    
    case 'area':
    case 'stackedArea':
      return (
        <figure aria-label={data.config?.title || 'Area Chart'} className={`flex w-full justify-center ${className}`}>
          <div className="w-full max-w-5xl">
            <AreaChart data={data} height={visualHeight} onDataPointClick={onDataPointClick} />
          </div>
        </figure>
      );
    
    case 'scatter':
      return (
        <figure aria-label={data.config?.title || 'Scatter Chart'} className={`flex w-full justify-center ${className}`}>
          <div className="w-full max-w-5xl">
            <ScatterChart data={data} height={visualHeight} onDataPointClick={onDataPointClick} />
          </div>
        </figure>
      );
  }
};

export default ChartRenderer; 
