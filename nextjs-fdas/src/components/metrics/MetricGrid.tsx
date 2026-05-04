import React, { useState } from 'react';
import { FinancialMetric, MetricCitation } from '@/types';
import MetricCard from './MetricCard';

interface MetricGridProps {
  metrics: FinancialMetric[];
  title?: string;
  subtitle?: string;
  onMetricClick?: (citation: MetricCitation) => void;
}

/**
 * MetricGrid component for organizing multiple metrics in a responsive grid layout
 * Includes filtering by category
 */
export default function MetricGrid({ metrics, title, subtitle, onMetricClick }: MetricGridProps) {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  
  // Extract unique categories from metrics
  const categories = Array.from(new Set(metrics.map(m => m.category).filter(Boolean))) as string[];
  
  // Filter metrics by selected category
  const filteredMetrics = selectedCategory
    ? metrics.filter(m => m.category === selectedCategory)
    : metrics;
  
  return (
    <div className="workspace-summary-block p-4">
      {/* Header section with title and category filter */}
      <div className="mb-4">
        {title && <h2 className="text-lg font-avenir-pro-demi text-foreground">{title}</h2>}
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
        
        {/* Category filter tabs (only show if we have categories) */}
        {categories.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            <button
              className={`px-3 py-1 text-xs rounded-full ${
                selectedCategory === null
                  ? 'bg-primary text-primary-foreground'
                  : 'border border-border bg-muted/70 text-foreground hover:bg-muted'
              }`}
              onClick={() => setSelectedCategory(null)}
            >
              All
            </button>
            
            {categories.map(category => (
              <button
                key={category}
                className={`px-3 py-1 text-xs rounded-full ${
                  selectedCategory === category
                    ? 'bg-primary text-primary-foreground'
                    : 'border border-border bg-muted/70 text-foreground hover:bg-muted'
                }`}
                onClick={() => setSelectedCategory(category)}
              >
                {category}
              </button>
            ))}
          </div>
        )}
      </div>
      
      {/* Metrics grid */}
      {filteredMetrics.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredMetrics.map((metric, index) => (
            <MetricCard
              key={`${metric.name}-${index}`}
              metric={metric}
              onClick={
                metric.citation && onMetricClick
                  ? () => onMetricClick(metric.citation as MetricCitation)
                  : undefined
              }
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-6">
          <p className="text-muted-foreground">No metrics available</p>
        </div>
      )}
    </div>
  );
} 