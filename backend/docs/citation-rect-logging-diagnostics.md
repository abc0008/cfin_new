# Citation Rect Finding - Logging Diagnostics

## Logging Overview

The system now has comprehensive logging to diagnose citation rect finding issues:

### 1. **Citation Processing Entry Point**
```
INFO: citation 35c04baa – needs_autocompute=True (rects_before=0, zero_area=[], type=page_location, cited_text_present=True)
```
Shows when auto-computation is triggered.

### 2. **Financial Metric Detection**
```
INFO: 🔍 Detected financial metric - searching for value part: '$4000M' from citation 'Cash & Due: $4000M'
```
Shows when the system detects and extracts value from label:value format.

### 3. **Search Strategy Generation**
```
INFO: 🔍 Search strategies for citation '35c04baa': ['$4000M', '4000M', '4000', '4000 M']
DEBUG: 📍 Citation details - Page: 1-2, Original text: 'Cash & Due: $4000M'
```
Lists all search variants that will be tried and citation context.

### 4. **Search Progress (rect_finder.py)**
```
DEBUG: 🔍 find_rects_for_text(page=1) – searching for: '4000' (normalized from 4 to 4 chars)
```
Shows exactly what text is being searched on each page.

### 5. **Search Results**

**Success Case:**
```
DEBUG: ✅ Found 1 rect(s) for '4000' on page(s) [1]
INFO: ✅ Found rects using search strategy: '4000'
INFO: ✅ Auto-bbox found 1 rect(s) for citation 35c04baa on page 1
```

**Failure Case:**
```
DEBUG: ❌ No rects found for '$4000M'
WARNING: ❌ No rects found for citation 35c04baa after trying 4 strategies: ['$4000M', '4000M', '4000']
```

### 6. **Fallback Search**
```
INFO: ✅ Found rects on page 3 using fallback search: '4000'
INFO: ✅ Fallback auto-bbox found 1 rect(s) for citation 35c04baa
```

### 7. **Final Result**
```
INFO: ↩️ Returning citation 35c04baa with 1 rect(s)
```

## How to Diagnose Issues

1. **Check if financial metric was detected**
   - Look for "Detected financial metric" log
   - If missing, citation wasn't recognized as financial

2. **Review search strategies**
   - Check the list of strategies attempted
   - Verify expected variants are included

3. **Track search progress**
   - DEBUG logs show each search attempt
   - Note which pages were searched

4. **Identify failure point**
   - "No rects found" shows complete failure
   - Check if text exists in PDF exactly as searched

5. **Monitor fallback attempts**
   - Fallback searches other pages
   - May find text on unexpected pages

## Log Levels

- **INFO**: Key events and results
- **DEBUG**: Detailed search progress (enable with appropriate log level)
- **WARNING**: Failed searches after all attempts

## Example Log Flow for Debugging

```
INFO: citation 35c04baa – needs_autocompute=True
INFO: 🔍 Detected financial metric - searching for value part: '$4000M'
INFO: 🔍 Search strategies for citation '35c04baa': ['$4000M', '4000M', '4000', '4000 M']
DEBUG: 🔍 find_rects_for_text(page=1) – searching for: '$4000M'
DEBUG: ❌ No rects found for '$4000M'
DEBUG: 🔍 find_rects_for_text(page=1) – searching for: '4000M'
DEBUG: ❌ No rects found for '4000M'
DEBUG: 🔍 find_rects_for_text(page=1) – searching for: '4000'
DEBUG: ✅ Found 1 rect(s) for '4000' on page(s) [1]
INFO: ✅ Found rects using search strategy: '4000'
INFO: ✅ Auto-bbox found 1 rect(s) for citation 35c04baa on page 1
INFO: ↩️ Returning citation 35c04baa with 1 rect(s)
```

This comprehensive logging allows complete visibility into the rect finding process.