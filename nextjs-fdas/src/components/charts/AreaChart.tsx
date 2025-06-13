import React from 'react';
import {
  ResponsiveContainer,
  AreaChart as RechartsAreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Label,
  ReferenceLine
} from 'recharts';
import { ChartData } from '@/types/visualization';
import { formatValue } from '@/utils/formatters';
import { CHART_COLORS_STROKE_FILL } from './chartColors';

interface AreaChartProps {
  data: ChartData;
  height?: number | string;
  width?: number | string;
  onDataPointClick?: (dataPoint: any) => void;
}

const AreaChart: React.FC<AreaChartProps> = ({ data, height = 400, width = '100%', onDataPointClick }) => {
  // Ensure height is a number for ResponsiveContainer
  const chartHeight = typeof height === 'string' && height.includes('%') ? 400 : height;
  const { config, data: rawChartData, chartType, chartConfig } = data;
  
  // Debug logging
  console.log('AreaChart - Debug Info:', {
    chartType,
    hasConfig: !!config,
    hasChartConfig: !!chartConfig,
    chartConfigKeys: chartConfig ? Object.keys(chartConfig) : [],
    dataLength: Array.isArray(rawChartData) ? rawChartData.length : 0,
    firstDataItem: Array.isArray(rawChartData) && rawChartData.length > 0 ? rawChartData[0] : null
  });
  
  // Check if data is in multi-series format [{name: "series", data: [{x, y}]}]
  const isMultiSeries = rawChartData.length > 0 && 
    rawChartData[0].hasOwnProperty('name') && 
    rawChartData[0].hasOwnProperty('data') &&
    Array.isArray(rawChartData[0].data);
  
  let chartData = rawChartData;
  let dataKeys = [];
  
  if (isMultiSeries) {
    console.log('AreaChart - Transforming multi-series data to flat format for Recharts');
    // Transform multi-series data to flat format for Recharts
    const transformedData = new Map();
    const xAxisKey = config.xAxisKey || 'category';
    
    // Collect all x values from all series
    rawChartData.forEach(series => {
      if (series.data && Array.isArray(series.data)) {
        series.data.forEach(point => {
          if (!transformedData.has(point.x)) {
            transformedData.set(point.x, { [xAxisKey]: point.x });
          }
        });
      }
    });
    
    // Add y values for each series - use series.name as the key
    rawChartData.forEach((series) => {
      const seriesKey = series.name; // Use the series name directly
      dataKeys.push(seriesKey);
      
      if (series.data && Array.isArray(series.data)) {
        series.data.forEach(point => {
          const row = transformedData.get(point.x);
          if (row) {
            row[seriesKey] = point.y;
          }
        });
      }
    });
    
    chartData = Array.from(transformedData.values());
    
    console.log('AreaChart - Multi-series transformation complete:', {
      originalSeriesCount: rawChartData.length,
      transformedDataLength: chartData.length,
      dataKeys,
      firstTransformedItem: chartData[0]
    });
  } else if (chartData.length > 0) {
    // Check if data is in {x, y} format - this means single series data
    if (chartData[0].hasOwnProperty('x') && chartData[0].hasOwnProperty('y')) {
      // For {x, y} format, we need to transform it for AreaChart
      // Use the first chartConfig key as the data key
      const firstChartConfigKey = chartConfig ? Object.keys(chartConfig)[0] : 'value';
      dataKeys = [firstChartConfigKey];
      
      // Transform the data to flat format
      const xAxisKey = config.xAxisKey || 'category';
      chartData = rawChartData.map(point => ({
        [xAxisKey]: point.x,
        [firstChartConfigKey]: point.y
      }));
    } else {
      // Flat data format - extract keys normally
      dataKeys = Object.keys(chartData[0]).filter(key => key !== (config.xAxisKey || 'name'));
    }
  }

  const handleAreaClick = (event: any) => {
    const payload = event?.payload;
    if (payload?.citation && onDataPointClick) {
      onDataPointClick(payload);
    }
  };

  if (!chartData || chartData.length === 0) {
    return (
      <div role="status" aria-label="No data available" className="flex items-center justify-center p-4 bg-gray-50 rounded-lg min-h-[300px]">
        <p className="text-gray-500">No data available</p>
      </div>
    );
  }

  // Additional logging for debugging
  console.log('AreaChart - Final processed data structure:', {
    chartDataLength: chartData.length,
    dataKeys,
    firstChartItem: chartData[0],
    hasChartConfig: !!chartConfig,
    chartConfigKeys: chartConfig ? Object.keys(chartConfig) : [],
    isMultiSeries,
    xAxisKey: config.xAxisKey || 'category',
    allChartData: chartData.slice(0, 3) // Show first 3 items for debugging
  });

  // Calculate min and max values for Y axis
  const allValues = chartData.flatMap(item => 
    dataKeys.map(key => Number(item[key]))
  ).filter(value => !isNaN(value));
  
  console.log('AreaChart - Numeric values extracted:', {
    allValues: allValues.slice(0, 10), // Show first 10 values
    allValuesLength: allValues.length,
    dataKeysUsed: dataKeys
  });
  
  if (allValues.length === 0) {
    console.warn('AreaChart - No valid numeric values found in data');
    return (
      <div className="w-full">
        <div className="mb-4">
          {config.title && (
            <h3 className="text-lg font-semibold text-gray-900">{config.title}</h3>
          )}
          <p className="text-sm text-red-500">
            Chart error: No valid numeric data found
          </p>
          <details className="mt-2">
            <summary className="text-xs text-gray-500 cursor-pointer">Debug info</summary>
            <pre className="text-xs text-gray-400 mt-1 overflow-auto max-h-32">
              {JSON.stringify({ chartData: chartData.slice(0, 2), dataKeys, isMultiSeries }, null, 2)}
            </pre>
          </details>
        </div>
      </div>
    );
  }
  
  const minValue = Math.min(...allValues);
  const maxValue = Math.max(...allValues);
  const hasNegativeValues = minValue < 0;

  return (
    <div className="w-full">
      <div className="mb-4">
        {config.title && (
          <h3 role="heading" aria-level={3} className="text-lg font-semibold text-gray-900">
            {config.title}
          </h3>
        )}
        {config.subtitle && (
          <p role="doc-subtitle" className="text-sm text-gray-500">
            {config.subtitle}
          </p>
        )}
        {config.description && (
          <p role="doc-description" className="text-sm text-gray-500 mt-1">
            {config.description}
          </p>
        )}
      </div>

      <div style={{ width: width, height: chartHeight, minHeight: '300px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <RechartsAreaChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 20, bottom: 50 }}
          >
            <defs>
              {dataKeys.map((key, index) => {
                const color = config.colors?.[index] || CHART_COLORS_STROKE_FILL[index % CHART_COLORS_STROKE_FILL.length].stroke;
                const safeKey = key.replace(/\s+/g, '').replace(/[^a-zA-Z0-9]/g, '');
                return (
                  <linearGradient key={key} id={`color${safeKey}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.8}/>
                    <stop offset="95%" stopColor={color} stopOpacity={0.1}/>
                  </linearGradient>
                );
              })}
              {/* Fallback gradient */}
              <linearGradient id="colorfallback" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={CHART_COLORS_STROKE_FILL[0].stroke} stopOpacity={0.8}/>
                <stop offset="95%" stopColor={CHART_COLORS_STROKE_FILL[0].stroke} stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey={config.xAxisKey || 'category'}
              height={60}
              tick={{ fill: '#666', fontSize: 12 }}
            >
              {config.xAxisLabel && (
                <Label
                  value={config.xAxisLabel}
                  position="bottom"
                  offset={0}
                  style={{ textAnchor: 'middle', fill: '#666' }}
                />
              )}
            </XAxis>
            <YAxis
              tick={{ fill: '#666', fontSize: 12 }}
              domain={[
                hasNegativeValues ? minValue * 1.1 : 0,
                maxValue * 1.1
              ]}
              tickFormatter={(value) => {
                // Format Y-axis ticks based on the first data key's config
                if (chartConfig && dataKeys.length > 0) {
                  const firstDataKey = dataKeys[0];
                  const metricConfig = chartConfig[firstDataKey];
                  if (metricConfig && metricConfig.formatter) {
                    return formatValue(value, metricConfig.formatter, metricConfig.precision);
                  }
                }
                // Default formatting with compact notation for readability
                return formatValue(value, 'compact', 1);
              }}
            >
              {config.yAxisLabel && (
                <Label
                  value={config.yAxisLabel}
                  angle={-90}
                  position="left"
                  style={{ textAnchor: 'middle', fill: '#666' }}
                />
              )}
            </YAxis>
            <Tooltip
              formatter={(value, name) => {
                // Format tooltip values based on metric config
                if (chartConfig && typeof name === 'string') {
                  const metricConfig = chartConfig[name];
                  if (metricConfig && metricConfig.formatter) {
                    return [formatValue(Number(value), metricConfig.formatter, metricConfig.precision), metricConfig.label || name];
                  }
                }
                return [formatValue(Number(value), 'compact', 1), name];
              }}
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #ccc',
                borderRadius: '4px'
              }}
              cursor={{ stroke: '#666', strokeWidth: 1 }}
            />
            {config.showLegend !== false && (
              <Legend
                verticalAlign="bottom"
                align="center"
                iconType="rect"
                iconSize={10}
                wrapperStyle={{ paddingTop: '10px' }}
              />
            )}
            
            {/* Zero reference line for charts with negative values */}
            {hasNegativeValues && (
              <ReferenceLine y={0} stroke="#666" strokeDasharray="3 3" />
            )}

            {/* Dynamically render areas based on data structure */}
            {dataKeys.length > 0 ? dataKeys.map((key, index) => {
              const colorObj = CHART_COLORS_STROKE_FILL[index % CHART_COLORS_STROKE_FILL.length];
              const customColor = config.colors?.[index];
              const safeKey = key.replace(/\s+/g, '').replace(/[^a-zA-Z0-9]/g, '');
              
              console.log(`AreaChart - Rendering area ${index}: key=${key}, safeKey=${safeKey}, color=${customColor || colorObj.stroke}`);
              
              return (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={customColor || colorObj.stroke}
                  fill={`url(#color${safeKey})`}
                  fillOpacity={1}
                  stackId={config.stacked || chartType === 'stackedArea' ? 'stack' : undefined}
                  dot={config.showDots ?? false}
                  activeDot={{ r: 6, stroke: customColor || colorObj.stroke, strokeWidth: 2, onClick: handleAreaClick }}
                  onClick={handleAreaClick}
                />
              );
            }) : (
              <Area
                key="fallback"
                type="monotone"
                dataKey="value"
                stroke={CHART_COLORS_STROKE_FILL[0].stroke}
                fill={`url(#colorfallback)`}
                fillOpacity={1}
                stackId={chartType === 'stackedArea' ? 'stack' : undefined}
                onClick={handleAreaClick}
              />
            )}
          </RechartsAreaChart>
        </ResponsiveContainer>
      </div>

      {config.footer && (
        <p role="doc-footnote" className="text-sm text-gray-500 mt-4">
          {config.footer}
        </p>
      )}
      {config.totalLabel && (
        <p role="doc-footnote" className="text-sm font-medium text-gray-700 mt-2">
          {config.totalLabel}
        </p>
      )}
    </div>
  );
};

export default AreaChart; 
