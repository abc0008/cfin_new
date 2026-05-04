// Professional chart color palette based on financial presentation style
// Optimized for data visualization with strong contrast and clarity

export const CHART_COLORS = [
  '#ffac03', // Aperture gold - primary metric color
  '#739666', // Aperture green - positive/secondary data
  '#6e8ea0', // Aperture slate - comparison series
  '#e6724f', // Aperture orange - caution/negative data
  '#263c49', // Deep slate - neutral dark series
  '#606060', // Mid gray - neutral series
  '#b8b8b8', // Light gray - supporting series
  '#8b6da5', // Plum accent - overflow series
];

// Enhanced color palette with stroke and fill variations for area charts
export const CHART_COLORS_STROKE_FILL = [
  { stroke: '#ffac03', fill: 'rgba(255, 172, 3, 0.16)' },
  { stroke: '#739666', fill: 'rgba(115, 150, 102, 0.14)' },
  { stroke: '#6e8ea0', fill: 'rgba(110, 142, 160, 0.14)' },
  { stroke: '#e6724f', fill: 'rgba(230, 114, 79, 0.14)' },
  { stroke: '#263c49', fill: 'rgba(38, 60, 73, 0.14)' },
  { stroke: '#606060', fill: 'rgba(96, 96, 96, 0.14)' },
  { stroke: '#b8b8b8', fill: 'rgba(184, 184, 184, 0.18)' },
  { stroke: '#8b6da5', fill: 'rgba(139, 109, 165, 0.14)' },
];

// Semantic color palette for specific chart types
export const SEMANTIC_COLORS = {
  // Trend indicators
  positive: '#739666',  // Aperture green for growth/positive trends
  negative: '#e6724f',  // Aperture orange for decline/negative trends
  neutral: '#606060',   // Gray for stable/neutral trends
  
  // Financial categories
  revenue: '#ffac03',   // Aperture gold for revenue data
  expenses: '#e6724f',  // Aperture orange for expenses
  profit: '#739666',    // Aperture green for profit
  assets: '#6e8ea0',    // Aperture slate for assets
  
  // Performance indicators
  high: '#739666',      // Green for high performance
  medium: '#6e8ea0',    // Slate for medium performance
  low: '#606060',       // Gray for low performance
  warning: '#ffac03',   // Gold for warnings
  
  // Portfolio colors (matching presentation style)
  portfolio: {
    primary: '#ffac03',     // Gold for primary segments
    secondary: '#739666',   // Green for secondary segments
    tertiary: '#6e8ea0',    // Slate for tertiary segments
    quaternary: '#263c49',  // Deep slate for additional segments
  }
};

// Color palette specifically for pie charts (matching presentation slides)
export const PIE_CHART_COLORS = [
  '#ffac03', // Gold - Primary data
  '#739666', // Green - Secondary data
  '#6e8ea0', // Slate - Additional data
  '#263c49', // Deep slate - Supporting data
  '#e6724f', // Orange - Negative/warning data
  '#606060', // Medium Gray - Neutral data
  '#b8b8b8', // Light Gray - Background data
];

// Export default as main chart colors
export default CHART_COLORS; 