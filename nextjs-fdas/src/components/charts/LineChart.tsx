import React from 'react';
import {
  LineChart as RechartsLineChart,
  Line,
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

interface LineChartProps {
  data: ChartData;
  height?: number | string;
  width?: number | string;
  onDataPointClick?: (dataPoint: any) => void;
}

/**
 * LineChart component for rendering trends and time series data
 * Uses Recharts library for rendering the chart
 */
export default function LineChart({ data, height = 400, width = '100%', onDataPointClick }: LineChartProps) {
  // Ensure height is a number for ResponsiveContainer
  const chartHeight = typeof height === 'string' && height.includes('%') ? 400 : height;
  const { config, chartConfig, data: rawDataPointsFromBackend } = data;
  let processedData = rawDataPointsFromBackend;

  // Debug logging to understand data structure
  console.log('LineChart - Debug Info:', {
    chartType: data.chartType,
    hasConfig: !!config,
    hasChartConfig: !!chartConfig,
    chartConfigKeys: chartConfig ? Object.keys(chartConfig) : [],
    dataLength: Array.isArray(rawDataPointsFromBackend) ? rawDataPointsFromBackend.length : 0,
    firstDataItem: Array.isArray(rawDataPointsFromBackend) && rawDataPointsFromBackend.length > 0 ? rawDataPointsFromBackend[0] : null,
    configXAxisKey: config?.xAxisKey,
    rawDataStructure: Array.isArray(rawDataPointsFromBackend) && rawDataPointsFromBackend.length > 0 ? 
      (rawDataPointsFromBackend[0].hasOwnProperty('data') ? 'multi-series' : 'flat') : 'unknown',
    fullData: JSON.stringify(rawDataPointsFromBackend, null, 2)
  });

  const handleLineClick = (event: any) => {
    const payload = event?.payload;
    if (payload?.citation && onDataPointClick) {
      onDataPointClick(payload);
    }
  };

  // Determine the key for the category axis (X-axis)
  // Prefer xAxisKey from config, fallback to a sanitized xAxisLabel, or default to 'category' or 'date'
  const categoryKey = config.xAxisKey || 
                     (config.xAxisLabel ? config.xAxisLabel.toLowerCase().replace(/\s+/g, '_') : 'date');
  
  // Determine the metric keys for the lines from chartConfig
  const metricKeys = chartConfig ? Object.keys(chartConfig) : [];

  // Transform data if it's in [{x: val, y: val}, ...] format
  if (
    Array.isArray(rawDataPointsFromBackend) && 
    rawDataPointsFromBackend.length > 0 && 
    rawDataPointsFromBackend[0].hasOwnProperty('x') && 
    rawDataPointsFromBackend[0].hasOwnProperty('y')
  ) {
    if (metricKeys.length === 1) {
      // Single metric transformation
      const singleMetricKey = metricKeys[0]; // e.g., "eps"
      processedData = rawDataPointsFromBackend.map(point => ({
        [categoryKey]: point.x,       // Use the derived categoryKey, e.g., { date: "Q1 2024", ... }
        [singleMetricKey]: point.y    // Use the metricKey from chartConfig, e.g., { ..., eps: 0.78 }
      }));
    } else {
      // Multi-series transformation for {x, y} format data
      // The backend sometimes sends {x, y} format even for multi-series charts
      // We need to transform this into flat format that Recharts expects
      console.warn('Multi-series line chart received {x, y} format data, this should be flat format. Converting...', {
        metricKeys,
        dataLength: rawDataPointsFromBackend.length,
        firstDataPoint: rawDataPointsFromBackend[0]
      });
      
      // For multi-series charts with {x, y} data, we need to either:
      // 1. Use the data as-is if it's actually single series
      // 2. Spread the y values across the metric keys if we have exactly matching counts
      
      if (metricKeys.length === rawDataPointsFromBackend.length) {
        // Special case: each data point represents one metric series
        // Transform [{x: "Q1", y: 100}, {x: "Q2", y: 120}] with metricKeys ["ci_loans", "cre_loans"]
        // to [{date: "Q1", ci_loans: 100}, {date: "Q2", cre_loans: 120}] - but this is wrong
        // Actually, this case suggests malformed data, keep original
        processedData = rawDataPointsFromBackend;
      } else {
        // Assume it's actually a single series and use the first metric key
        const primaryMetricKey = metricKeys[0];
        processedData = rawDataPointsFromBackend.map(point => ({
          [categoryKey]: point.x,
          [primaryMetricKey]: point.y
        }));
        console.log('Converted multi-series {x,y} data to single-series flat format using primary metric:', primaryMetricKey);
      }
    }
  }
  // If data is already in the correct flat format with multiple metric keys, it should pass through
  // e.g. [{category: "Q1", sales: 100, profit: 20}, {category: "Q2", sales: 120, profit: 25}]
  // and chartConfig: {sales: {label: "Sales"}, profit: {label: "Profit"}}
  // In this case, categoryKey would be "category", and metricKeys would be ["sales", "profit"]

  // Handle case where chartConfig is undefined or empty
  if (!chartConfig || metricKeys.length === 0) {
    console.warn('LineChart: No chartConfig or metric keys found. Data:', { config, chartConfig, rawDataPointsFromBackend });
    
    // Fallback: try to render with basic data if we have {x, y} format
    if (Array.isArray(rawDataPointsFromBackend) && 
        rawDataPointsFromBackend.length > 0 && 
        rawDataPointsFromBackend[0].hasOwnProperty('x') && 
        rawDataPointsFromBackend[0].hasOwnProperty('y')) {
      
      console.log('LineChart: Attempting fallback rendering with {x, y} data');
      
      return (
        <div className="w-full overflow-hidden rounded-lg bg-white p-4 shadow-sm">
          {config.title && (
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-gray-800">{config.title}</h3>
              {config.subtitle && <p className="text-sm text-gray-500">{config.subtitle}</p>}
            </div>
          )}
          
          <ResponsiveContainer width={width} height={height}>
            <RechartsLineChart
              data={rawDataPointsFromBackend}
              margin={{ top: 10, right: 30, left: 20, bottom: 30 }}
            >
              {config.showGrid !== false && <CartesianGrid strokeDasharray="3 3" />}
              
              <XAxis
                dataKey="x"
                scale="auto"
                padding={{ left: 10, right: 10 }}
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
              >
                {config.yAxisLabel && <Label value={config.yAxisLabel} angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />}
              </YAxis>
              
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(255, 255, 255, 0.95)',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
                  padding: '8px 12px',
                }}
              />
              
              <Line
                type="monotone"
                dataKey="y"
                name={config.title || 'Value'}
                stroke={CHART_COLORS[0]}
                strokeWidth={2}
                dot={{ r: 3, strokeWidth: 1 }}
                activeDot={{ r: 5, strokeWidth: 1, onClick: handleLineClick }}
                onClick={handleLineClick}
              />
            </RechartsLineChart>
          </ResponsiveContainer>
        </div>
      );
    }
    
    return (
      <div className="w-full overflow-hidden rounded-lg bg-white p-4 shadow-sm">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-800">
            {config?.title || 'Line Chart'}
          </h3>
          <p className="text-sm text-red-500">
            Chart configuration error: No metric configuration found
          </p>
          <details className="mt-2">
            <summary className="text-xs text-gray-500 cursor-pointer">Debug info</summary>
            <pre className="text-xs text-gray-400 mt-1 overflow-auto max-h-32">
              {JSON.stringify({ config, chartConfig, dataLength: rawDataPointsFromBackend?.length }, null, 2)}
            </pre>
          </details>
        </div>
      </div>
    );
  }

  // Generate lines for each metric with their respective colors
  const lines = metricKeys.map((key, index) => {
    const metricConfig: MetricConfig = chartConfig[key];
    return (
      <Line
        key={key}
        type="monotone"
        dataKey={key}
        name={metricConfig?.label || key}
        stroke={CHART_COLORS[index % CHART_COLORS.length] || '#8884d8'}
        strokeWidth={2}
        dot={{ r: 3, strokeWidth: 1 }}
        activeDot={{ r: 5, strokeWidth: 1, onClick: handleLineClick }}
        onClick={handleLineClick}
      />
    );
  });

  // Custom tooltip formatter to use metric config for formatting
  const formatTooltip = (value: number, name: string) => {
    // Find the metric config for this line
    const metricKey = metricKeys.find(key => chartConfig[key]?.label === name);
    if (metricKey && chartConfig[metricKey]) {
      const metric = chartConfig[metricKey];
      return [formatValue(value, metric.formatter, metric.precision), metric.unit || ''];
    }
    return [value, ''];
  };

  // Final logging before render
  console.log('LineChart - Final render data:', {
    processedDataLength: processedData.length,
    processedDataFirst: processedData[0],
    metricKeys,
    categoryKey,
    linesCount: lines.length
  });

  // SAFETY FALLBACK: If we have data but something is wrong with processing, try simple rendering
  if (Array.isArray(rawDataPointsFromBackend) && rawDataPointsFromBackend.length > 0 && metricKeys.length === 0) {
    console.log('LineChart - Using simple fallback rendering');
    
    // Try to find numeric keys for basic rendering
    const firstItem = rawDataPointsFromBackend[0];
    const numericKeys = Object.keys(firstItem).filter(key => 
      typeof firstItem[key] === 'number' && key !== config.xAxisKey
    );
    
    if (numericKeys.length > 0) {
      return (
        <div className="w-full overflow-hidden rounded-lg bg-white p-4 shadow-sm">
          {config.title && (
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-gray-800">{config.title}</h3>
              {config.subtitle && <p className="text-sm text-gray-500">{config.subtitle}</p>}
            </div>
          )}
          
          <div style={{ width: width, height: chartHeight, minHeight: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <RechartsLineChart
                data={rawDataPointsFromBackend}
                margin={{ top: 10, right: 30, left: 20, bottom: 30 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey={config.xAxisKey || categoryKey} />
                <YAxis />
                <Tooltip />
                <Legend />
                {numericKeys.map((key, index) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    name={key}
                    stroke={CHART_COLORS[index % CHART_COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 3, strokeWidth: 1 }}
                  />
                ))}
              </RechartsLineChart>
            </ResponsiveContainer>
          </div>
        </div>
      );
    }
  }

  return (
    <div className="w-full overflow-hidden rounded-lg bg-white p-4 shadow-sm">
      {config.title && (
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-800">{config.title}</h3>
          {config.subtitle && <p className="text-sm text-gray-500">{config.subtitle}</p>}
        </div>
      )}
      
      <div style={{ width: width, height: chartHeight, minHeight: '300px' }}>
        <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart
          data={processedData}
          margin={{ top: 10, right: 30, left: 20, bottom: 30 }}
        >
          {config.showGrid !== false && <CartesianGrid strokeDasharray="3 3" />}
          
          <XAxis
            dataKey={categoryKey}
            scale="auto"
            padding={{ left: 10, right: 10 }}
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
            labelFormatter={(label) => {
              // Format the X-axis label in the tooltip (usually a date)
              if (typeof label === 'string' && label.includes('-')) {
                // If it looks like a date string, format it
                try {
                  const date = new Date(label);
                  return date.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  });
                } catch (e) {
                  return label;
                }
              }
              return label;
            }}
          />
          
          {config.showLegend && (
            <Legend
              verticalAlign={config.legendPosition === 'top' || config.legendPosition === 'bottom' ? config.legendPosition : 'bottom'}
              align={config.legendPosition === 'left' || config.legendPosition === 'right' ? config.legendPosition : 'center'}
              iconType="line"
              iconSize={10}
              wrapperStyle={{ paddingTop: '10px' }}
            />
          )}
          
          {lines}
        </RechartsLineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
} 
