import React from 'react';
import {
  ResponsiveContainer,
  ScatterChart as RechartsScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine
} from 'recharts';
import { ChartData } from '@/types/visualization';
import { formatValue } from '@/utils/formatters';
import { CHART_COLORS } from './chartColors';

interface ScatterChartProps {
  data: ChartData;
  height?: number | string;
  width?: number | string;
  onDataPointClick?: (dataPoint: any) => void;
}

/**
 * Scatter Chart component for visualizing correlation between two variables
 */
export default function ScatterChart({ data, height = 400, width = '100%', onDataPointClick }: ScatterChartProps) {
  const { config, data: chartData, chartConfig } = data;
  
  // Ensure height is a number for ResponsiveContainer
  const chartHeight = typeof height === 'string' && height.includes('%') ? 400 : height;

  const handlePointClick = (event: any) => {
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

  // Check if data is in transformed {x, y} format from backend
  const isTransformedData = chartData.length > 0 && 'x' in chartData[0] && 'y' in chartData[0];
  
  // Determine x and y axis keys
  const xAxisKey = isTransformedData ? 'x' : (config.xAxisKey || Object.keys(chartData[0]).find(
    key => typeof chartData[0][key] === 'number' && key !== 'z'
  ) || 'x');
  
  const yAxisKey = isTransformedData ? 'y' : (Object.keys(chartData[0]).find(
    key => typeof chartData[0][key] === 'number' && key !== xAxisKey && key !== 'z'
  ) || 'y');
  
  // Check if we have a z-axis value for bubble size
  const hasZValue = chartData.some(item => 'z' in item && typeof item.z === 'number');

  // Format tooltip value based on the metric config
  const formatTooltipValue = (value: any, name: string) => {
    const metricConfig = chartConfig[name];
    if (metricConfig) {
      return [formatValue(value, metricConfig.formatter, metricConfig.precision), metricConfig.unit || ''];
    }
    return [value, ''];
  };

  return (
    <div className="w-full bg-card rounded-lg shadow-sm border border-border p-4">
      {/* Header */}
      <div className="mb-6">
        {config.title && (
          <h3 className="font-avenir-pro-demi text-xl text-foreground tracking-tighter">
            {config.title}
          </h3>
        )}
        {config.subtitle && (
          <p className="font-avenir-pro-light text-sm text-muted-foreground mt-1">
            {config.subtitle}
          </p>
        )}
        {config.description && !config.subtitle && (
          <p className="font-avenir-pro text-sm text-muted-foreground mt-2">
            {config.description}
          </p>
        )}
      </div>

      {/* Chart */}
      <figure className="flex justify-center items-center" style={{ width: width, height: chartHeight, minHeight: '300px' }} role="figure" aria-label={`Scatter plot of ${config.title || 'data points'}`}>
        <ResponsiveContainer width="100%" height="100%">
          <RechartsScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 50 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis 
              dataKey={xAxisKey} 
              name={config.xAxisLabel || xAxisKey}
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12, fontFamily: 'Avenir Pro, sans-serif' }}
              tickLine={{ stroke: 'hsl(var(--border))' }}
              axisLine={{ stroke: 'hsl(var(--border))' }} 
              label={{ 
                value: config.xAxisLabel || xAxisKey, 
                position: 'insideBottom', 
                offset: -10,
                style: {
                  fill: 'hsl(var(--muted-foreground))',
                  fontFamily: 'Avenir Pro, sans-serif',
                  fontSize: 14
                }
              }}
              aria-label={config.xAxisLabel || xAxisKey}
            />
            <YAxis 
              dataKey={yAxisKey} 
              name={config.yAxisLabel || yAxisKey}
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12, fontFamily: 'Avenir Pro, sans-serif' }}
              tickLine={{ stroke: 'hsl(var(--border))' }}
              axisLine={{ stroke: 'hsl(var(--border))' }}
              width={60}
              label={{ 
                value: config.yAxisLabel || yAxisKey, 
                angle: -90, 
                position: 'insideLeft',
                offset: 10,
                style: {
                  textAnchor: 'middle',
                  fill: 'hsl(var(--muted-foreground))',
                  fontFamily: 'Avenir Pro, sans-serif',
                  fontSize: 13
                }
              }}
              tickFormatter={(value) => formatValue(value, 'compact', 1)}
              aria-label={config.yAxisLabel || yAxisKey}
            />
            
            {hasZValue && <ZAxis dataKey="z" range={[50, 500]} />}
            
            <Tooltip 
              formatter={formatTooltipValue}
              labelFormatter={(label) => `${config.xAxisLabel || xAxisKey}: ${label}`}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                fontFamily: 'Avenir Pro, sans-serif',
                fontSize: '14px',
              }}
              labelStyle={{
                fontFamily: 'Avenir Pro, sans-serif',
                fontWeight: '600',
                color: 'hsl(var(--foreground))'
              }}
            />
            
            {config.showLegend !== false && (
              <Legend 
                verticalAlign="bottom"
                align="center"
                iconType="rect"
                iconSize={10}
                wrapperStyle={{ 
                  paddingTop: '20px',
                  fontFamily: 'Avenir Pro, sans-serif',
                  fontSize: '14px'
                }}
              />
            )}
            
            {/* Add reference lines at x=0 and y=0 if needed */}
            <ReferenceLine x={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="3 3" />
            <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="3 3" />
            
            <Scatter
              name={config.title || "Data"}
              data={chartData}
              fill={CHART_COLORS[0]}
              aria-label={`Scatter plot points for ${config.title || 'data'}`}
              onClick={handlePointClick}
            />
          </RechartsScatterChart>
        </ResponsiveContainer>
      </figure>

      {/* Footer */}
      {config.footer && (
        <div className="mt-6 pt-4 border-t border-border">
          <p className="font-avenir-pro text-sm text-muted-foreground">
            {config.footer}
          </p>
        </div>
      )}
      {config.totalLabel && (
        <div className="mt-4">
          <p className="font-avenir-pro-demi text-sm text-foreground">
            {config.totalLabel}
          </p>
        </div>
      )}
    </div>
  );
} 
