import React from 'react';
import type { ChartData } from '@/types/visualization';
import { EnhancedChart } from '../visualization/EnhancedChart';
import BarChart from './BarChart';
import LineChart from './LineChart';
import PieChart from './PieChart';
import ScatterChart from './ScatterChart';
import AreaChart from './AreaChart';

interface ChartRendererProps {
  data: ChartData;
  className?: string;
  onDataPointClick?: (dataPoint: any) => void;
}

/**
 * ChartRenderer component acts as a pure dispatcher for different chart types
 * It renders the appropriate chart component based on the chartType in the data
 */
const ChartRenderer: React.FC<ChartRendererProps> = ({ 
  data, 
  className = '',
  onDataPointClick
}) => {
  // Extract chart type from data
  const { chartType } = data;

  console.log('ChartRenderer - Data received:', {
    chartType,
    hasData: !!data.data,
    dataLength: Array.isArray(data.data) ? data.data.length : 'not array',
    hasConfig: !!data.config,
    hasChartConfig: !!data.chartConfig,
    firstDataItem: Array.isArray(data.data) && data.data.length > 0 ? data.data[0] : null,
    chartConfigKeys: data.chartConfig ? Object.keys(data.chartConfig) : []
  });

  // Render the appropriate chart component based on chartType
  switch (chartType) {
    case 'bar':
      return (
        <div className={`h-full ${className}`}>
          <BarChart data={data} height="100%" onDataPointClick={onDataPointClick} />
        </div>
      );
    
    case 'multiBar':
      return (
        <div className={`h-full ${className}`}>
          <BarChart data={data} height="100%" onDataPointClick={onDataPointClick} />
        </div>
      );
    
    case 'line':
      return (
        <div className={`h-full ${className}`}>
          <LineChart data={data} height="100%" onDataPointClick={onDataPointClick} />
        </div>
      );
    
    case 'pie':
      return (
        <div className={`h-full ${className}`}>
          <PieChart data={data} height="100%" onDataPointClick={onDataPointClick} />
        </div>
      );
    
    case 'area':
    case 'stackedArea':
      return (
        <div className={`h-full ${className}`}>
          <AreaChart data={data} height="100%" onDataPointClick={onDataPointClick} />
        </div>
      );
    
    case 'scatter':
      return (
        <div className={`h-full ${className}`}>
          <ScatterChart data={data} height="100%" onDataPointClick={onDataPointClick} />
        </div>
      );
    
    default:
      // Fallback to EnhancedChart for any other chart types
      return (
        <div className={`bg-white rounded-lg shadow-sm p-4 h-full flex flex-col ${className}`}>
          {data.config?.title && (
            <div className="mb-4 flex-shrink-0">
              <h3 className="text-lg font-semibold text-gray-900">{data.config.title}</h3>
              {data.config.description && (
                <p className="text-sm text-gray-500 mt-1">{data.config.description}</p>
              )}
            </div>
          )}
          <div className="relative flex-1 min-h-[300px]">
            <EnhancedChart 
              data={data.data}
              chartType={chartType}
              onDataPointClick={onDataPointClick}
              height="100%"
              xAxisTitle={data.config?.xAxisLabel}
              yAxisTitle={data.config?.yAxisLabel}
            />
          </div>
        </div>
      );
  }
};

export default ChartRenderer; 
