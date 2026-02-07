# Citation Text Granularity Issue

## Problem
Backend citations are capturing entire tables or sections instead of specific values used in the analysis.

### Current Behavior
Citations contain full table text like:
```
"As of 12/31/2023 ($ in millions) Current Debt Long-term Debt Total Debt..."
```

### Desired Behavior
Citations should contain only the specific values being referenced:
```
"$29,823" (for Current Debt value)
```

## Root Cause
This is a backend issue in the citation extraction logic. The frontend has no control over citation granularity - it simply displays what the backend returns via `/api/documents/{id}/citations`.

## Required Backend Changes

1. **Improve Citation Extraction Logic**
   - Extract specific values rather than entire table cells/rows
   - Use more precise text matching when creating citations
   - Consider the context of what's being analyzed

2. **Citation Creation During Analysis**
   - When the analysis references a specific value (e.g., "$29,823"), create a citation for just that value
   - Include surrounding context minimally (e.g., "Current Debt: $29,823")

3. **Backend API Enhancement Options**
   - Add optional `granularity` parameter to citation endpoints
   - Implement smarter text extraction that identifies numeric values within larger text blocks
   - Use the analysis context to determine what specific values are being referenced

## Frontend Workaround (Not Recommended)
While not ideal, the frontend could potentially:
- Parse citation text to extract numeric values
- Use regex to identify specific data points
- Display truncated versions of citations

However, this would be fragile and the proper solution is to fix the backend extraction logic.

## Implementation Priority
- **Priority**: Medium (as specified by user)
- **Impact**: Improves user experience by making citations more precise and relevant
- **Effort**: Requires backend changes to citation extraction logic

## Next Steps
1. Review backend citation extraction code
2. Implement more granular text extraction
3. Test with various document types to ensure accuracy
4. Update frontend only if API changes require it