# Citation System Fixes Summary

## Issues Fixed

### 1. Citation Post-Processing
- **Problem**: All citations showed "14.0: M" instead of meaningful values
- **Solution**: Improved extraction logic to handle quarterly data tables
- **File**: `/backend/utils/citation_processor.py`

### 2. Rect Finder Error
- **Problem**: "local variable 'rects_found' referenced before assignment"
- **Solution**: Initialize `rects_found = []` before use
- **File**: `/backend/repositories/document_repository.py`

### 3. Citation Granularity
- **Original Problem**: Citations contained entire tables (1286 chars)
- **Solution**: Post-processing extracts specific values like "Interest Income: $14.0M"

## Testing Required

1. **Reload the frontend** to pick up backend changes
2. **Try a new query** that triggers citations
3. **Check the backend logs** for improved citation extraction

## Expected Improvements

1. Citations should now show specific financial metrics instead of "14.0: M"
2. Rect finder should successfully locate text in PDFs
3. Citation highlights should be more precise

## Debug Logging Added

The citation processor now logs:
- Original citation text 
- Extracted pairs found
- Processing results

Watch for logs like:
```
📊 Original citation text (1286 chars): 2024Q1 2024Q2...
📊 Found inline pair: Interest Income: $14.0M
✅ Improved citation granularity: 1286 chars -> 21 chars
```

## Known Issues

1. If citations still show generic values, check if the table format matches our patterns
2. The "processing" status in chat might be a frontend websocket handling issue