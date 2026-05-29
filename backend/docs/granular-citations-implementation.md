# Granular Citations Implementation

## Problem
Backend citations were capturing entire tables or sections instead of specific values. For example:
- **Before**: "As of 12/31/2023 ($ in millions) Current Debt Long-term Debt Total Debt..."
- **Desired**: "$29,823" (just the specific value)

## Solution Implemented

### 1. Created Citation Instructions Module
**File**: `/backend/services/citation_instructions.py`

This module contains explicit instructions for Claude to create granular citations:
- Cite individual values, not entire tables
- Each financial figure should have its own citation
- Include minimal context (metric name + value)
- Place citations immediately after mentioning specific values

### 2. Enhanced System Prompts

Updated the following files to include granular citation instructions:

#### `/backend/services/conversation_service.py`
- Modified `_build_system_prompt()` to import and append `GRANULAR_CITATION_INSTRUCTIONS`
- Ensures all conversation-based interactions use granular citations

#### `/backend/pdf_processing/api_service.py`
- Updated `extract_structured_financial_data()` method
- Added citation instructions to both instances of the financial data extraction prompt
- Imports `GRANULAR_CITATION_INSTRUCTIONS` from the citation module

#### `/backend/pdf_processing/prompts/default_financial_analysis_prompt.md`
- Added comprehensive CITATION GUIDELINES section
- Provides examples of good vs bad citations
- Emphasizes citing at the value level

### 3. Key Instructions Added

```
CITATION GUIDELINES:
1. BE SPECIFIC AND GRANULAR: 
   - Cite individual values, not entire tables or sections
   - For example, cite "$29,823" instead of the entire debt table

2. CITE AT THE VALUE LEVEL:
   - Good: "Current Debt: $29,823"
   - Bad: "As of 12/31/2023 ($ in millions) Current Debt Long-term Debt Total Debt..."

3. MULTIPLE SPECIFIC CITATIONS:
   - If discussing multiple values from the same table, create separate citations for each
   - Each financial figure should have its own citation

4. CONTEXT IN CITATIONS:
   - Include minimal context (metric name + value)
   - Example: "Net Revenue: $2.5B" not the entire income statement

5. CITATION PLACEMENT:
   - Place citations immediately after mentioning specific values
   - Don't wait until the end of a paragraph to cite

6. NUMBER-FIRST SELECTION:
   - Prioritize concrete numeric financial data when choosing what to cite
   - Avoid citing purely narrative sentences unless no numeric source exists

7. TABLE SOURCE PREFERENCE:
   - Default to financial tables over narrative sentences when both contain the same figure
   - When the same figure appears in narrative text and a table, cite the table cell
   - Source priority: table cell > chart label > narrative mention
   - Use narrative sentences for citations only when no table or chart source exists

8. BANKING METRIC FORMATTING:
   - Rates, yields, margins, and capital ratios: two decimal % (e.g., 4.25%)
   - Dollar balances: match document unit scale and precision
   - EPS and per-share values: two decimals; counts as integers with separators
   - Apply the same precision in cited_text as in narrative and tool outputs
```

### Single source of truth

Citation rules and banking metric formatting live in `/backend/services/citation_instructions.py` and are injected at runtime via `enhance_system_prompt_with_citation_instructions()`. The default financial analysis markdown prompt no longer duplicates this block; it is appended when loaded in `api_service.py`. Prebuilt analysis strategies and LangGraph citation nodes use the same helper or `FINANCIAL_AGENT_INSTRUCTIONS`.

## Testing

Created `/backend/test_granular_citations.py` to verify the implementation:
- Uploads a financial document to Claude Files API
- Sends a query requesting specific value citations
- Monitors citation events during streaming
- Measures citation granularity (text length ≤100 chars is considered granular)

## Expected Impact

1. **Better User Experience**: Citations will highlight specific numbers rather than entire sections
2. **More Precise References**: Each financial metric gets its own citation
3. **Improved Navigation**: Users can jump directly to specific values in the PDF

## Implementation Notes

- The solution works by guiding Claude's native citation feature through explicit instructions
- No changes to the citation processing logic were needed
- The approach is backward compatible with existing code
- Citations are still created automatically by Claude, but now with better granularity

## Next Steps

1. Test with various financial document types
2. Monitor citation quality in production
3. Fine-tune instructions if needed based on results
4. Consider adding citation granularity metrics to monitoring