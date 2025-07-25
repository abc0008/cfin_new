# Citation Post-Processing Solution

## Problem
Claude's native citation feature extracts large blocks of text (entire tables) instead of specific values. This causes:
- Citations highlighting entire pages instead of specific values
- Poor user experience when clicking citation markers
- Rect finder unable to locate large text blocks in PDFs

## Root Cause
Claude's citation extraction operates at the API level, before our prompt instructions can influence it. Even with explicit granular citation instructions in prompts, Claude still returns large text blocks.

## Solution: Post-Processing Citations

### Approach
Since we cannot control Claude's citation extraction at the API level, we implemented a post-processing solution that:
1. Intercepts citations after they come from Claude API
2. Analyzes the cited text to extract specific values
3. Replaces large text blocks with granular value-label pairs
4. Preserves the original citation metadata (page numbers, rects, etc.)

### Implementation

#### 1. Citation Processor Module
Created `/backend/utils/citation_processor.py` with intelligent extraction logic:
- Detects multi-line table structures
- Extracts label-value pairs (e.g., "Current Debt: $29,823")
- Handles various financial data formats (currency, percentages, ratios)
- Preserves already-granular citations

#### 2. Integration Points
Modified `/backend/pdf_processing/api_service.py` to process citations at key points:
- `_process_streaming_response()` - Process citations from streaming responses
- `_extract_financial_data_with_citations_by_file_id()` - Process extraction citations
- `analyze_with_visualization_tools_streaming()` - Process analysis citations

### Results

#### Before (Large Citation):
```
As of 12/31/2023 
($ in millions)
Current Debt
$29,823
Long-term Debt
$176,265
Total Debt
$206,089
```
(98 characters)

#### After (Granular Citation):
```
Current Debt: $29,823
```
(21 characters - 78.6% reduction)

### Benefits
1. **Improved Highlighting**: Rect finder can now locate specific values in PDFs
2. **Better UX**: Users see highlighted values, not entire pages
3. **Backward Compatible**: Original citation data preserved for debugging
4. **Automatic**: No changes needed to prompts or Claude configuration

### Technical Details

The citation processor uses pattern matching to identify:
- Table structures with labels and values on separate lines
- Currency values with various formats ($29,823, $2.5B, 125M)
- Percentage values (ROE: 12.5%, Growth Rate: 15%)
- Label-value pairs in various formats

Processing logic:
1. Check if citation is already granular (<50 chars)
2. Detect table structures by analyzing line patterns
3. Extract first meaningful label-value pair
4. Fall back to regex patterns for other formats
5. Truncate as last resort if no pattern matches

### Testing
Created comprehensive test suite in `/backend/test_citation_postprocessing.py` that verifies:
- Table data extraction
- Already-granular citation preservation
- Various financial data formats
- Reduction metrics

### Next Steps
1. Monitor citation quality in production
2. Add more financial patterns as needed
3. Consider caching processed citations
4. Add metrics for citation granularity to monitoring