# Citation Rect Finding Fix

## Problem
Citations like "Cash & Due: $4000M" were not finding rects in the PDF because:
1. The citation processor constructs these by combining label and value from different parts of tables
2. The rect finder was searching for the entire string "Cash & Due: $4000M" which doesn't exist as a contiguous string in the PDF
3. The PDF likely has "Cash & Due" in one cell and "4000" in another cell

## Solution
Modified the rect finding logic in `document_repository.py` to:

1. **Detect processed financial citations**: For citations containing ":" and "$", extract just the value part
   - Example: "Cash & Due: $4000M" → search for "$4000M"

2. **Try multiple search strategies**: For financial values, try variants:
   - Original: "$4000M"
   - Without dollar sign: "4000M"
   - Without suffix: "4000"
   - With space: "4000 M"

3. **Apply strategies to fallback search**: Use the same strategies when searching other pages

## Implementation Details

### Code Changes in `citation_to_api_schema` method:
```python
# For citations that look like processed financial values (e.g., "Cash & Due: $4000M"),
# try to extract just the value part for better rect finding
if ":" in raw_search_text and "$" in raw_search_text:
    # Extract the value after the colon
    parts = raw_search_text.split(":", 1)
    if len(parts) == 2:
        value_part = parts[1].strip()
        # Try finding just the value first
        logger.info("🔍 Searching for value part only: '%s' from citation '%s'", value_part, raw_search_text)
        search_text = value_part

# Try multiple search strategies for financial values
search_strategies = [search_text]

# If searching for a financial value like "$4000M", also try variants
if "$" in search_text:
    # Try without dollar sign
    no_dollar = search_text.replace("$", "").strip()
    search_strategies.append(no_dollar)
    
    # Try without suffix (M, B, K)
    if no_dollar and no_dollar[-1] in "MBK":
        no_suffix = no_dollar[:-1].strip()
        search_strategies.append(no_suffix)
        
    # Also try with spaces around the number
    if no_dollar and no_dollar[-1] in "MBK":
        with_space = no_dollar[:-1].strip() + " " + no_dollar[-1]
        search_strategies.append(with_space)
```

## Expected Results
Citations should now find the correct rects for financial values in tables, enabling precise highlighting instead of full page highlights.

## Testing
1. Restart the backend server
2. Test with a document containing financial tables
3. Click on citation markers - they should highlight specific values