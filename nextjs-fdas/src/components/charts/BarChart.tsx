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
  onDataPointClick?: (dataPoint: any) => void;
}

const CustomizedAxisTick = (props: any) => {
  const { x, y, payload } = props;
  const words = payload.value.split(' ');
  const maxCharsPerLine = 10;
  let line = '';
  const lines = [];

  for (const word of words) {
    if ((line + word).length > maxCharsPerLine) {
      lines.push(line.trim());
      line = '';
    }
    line += `${word} `;
  }
  lines.push(line.trim());

  return (
    <g transform={`translate(${x},${y})`}>
      <text x={0} y={0} dy={16} textAnchor="middle" fill="hsl(var(--muted-foreground))" fontSize={12} fontFamily="Avenir Pro, sans-serif">
        {lines.map((l, i) => (
          <tspan x="0" dy={i > 0 ? "1.2em" : "0"} key={i}>{l}</tspan>
        ))}
      </text>
    </g>
  );
};

/**
 * BarChart component for rendering monetary values and comparing quantities
 * Uses Recharts library for rendering the chart
 */
export default function BarChart({ data, height = 400, width = '100%', onDataPointClick }: BarChartProps) {
  const { config, chartConfig, data: rawChartData, chartType } = data;
  
  // Ensure height is a number for ResponsiveContainer
  const chartHeight = typeof height === 'string' && height.includes('%') ? 400 : height;
  
  let processedData = rawChartData;
  // Expected categoryKey from config.xAxisKey or a fallback
  const categoryKey = config.xAxisKey ||
                     (config.xAxisLabel ? config.xAxisLabel.toLowerCase().replace(/\s+/g, '_') : 'category');

  const handleBarClick = (data: any) => {
    const payload = data?.payload;
    if (payload?.citation && onDataPointClick) {
      onDataPointClick(payload);
    }
  };

  // Check if data is in {x, y} format (single bar chart from backend)
  let metricKeys: string[] = [];
  if (Array.isArray(rawChartData) && rawChartData.length > 0 && rawChartData[0].hasOwnProperty('x') && rawChartData[0].hasOwnProperty('y')) {
    // Transform {x, y} data for single bar chart
    const valueKey = Object.keys(chartConfig)[0] || 'value';
    processedData = rawChartData.map(item => ({
      [categoryKey]: item.x,
      [valueKey]: item.y
    }));
    metricKeys = [valueKey];
  } else if (chartType === 'bar' && chartConfig && Object.keys(chartConfig).length > 0) {
    // For regular bar charts with chartConfig, the data might already be in the right format
    metricKeys = Object.keys(chartConfig);
  } else if (processedData && processedData.length > 0) {
    // Extract metric keys from the data itself
    const firstItem = processedData[0];
    metricKeys = Object.keys(firstItem).filter(key => key !== categoryKey && typeof firstItem[key] === 'number');
  }
  
  // Format Y-axis values to use compact formatting for consistency
  const defaultFormatter = 'compact';
  const defaultPrecision = 0;

  // Generate bars for each metric with their respective colors
  const bars = metricKeys.map((key, index) => {
    const metricConfig: MetricConfig = chartConfig?.[key];
    return (
      <Bar
        key={key}
        dataKey={key}
        name={metricConfig?.label || key}
        fill={metricConfig?.color || CHART_COLORS[index % CHART_COLORS.length] || '#8884d8'}
        radius={[4, 4, 0, 0]}
        onClick={handleBarClick}
      />
    );
  });

  // Custom tooltip formatter to use metric config for formatting
  const formatTooltip = (value: number, name: string) => {
    // Find the metric config for this bar
    const metricKey = metricKeys.find(key => chartConfig?.[key]?.label === name || key === name);
    if (metricKey && chartConfig?.[metricKey]) {
      const metric = chartConfig[metricKey];
      return [formatValue(value, metric.formatter, metric.precision), metric.unit || ''];
    }
    // Default formatting
    return [formatValue(value, defaultFormatter, defaultPrecision), ''];
  };

  // Check if we have data to display
  if (!processedData || processedData.length === 0 || metricKeys.length === 0) {
    return (
      <div className="w-full bg-card rounded-lg shadow-sm border border-border p-4">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">No data available for chart</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-card rounded-lg shadow-sm border border-border p-4">
      {/* Header */}
      {(config.title || config.subtitle || config.description) && (
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
      )}
      
      {/* Chart */}
      <figure className="flex justify-center items-center" style={{ width: width, height: chartHeight, minHeight: '300px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <RechartsBarChart
            data={processedData}
            margin={{ top: 10, right: 20, left: 10, bottom: 50 }}
            barSize={40}
            barGap={8}
            barCategoryGap={'20%'}
          >
            {config.showGrid !== false && <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />}
            
            <XAxis
              dataKey={categoryKey}
              scale="point"
              padding={{ left: 20, right: 20 }}
              tick={<CustomizedAxisTick />}
              height={60}
              interval={0}
              tickLine={{ stroke: 'hsl(var(--border))' }}
              axisLine={{ stroke: 'hsl(var(--border))' }}
            >
              {config.xAxisLabel && (
                <Label 
                  value={config.xAxisLabel} 
                  offset={-10} 
                  position="insideBottom"
                  style={{ 
                    fill: 'hsl(var(--muted-foreground))',
                    fontFamily: 'Avenir Pro, sans-serif',
                    fontSize: 14
                  }}
                />
              )}
            </XAxis>
            
            <YAxis
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11, fontFamily: 'Avenir Pro, sans-serif' }}
              tickLine={{ stroke: 'hsl(var(--border))' }}
              axisLine={{ stroke: 'hsl(var(--border))' }}
              width={60}
              tickFormatter={(value) => {
                // Format Y-axis ticks based on the first metric's config or use default
                if (metricKeys.length > 0 && chartConfig?.[metricKeys[0]]) {
                  const firstMetric = chartConfig[metricKeys[0]];
                  return formatValue(value, firstMetric.formatter || defaultFormatter, firstMetric.precision ?? defaultPrecision);
                }
                // Default to compact formatting with no decimals
                return formatValue(value, defaultFormatter, defaultPrecision);
              }}
            >
              {config.yAxisLabel && (
                <Label 
                  value={config.yAxisLabel} 
                  angle={-90} 
                  position="insideLeft"
                  offset={10} 
                  style={{ 
                    textAnchor: 'middle',
                    fill: 'hsl(var(--muted-foreground))',
                    fontFamily: 'Avenir Pro, sans-serif',
                    fontSize: 13
                  }}
                />
              )}
            </YAxis>
            
            <Tooltip
              formatter={formatTooltip}
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
            
            {config.showLegend && (
              <Legend
                verticalAlign={config.legendPosition === 'top' || config.legendPosition === 'bottom' ? config.legendPosition : 'bottom'}
                align={config.legendPosition === 'left' || config.legendPosition === 'right' ? config.legendPosition : 'center'}
                iconType="rect"
                iconSize={10}
                wrapperStyle={{ 
                  paddingTop: '20px',
                  fontFamily: 'Avenir Pro, sans-serif',
                  fontSize: '14px'
                }}
              />
            )}
            
            {bars}
          </RechartsBarChart>
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
