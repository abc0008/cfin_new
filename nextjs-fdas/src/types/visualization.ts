/**
 * TypeScript interfaces for visualization data
 * These interfaces match the backend Pydantic models
 */

import type { FinancialMetric } from './index';

// Supported chart types - Aligned with backend and Zod schema
export type ChartType = 'bar' | 'multiBar' | 'line' | 'pie' | 'area' | 'stackedArea' | 'scatter';

// Supported table types - Aligned with backend and Zod schema
export type TableType = 'simple' | 'matrix' | 'comparison' | 'summary' | 'detailed';

// Format types for table columns
export type FormatType = 'number' | 'currency' | 'percentage' | 'text';

// Direction for financial metrics trend
export type TrendDirection = 'up' | 'down' | 'neutral';

// Configuration for individual metrics in charts
export interface MetricConfig {
  label: string;
  unit?: string;
  color?: string;
  formatter?: string;
  precision?: number;
}

// Configuration for charts
export interface ChartConfig {
  title: string;
  description?: string;
  subtitle?: string;
  xAxisKey?: string; // Optional for pie charts
  yAxisKey?: string;
  xAxisLabel?: string;
  yAxisLabel?: string;
  showLegend?: boolean;
  legendPosition?: 'top' | 'bottom' | 'left' | 'right';
  showGrid?: boolean;
  stack?: boolean;
  stacked?: boolean; // Alternative property name used by some components
  colors?: string[];
  footer?: string;
  totalLabel?: string;
  showDots?: boolean; // For line/area charts
  [key: string]: any;
}

// Chart data item - used in tool-based visualization
export interface ChartDataItem {
  x: string | number;
  y: number;
  label?: string;
  category?: string;
  [key: string]: any;
}

// Chart data series - used in tool-based visualization
export interface ChartSeries {
  name: string;
  data: ChartDataItem[];
  color?: string;
}

// Chart data structure
export interface ChartData {
  chartType: ChartType;
  config: ChartConfig;
  data: any[] | ChartSeries[];  // Support both direct data array and series format
  chartConfig?: {
    [key: string]: MetricConfig;
  };
  xAxisTitle?: string;
  yAxisTitle?: string;
  legendPosition?: 'top' | 'right' | 'bottom' | 'left';
}

// Table column configuration
export interface TableColumn {
  key: string;
  header: string;
  label?: string;
  width?: number;
  align?: 'left' | 'center' | 'right';
  formatter?: string;
  format?: FormatType;
}

// Table configuration
export interface TableConfig {
  title: string;
  description?: string;
  footer?: string;
  columns: TableColumn[];
  showRowNumbers?: boolean;
  sortable?: boolean;
  pagination?: boolean;
  pageSize?: number;
}

// Table data structure
export interface TableData {
  tableType: TableType;
  config: TableConfig;
  data: any[];
}

// Combined visualization data that can contain both charts and tables
export interface VisualizationData {
  charts: ChartData[];
  tables: TableData[];
  metrics?: FinancialMetric[];
  analysisText?: string;
  // Legacy format fields - keep for backward compatibility
  monetaryValues?: any;
  percentages?: any;
}

// Interface for financial metrics to be displayed in cards
// FinancialMetric is now defined in src/types/index.ts to match backend/Zod schema

export interface AnalysisResult {
  id: string;
  type: 'financial' | 'market' | 'operational';
  data: {
    metrics: FinancialMetric[];
    charts?: ChartData[];
    tables?: TableData[];
  };
  timestamp: string;
}

export type { FinancialMetric, MetricCitation } from './index';
