# Citation Processor Fixes

## Issues Fixed

### 1. Incorrect Text Extraction
**Problem**: All citations were showing "14.0: M" instead of meaningful financial metrics
**Root Cause**: The regex pattern was incorrectly matching "M" as a label and "14.0" as a value

### 2. Improved Table Parsing
**Solution**: Updated citation processor with better patterns:
- Skip header lines (quarters/years)
- Handle both inline and vertical label-value pairs
- Properly format financial values with $ and M/B/K suffixes
- Better regex patterns for financial metrics

### 3. Enhanced Debug Logging
- Log full lines instead of truncated versions
- Better visibility into table structure
- Track which extraction patterns are matched

## Expected Behavior

Citations should now extract:
- **Good**: "Interest Income: $14.0M"
- **Good**: "Current Debt: $29,823"
- **Good**: "Revenue Growth: 12.5%"
- **Bad**: "14.0: M" (this was the bug)

## Testing Instructions

1. Reload the frontend to pick up backend changes
2. Send a new query that triggers citations
3. Click on citation markers - they should:
   - Show meaningful financial metrics
   - Highlight specific values in the PDF
   - Not highlight entire pages

## Key Changes

1. **Pattern Matching**: Fixed regex to properly identify labels and values
2. **Table Structure**: Better handling of quarterly financial tables
3. **Value Formatting**: Automatically add $ and M/B/K suffixes
4. **Debug Logging**: Enhanced logging to diagnose issues