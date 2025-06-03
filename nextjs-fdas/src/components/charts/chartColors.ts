// Professional chart color palette based on financial presentation style
// Optimized for data visualization with strong contrast and clarity

export const CHART_COLORS = [
  '#8f0f56', // Deep Red/Mulberry - Primary brand color, excellent for key metrics
  '#02a88e', // Professional Teal - Secondary brand color, great for positive data
  '#00bed5', // Bright Blue - Accent color, good for highlights and comparisons
  '#e5241d', // Strong Red - Alert/negative values, clear warning color
  '#2c3e50', // Dark Blue-Gray - Professional dark neutral
  '#7f8c8d', // Medium Gray - Balanced neutral color
  '#95a5a6', // Light Gray - Subtle data points
  '#34495e', // Charcoal - Alternative dark color
];

// Enhanced color palette with stroke and fill variations for area charts
export const CHART_COLORS_STROKE_FILL = [
  { stroke: '#8f0f56', fill: 'rgba(143, 15, 86, 0.1)' },   // Mulberry with transparency
  { stroke: '#02a88e', fill: 'rgba(2, 168, 142, 0.1)' },   // Teal with transparency
  { stroke: '#00bed5', fill: 'rgba(0, 190, 213, 0.1)' },   // Blue with transparency
  { stroke: '#e5241d', fill: 'rgba(229, 36, 29, 0.1)' },   // Red with transparency
  { stroke: '#2c3e50', fill: 'rgba(44, 62, 80, 0.1)' },    // Dark blue-gray with transparency
  { stroke: '#7f8c8d', fill: 'rgba(127, 140, 141, 0.1)' }, // Medium gray with transparency
  { stroke: '#95a5a6', fill: 'rgba(149, 165, 166, 0.1)' }, // Light gray with transparency
  { stroke: '#34495e', fill: 'rgba(52, 73, 94, 0.1)' },    // Charcoal with transparency
];

// Semantic color palette for specific chart types
export const SEMANTIC_COLORS = {
  // Trend indicators
  positive: '#02a88e',  // Teal for growth/positive trends
  negative: '#e5241d',  // Red for decline/negative trends
  neutral: '#7f8c8d',   // Gray for stable/neutral trends
  
  // Financial categories
  revenue: '#8f0f56',   // Mulberry for revenue data
  expenses: '#e5241d',  // Red for expenses
  profit: '#02a88e',    // Teal for profit
  assets: '#00bed5',    // Blue for assets
  
  // Performance indicators
  high: '#02a88e',      // Teal for high performance
  medium: '#00bed5',    // Blue for medium performance
  low: '#7f8c8d',       // Gray for low performance
  warning: '#f39c12',   // Orange for warnings
  
  // Portfolio colors (matching presentation style)
  portfolio: {
    primary: '#8f0f56',     // Deep red for primary segments
    secondary: '#02a88e',   // Teal for secondary segments  
    tertiary: '#00bed5',    // Blue for tertiary segments
    quaternary: '#2c3e50',  // Dark gray for additional segments
  }
};

// Color palette specifically for pie charts (matching presentation slides)
export const PIE_CHART_COLORS = [
  '#8f0f56', // Deep Red - Primary data
  '#02a88e', // Teal - Secondary data
  '#00bed5', // Blue - Additional data
  '#2c3e50', // Dark Gray - Supporting data
  '#e5241d', // Alert Red - Negative/warning data
  '#7f8c8d', // Medium Gray - Neutral data
  '#95a5a6', // Light Gray - Background data
];

// Export default as main chart colors
export default CHART_COLORS; 