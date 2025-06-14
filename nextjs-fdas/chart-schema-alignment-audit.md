# Chart Schema Alignment Audit Report

## Executive Summary

This report provides a comprehensive analysis of the schema alignment between backend and frontend for all 7 chart types in the financial data analysis system. The audit reveals several critical misalignments that could cause validation errors and rendering issues.

## Chart Types Analyzed

1. **bar** - Single series bar chart
2. **multiBar** - Multi-series bar chart
3. **line** - Line chart (single or multi-series)
4. **pie** - Pie chart
5. **area** - Area chart
6. **stackedArea** - Stacked area chart
7. **scatter** - Scatter plot

## Critical Findings

### 1. Data Format Transformation Issues

The backend `tool_processing.py` transforms data into different formats based on chart type:
- **Single series**: Transforms to `{x, y}` format
- **Multi-series (bar/multiBar/stackedArea/area)**: Transforms to `[{name: "series", data: [{x, y}]}]` format
- **Multi-series line**: Keeps flat format for frontend compatibility
- **Pie charts**: Transforms to `{x, y}` format where x is category and y is value

### 2. xAxisKey Requirements

Backend behavior:
- Pie charts: Optional, defaults to "name"
- All other charts: Required
- Validation error thrown if missing for non-pie charts

Frontend expectations vary by component.

## Detailed Analysis by Chart Type

| Chart Type | Backend Tool Definition | Backend Processing | Frontend Types | Frontend Validation | Component Expectations | Issues/Misalignments |
|------------|------------------------|-------------------|----------------|---------------------|----------------------|---------------------|
| **bar** | - Expects `chartType: "bar"`<br>- `config.xAxisKey` required<br>- `data`: array of objects<br>- `chartConfig`: metric definitions | - Transforms to `{x, y}` format for single series<br>- If multiple series detected, changes `chartType` to "multiBar"<br>- Uses `config.xAxisKey` for category axis | - `ChartData` interface expects `data: any[] \| ChartSeries[]`<br>- `xAxisKey` optional in interface | - Zod schema: `xAxisKey` optional<br>- Accepts both flat and series format | - BarChart.tsx expects flat format for single series<br>- Handles transformation from series format<br>- Uses `config.xAxisKey` or fallback | **Issue**: Backend auto-converts bar to multiBar based on data, but frontend BarChart handles both |
| **multiBar** | - Expects `chartType: "multiBar"`<br>- `config.xAxisKey` required<br>- `data`: array of objects<br>- `chartConfig`: multiple metric definitions | - Transforms to series format: `[{name: "Series", data: [{x, y}]}]`<br>- Each series key from `chartConfig` | - Same as bar | - Same as bar | - BarChart.tsx transforms series format back to flat format<br>- Expects data keyed by series names | **Issue**: Complex double transformation - backend transforms to series format, frontend transforms back to flat |
| **line** | - Expects `chartType: "line"`<br>- `config.xAxisKey` required<br>- `data`: array of objects<br>- `chartConfig`: metric definitions | - Single series: transforms to `{x, y}`<br>- Multi-series: keeps flat format (special case)<br>- Uses `config.xAxisKey` | - Same as bar | - Same as bar | - LineChart.tsx has extensive fallback logic<br>- Handles both `{x, y}` and flat formats<br>- Multiple safety checks | **Issue**: Inconsistent handling - line charts keep flat format for multi-series while others use series format |
| **pie** | - Expects `chartType: "pie"`<br>- `config.xAxisKey` optional (defaults to "name")<br>- `data`: typically `[{name, value}]` | - Transforms to `{x, y}` format<br>- `x` = category name<br>- `y` = numeric value<br>- Looks for "value" key or first numeric key | - Same as bar | - Zod includes `PieChartDataItemSchema` for `{name, value}` format | - PieChart.tsx expects `{name, value}` format<br>- Uses hardcoded "name" and "value" keys | **Issue**: Backend transforms pie data to `{x, y}` but frontend expects `{name, value}` |
| **area** | - Expects `chartType: "area"`<br>- `config.xAxisKey` required<br>- `data`: array of objects | - Single series: transforms to `{x, y}`<br>- Multi-series: transforms to series format | - Same as bar | - Same as bar | - AreaChart.tsx handles both formats<br>- Transforms series format to flat<br>- Extensive debug logging | Works correctly with current transformation |
| **stackedArea** | - Expects `chartType: "stackedArea"`<br>- `config.xAxisKey` required<br>- `data`: array of objects | - Same as area<br>- Multi-series: transforms to series format | - Same as bar | - Same as bar | - AreaChart.tsx handles stackedArea<br>- Uses `config.stack` or `chartType === 'stackedArea'` | Works correctly with current transformation |
| **scatter** | - Expects `chartType: "scatter"`<br>- `config.xAxisKey` required<br>- `data`: array of objects | - Transforms to `{x, y}` format<br>- Preserves "z" values if present | - Same as bar | - Same as bar | - ScatterChart.tsx looks for numeric keys<br>- Falls back to 'x' and 'y'<br>- Supports bubble charts with 'z' | **Issue**: Component expects direct access to data keys, but backend transforms to `{x, y}` |

## Key Issues and Recommendations

### 1. **Pie Chart Data Format Mismatch** 🔴 Critical
- **Problem**: Backend transforms to `{x, y}` but PieChart.tsx expects `{name, value}`
- **Impact**: Pie charts will not render correctly
- **Fix**: Either update backend to keep `{name, value}` format for pie charts, or update PieChart.tsx to use `x` and `y` keys

### 2. **Multi-Series Bar Chart Double Transformation** 🟡 Medium
- **Problem**: Backend transforms to series format, frontend transforms back to flat
- **Impact**: Performance overhead and complexity
- **Fix**: Consider keeping flat format in backend for bar charts

### 3. **Line Chart Inconsistent Multi-Series Handling** 🟡 Medium
- **Problem**: Line charts use different format than other multi-series charts
- **Impact**: Confusing and inconsistent data handling
- **Fix**: Standardize multi-series format across all chart types

### 4. **xAxisKey Validation Inconsistency** 🟡 Medium
- **Problem**: Backend requires xAxisKey for most charts, but frontend types/validation mark it optional
- **Impact**: Runtime errors when xAxisKey is missing
- **Fix**: Update frontend validation to match backend requirements

### 5. **Scatter Chart Key Mapping** 🟡 Medium
- **Problem**: ScatterChart looks for original data keys, but backend transforms to `{x, y}`
- **Impact**: May not correctly identify x and y axes
- **Fix**: Update ScatterChart to use transformed `x` and `y` keys consistently

## Recommended Actions

1. **Immediate**: Fix pie chart data format mismatch
2. **Short-term**: Standardize multi-series data format across all chart types
3. **Medium-term**: Align frontend validation schemas with backend requirements
4. **Long-term**: Consider simplifying the transformation pipeline to reduce complexity

## Testing Recommendations

1. Create unit tests for each chart type with both single and multi-series data
2. Test edge cases: empty data, missing xAxisKey, malformed chartConfig
3. Validate that all chart types render correctly with backend-transformed data
4. Test validation error handling for missing required fields