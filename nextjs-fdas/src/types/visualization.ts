/**
 * TypeScript interfaces for visualization data
 * These interfaces match the backend Pydantic models
 */

// Supported chart types
export type ChartType = 'line' | 'bar' | 'area' | 'pie' | 'multiBar' | 'scatter';

// Supported table types
export type TableType = 'comparison' | 'summary' | 'detailed';

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
  description: string;
  subtitle?: string;
  xAxisLabel?: string;
  yAxisLabel?: string;
  xAxisKey?: string;
  trend?: Record<string, any>;
  footer?: string;
  totalLabel?: string;
  showLegend?: boolean;
  legendPosition?: 'top' | 'bottom' | 'left' | 'right';
  showGrid?: boolean;
  height?: number;
  width?: number;
  stack?: boolean;
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
  chartType: 'bar' | 'multiBar' | 'line' | 'pie' | 'area' | 'stackedArea';
  config: ChartConfig;
  data: Record<string, any>[];
  chartConfig: Record<string, MetricConfig>;
}

// Table column configuration
export interface TableColumn {
  key: string;
  label: string;
  header?: string;
  format?: 'number' | 'currency' | 'percentage' | 'text';
  width?: number;
  align?: 'left' | 'center' | 'right';
  formatter?: string;
}

// Table configuration
export interface TableConfig {
  title: string;
  description: string;
  subtitle?: string;
  footer?: string;
  columns: TableColumn[];
  showRowNumbers?: boolean;
  sortable?: boolean;
  pagination?: boolean;
  pageSize?: number;
  height?: number;
  width?: number;
}

// Table data structure
export interface TableData {
  tableType: 'simple' | 'matrix' | 'comparison';
  config: TableConfig;
  data: Record<string, any>[];
}

// Combined visualization data that can contain both charts and tables
export interface VisualizationData {
  charts?: ChartData[];
  tables?: TableData[];
  monetaryValues?: Record<string, any>;
  percentages?: Record<string, any>;
  keywordFrequency?: Record<string, any>;
}

// Interface for financial metrics to be displayed in cards
export interface FinancialMetric {
  name: string;
  value: number;
  previousValue?: number;
  percentChange?: number;
  trend?: TrendDirection;
  unit?: string;
  category?: string;
  description?: string;
  highlight?: boolean;
}

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