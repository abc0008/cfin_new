import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
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
import { CHART_COLORS } from './chartColors';

interface MultiBarChartProps {
  data: ChartData;
  height?: number | string;
  width?: number | string;
  onDataPointClick?: (dataPoint: any) => void;
}

const MultiBarChart: React.FC<MultiBarChartProps> = ({ data, height = 400, width = '100%', onDataPointClick }) => {
  const { config, data: rawChartData, chartConfig, chartType } = data;
  
  // Ensure height is a number for ResponsiveContainer
  const chartHeight = typeof height === 'string' && height.includes('%') ? 400 : height;
  
  let processedData = rawChartData;
  const categoryKey = config.xAxisKey || (config.xAxisLabel ? config.xAxisLabel.toLowerCase().replace(/\s+/g, '_') : 'name');

  const handleBarClick = (event: any) => {
    const payload = event?.payload;
    if (payload?.citation && onDataPointClick) {
      onDataPointClick(payload);
    }
  };

  if (chartType === 'multiBar' && Array.isArray(rawChartData) && rawChartData.length > 0 && rawChartData[0].hasOwnProperty('name') && rawChartData[0].hasOwnProperty('data')) {
    const seriesKeysFromChartConfig = Object.keys(chartConfig);
    const transformedDataMap = new Map();

    rawChartData.forEach(seriesObject => {
      const seriesDataKey = seriesKeysFromChartConfig.find(
        key => chartConfig[key].label === seriesObject.name || key === seriesObject.name
      );

      if (seriesDataKey && Array.isArray(seriesObject.data)) {
        seriesObject.data.forEach(point => {
          const xValue = point.x;
          if (!transformedDataMap.has(xValue)) {
            transformedDataMap.set(xValue, { [categoryKey]: xValue });
          }
          transformedDataMap.get(xValue)[seriesDataKey] = point.y;
        });
      }
    });
    processedData = Array.from(transformedDataMap.values());
  }
  
  const dataKeys = processedData.length > 0 ? Object.keys(processedData[0]).filter(key => key !== categoryKey) : [];

  if (!processedData || processedData.length === 0) {
    return (
      <div role="status" aria-label="No data available" className="flex items-center justify-center p-4 bg-gray-50 rounded-lg min-h-[300px]">
        <p className="text-gray-500">No data available</p>
      </div>
    );
  }

  // Calculate min and max values for Y axis
  const allValues = processedData.flatMap(item => 
    dataKeys.map(key => Number(item[key]))
  ).filter(value => !isNaN(value));
  
  const minValue = Math.min(...allValues);
  const maxValue = Math.max(...allValues);
  const hasNegativeValues = minValue < 0;

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
      <figure className="flex justify-center items-center" style={{ width: width, height: chartHeight, minHeight: '300px' }} role="figure" aria-label={config.title || 'Multi Bar Chart'}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={processedData}
            margin={{ top: 10, right: 20, left: 10, bottom: 50 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
            <XAxis
              dataKey={categoryKey}
              height={60}
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12, fontFamily: 'Avenir Pro, sans-serif' }}
              tickLine={{ stroke: 'hsl(var(--border))' }}
              axisLine={{ stroke: 'hsl(var(--border))' }}
            >
              {config.xAxisLabel && (
                <Label
                  value={config.xAxisLabel}
                  position="insideBottom"
                  offset={-10}
                  style={{ 
                    textAnchor: 'middle', 
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
              domain={[
                hasNegativeValues ? minValue * 1.1 : 0,
                maxValue * 1.1
              ]}
              tickFormatter={(value) => formatValue(value, 'compact', 0)}
              width={60}
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
              formatter={(value) => [formatValue(Number(value), 'compact', 1), '']}
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
              cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }}
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
            
            {/* Zero reference line for charts with negative values */}
            {hasNegativeValues && (
              <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="3 3" />
            )}

            {/* Dynamically render bars based on data structure */}
            {dataKeys.map((key, index) => (
              <Bar
                key={key}
                dataKey={key}
                fill={config.colors?.[index] || CHART_COLORS[index % CHART_COLORS.length]}
                radius={[4, 4, 0, 0]}
                maxBarSize={30}
                stackId={config.stacked ? 'stack' : undefined}
                onClick={handleBarClick}
              />
            ))}
          </BarChart>
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
};

export default MultiBarChart; 
