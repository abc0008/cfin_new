import React from 'react';
import { formatValue, formatChange, getTrend } from '@/utils/formatters';

interface MetricCardProps {
  metric: {
    name: string;
    value: number;
    unit?: string;
    percentChange?: number;
    previousValue?: number;
    trend?: 'up' | 'down' | 'neutral';
    category?: string;
    description?: string;
  };
  className?: string;
  onClick?: () => void;
}

/**
 * MetricCard component for displaying individual financial metrics
 * Includes trend indicators and formatted values
 */
export default function MetricCard({ metric, className = '', onClick }: MetricCardProps) {
  // Calculate trend if not provided
  const trend = metric.trend || 
    (metric.percentChange !== undefined ? getTrend(metric.percentChange) : 'neutral');
  
  // Determine color based on trend using brand colors
  const colorMap = {
    up: 'text-brand-hobgoblin', // Hobgoblin for positive
    down: 'text-brand-lust', // Lust for negative
    neutral: 'text-brand-mt-rushmore' // Mt. Rushmore for neutral
  };
  
  const bgColorMap = {
    up: 'bg-brand-hobgoblin bg-opacity-10',
    down: 'bg-brand-lust bg-opacity-10', 
    neutral: 'bg-brand-pigeon bg-opacity-30'
  };
  
  const trendColor = colorMap[trend];
  const trendBgColor = bgColorMap[trend];
  
  // Icon based on trend
  const TrendIcon = () => {
    if (trend === 'up') {
      return (
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          viewBox="0 0 20 20" 
          fill="currentColor" 
          className="w-5 h-5"
        >
          <path 
            fillRule="evenodd" 
            d="M10 17a.75.75 0 01-.75-.75V5.612L5.29 9.77a.75.75 0 01-1.08-1.04l5.25-5.5a.75.75 0 011.08 0l5.25 5.5a.75.75 0 11-1.08 1.04l-3.96-4.158V16.25A.75.75 0 0110 17z" 
            clipRule="evenodd" 
          />
        </svg>
      );
    } else if (trend === 'down') {
      return (
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          viewBox="0 0 20 20" 
          fill="currentColor" 
          className="w-5 h-5"
        >
          <path 
            fillRule="evenodd" 
            d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z" 
            clipRule="evenodd" 
          />
        </svg>
      );
    } else {
      return (
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          viewBox="0 0 20 20" 
          fill="currentColor" 
          className="w-5 h-5"
        >
          <path 
            fillRule="evenodd" 
            d="M10 2a.75.75 0 01.75.75v6.5h6.5a.75.75 0 010 1.5h-6.5v6.5a.75.75 0 01-1.5 0v-6.5h-6.5a.75.75 0 010-1.5h6.5v-6.5A.75.75 0 0110 2z" 
            clipRule="evenodd" 
          />
        </svg>
      );
    }
  };
  
  return (
    <div 
      className={`metric-card ${className} ${onClick ? 'cursor-pointer hover:shadow-md' : ''}`}
      onClick={onClick}
    >
      <div className="flex justify-between items-start">
        <h3 className="metric-card-title">{metric.name}</h3>
        
        {/* Display category label if provided */}
        {metric.category && (
          <span className="px-3 py-1 text-xs rounded-full bg-muted text-muted-foreground font-avenir-pro uppercase tracking-wide">
            {metric.category}
          </span>
        )}
      </div>
      
      <div className="mt-4 flex items-baseline">
        <div className="metric-card-value">
          {formatValue(metric.value, 'currency', 0)}
        </div>
        {metric.unit && (
          <div className="ml-2 text-sm text-muted-foreground font-avenir-pro-light">
            {metric.unit}
          </div>
        )}
      </div>
      
      {/* Trend indicator */}
      {metric.percentChange !== undefined && (
        <div className="metric-card-change">
          <div className={`flex items-center ${trendColor}`}>
            <span className={`p-2 rounded-full ${trendBgColor} mr-2`}>
              <TrendIcon />
            </span>
            <span className="font-avenir-pro-demi">
              {formatChange(metric.percentChange, 'percent')}
            </span>
          </div>
          
          {metric.previousValue !== undefined && (
            <span className="ml-3 text-xs text-muted-foreground font-avenir-pro-light">
              vs {formatValue(metric.previousValue, 'currency', 0)}
            </span>
          )}
        </div>
      )}
      
      {/* Description if provided */}
      {metric.description && (
        <p className="mt-4 text-sm text-muted-foreground font-avenir-pro-light line-clamp-2">
          {metric.description}
        </p>
      )}
    </div>
  );
} 