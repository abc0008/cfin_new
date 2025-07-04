import React from 'react';
import { PieChart as RechartsPieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { ChartData } from '@/types/visualization';
import { formatValue } from '@/utils/formatters';
import { PIE_CHART_COLORS } from './chartColors';

interface PieChartProps {
  data: ChartData;
  height?: number | string;
  width?: number | string;
  onDataPointClick?: (dataPoint: any) => void;
}

const PieChart: React.FC<PieChartProps> = ({ data, height = 400, width = '100%', onDataPointClick }) => {
  const { config, data: rawChartData } = data;
  
  // Ensure height is a number for ResponsiveContainer
  const chartHeight = typeof height === 'string' && height.includes('%') ? 400 : height;
  
  // Transform data if it's in {x, y} format from backend
  const chartData = rawChartData.map(item => {
    if ('x' in item && 'y' in item) {
      // Backend transformed format
      return {
        name: item.x,
        value: item.y,
        ...item // Preserve any additional properties
      };
    }
    // Already in correct format
    return item;
  });

  const handleSliceClick = (event: any) => {
    const payload = event?.payload;
    if (payload?.citation && onDataPointClick) {
      onDataPointClick(payload);
    }
  };

  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center p-8 bg-muted/20 rounded-lg min-h-[300px]">
        <p role="status" className="text-muted-foreground font-avenir-pro">No pie chart data available</p>
      </div>
    );
  }

  return (
    <div className="w-full bg-card rounded-lg shadow-sm border border-border p-4">
      {/* Header */}
      <div className="mb-6">
        <h3 className="font-avenir-pro-demi text-xl text-foreground tracking-tighter">{config.title}</h3>
        {config.subtitle && (
          <p className="font-avenir-pro-light text-sm text-muted-foreground mt-1">{config.subtitle}</p>
        )}
        {config.description && (
          <p className="font-avenir-pro text-sm text-muted-foreground mt-2">{config.description}</p>
        )}
      </div>

      {/* Chart */}
      <figure className="flex justify-center items-center" style={{ width: width, height: chartHeight, minHeight: '300px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <RechartsPieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={120}
              innerRadius={40}
              paddingAngle={2}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              labelLine={false}
              className="font-avenir-pro text-xs"
              onClick={handleSliceClick}
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={PIE_CHART_COLORS[index % PIE_CHART_COLORS.length]}
                  stroke="rgba(255, 255, 255, 0.8)"
                  strokeWidth={2}
                />
              ))}
            </Pie>
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
            <Tooltip 
              formatter={(value) => formatValue(Number(value), 'compact', 1)}
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
          </RechartsPieChart>
        </ResponsiveContainer>
      </figure>

      {/* Footer */}
      {config.footer && (
        <div className="mt-6 pt-4 border-t border-border">
          <p className="font-avenir-pro text-sm text-muted-foreground">{config.footer}</p>
        </div>
      )}
      {config.totalLabel && (
        <div className="mt-4">
          <p className="font-avenir-pro-demi text-sm text-foreground">{config.totalLabel}</p>
        </div>
      )}
    </div>
  );
};

export default PieChart; 
