import React from 'react';
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Label,
} from 'recharts';
import { ChartData, MetricConfig } from '@/types/visualization';
import { formatValue } from '@/utils/formatters';
import { CHART_COLORS } from './chartColors';

interface BarChartProps {
  data: ChartData;
  height?: number | string;
  width?: number | string;
}

/**
 * BarChart component for rendering monetary values and comparing quantities
 * Uses Recharts library for rendering the chart
 */
export default function BarChart({ data, height = 400, width = '100%' }: BarChartProps) {
  const { config, chartConfig, data: rawChartData, chartType } = data;
  
  let processedData = rawChartData;
  // Expected categoryKey from config.xAxisKey or a fallback
  const categoryKey = config.xAxisKey || 
                     (config.xAxisLabel ? config.xAxisLabel.toLowerCase().replace(/\s+/g, '_') : 'category');

  if (chartType === 'multiBar' && Array.isArray(rawChartData) && rawChartData.length > 0 && rawChartData[0].hasOwnProperty('name') && rawChartData[0].hasOwnProperty('data')) {
    // Transform data for multiBar:
    // from: [ { name: "SeriesA", data: [{x: "cat1", y: valA1}, ...] }, ... ]
    // to:   [ { [categoryKey]: "cat1", SeriesA: valA1, SeriesB: valB1}, ... ]
    // where SeriesA/SeriesB are keys from chartConfig
    
    const seriesKeysFromChartConfig = Object.keys(chartConfig);
    const transformedDataMap = new Map();

    rawChartData.forEach(seriesObject => {
      // Find the key in chartConfig that corresponds to seriesObject.name (the series identifier in the raw data)
      // This assumes seriesObject.name directly matches a key in chartConfig or its label.
      const seriesDataKey = seriesKeysFromChartConfig.find(
        key => chartConfig[key].label === seriesObject.name || key === seriesObject.name
      );

      if (seriesDataKey && Array.isArray(seriesObject.data)) {
        seriesObject.data.forEach(point => {
          const xValue = point.x; // This is the actual category value like "Net Interest Income"
          if (!transformedDataMap.has(xValue)) {
            transformedDataMap.set(xValue, { [categoryKey]: xValue });
          }
          transformedDataMap.get(xValue)[seriesDataKey] = point.y;
        });
      }
    });
    processedData = Array.from(transformedDataMap.values());
  }
  
  // Extract the keys that should be rendered as bars (all except the category axis)
  // These are the keys from chartConfig (e.g., "2025", "2024" for multiBar)
  const metricKeys = Object.keys(chartConfig);
  
  // Generate bars for each metric with their respective colors
  const bars = metricKeys.map((key, index) => {
    const metricConfig: MetricConfig = chartConfig[key];
    return (
      <Bar
        key={key}
        dataKey={key}
        name={metricConfig.label}
        fill={CHART_COLORS[index % CHART_COLORS.length] || '#8884d8'}
        stroke={metricConfig.color ? undefined : '#7066bb'}
        strokeWidth={1}
        radius={[4, 4, 0, 0]}
      />
    );
  });

  // Custom tooltip formatter to use metric config for formatting
  const formatTooltip = (value: number, name: string) => {
    // Find the metric config for this bar
    const metricKey = metricKeys.find(key => chartConfig[key].label === name);
    if (metricKey && chartConfig[metricKey]) {
      const metric = chartConfig[metricKey];
      return [formatValue(value, metric.formatter, metric.precision), metric.unit || ''];
    }
    return [value, ''];
  };

  return (
    <div className="w-full overflow-hidden rounded-lg bg-white p-4 shadow-sm">
      {config.title && (
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-800">{config.title}</h3>
          {config.subtitle && <p className="text-sm text-gray-500">{config.subtitle}</p>}
          {config.description && !config.subtitle && (
            <p className="text-sm text-gray-500">{config.description}</p>
          )}
          {config.footer && (
            <p className="text-xs text-gray-400 mt-1">{config.footer}</p>
          )}
        </div>
      )}
      
      <ResponsiveContainer width={width} height={height}>
        <RechartsBarChart
          data={processedData}
          margin={{ top: 10, right: 30, left: 20, bottom: 30 }}
          barSize={config.stack ? 20 : 40}
          barGap={config.stack ? 0 : 4}
          barCategoryGap={config.stack ? '10%' : '20%'}
        >
          {config.showGrid !== false && <CartesianGrid strokeDasharray="3 3" vertical={false} />}
          
          <XAxis
            dataKey={categoryKey}
            scale="point"
            padding={{ left: 20, right: 20 }}
            tick={{ fontSize: 12 }}
            tickLine={true}
            axisLine={true}
          >
            {config.xAxisLabel && <Label value={config.xAxisLabel} offset={-10} position="insideBottom" />}
          </XAxis>
          
          <YAxis
            tick={{ fontSize: 12 }}
            tickLine={true}
            axisLine={true}
            tickFormatter={(value) => {
              // Format Y-axis ticks based on the first metric's config
              if (metricKeys.length > 0) {
                const firstMetric = chartConfig[metricKeys[0]];
                return formatValue(value, firstMetric.formatter, firstMetric.precision);
              }
              return value;
            }}
          >
            {config.yAxisLabel && <Label value={config.yAxisLabel} angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />}
          </YAxis>
          
          <Tooltip
            formatter={formatTooltip}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
              padding: '8px 12px',
            }}
          />
          
          {config.showLegend && (
            <Legend
              verticalAlign={config.legendPosition === 'top' || config.legendPosition === 'bottom' ? config.legendPosition : 'bottom'}
              align={config.legendPosition === 'left' || config.legendPosition === 'right' ? config.legendPosition : 'center'}
              iconType="circle"
              iconSize={10}
              wrapperStyle={{ paddingTop: '10px' }}
            />
          )}
          
          {bars}
        </RechartsBarChart>
      </ResponsiveContainer>

      {/* Display totalLabel if provided */}
      {config.totalLabel && (
        <div className="mt-2 text-sm text-gray-500 text-center">
          {config.totalLabel}
        </div>
      )}
    </div>
  );
} 