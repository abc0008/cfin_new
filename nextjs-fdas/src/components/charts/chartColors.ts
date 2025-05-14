// Shared chart color palette for all chart components
// You can adjust or expand this palette as needed

export const CHART_COLORS = [
  '#8884d8', // Purple
  '#82ca9d', // Green
  '#ffc658', // Yellow
  '#ff7300', // Orange
  '#0088fe', // Blue
  '#00c49f', // Teal
  '#ffbb28', // Gold
  '#ff8042', // Orange-Red
  '#a4de6c', // Light Green
  '#d0ed57', // Light Yellow
];

// For charts that use both stroke and fill (e.g., AreaChart)
export const CHART_COLORS_STROKE_FILL = CHART_COLORS.map(color => ({ stroke: color, fill: color })); 