"""
Citation Post-Processing Utilities
==================================

This module provides utilities to post-process citations from Claude API
to extract specific values from large text blocks and improve granularity.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

def extract_specific_value_from_citation(cited_text: str, page_number: Optional[int] = None) -> Tuple[str, bool]:
    """
    Extract specific financial values from a large citation text block.
    
    Args:
        cited_text: The full cited text from Claude
        page_number: The page number where the citation appears
        
    Returns:
        Tuple of (extracted_value, was_modified)
    """
    # If citation is already small/granular, return as-is
    if len(cited_text) <= 50:
        return cited_text, False
    
    # First check if this looks like a table with multiple values
    lines = cited_text.strip().split('\n')
    
    logger.info(f"📊 Processing citation with {len(lines)} lines. First line: '{lines[0] if lines else ''}'")
    
    # Debug: Log first few lines to understand table structure
    if len(lines) > 3:
        logger.debug(f"📊 Table preview - Line 0: '{lines[0]}'")
        logger.debug(f"📊 Table preview - Line 1: '{lines[1] if len(lines) > 1 else ''}'")
        logger.debug(f"📊 Table preview - Line 2: '{lines[2] if len(lines) > 2 else ''}'")
        logger.debug(f"📊 Table preview - Line 3: '{lines[3] if len(lines) > 3 else ''}'")
        logger.debug(f"📊 Table preview - Line 4: '{lines[4] if len(lines) > 4 else ''}'")
    
    # Look for patterns that indicate this is a table
    if len(lines) > 3:
        # Check if we have labels and values in separate lines
        value_lines = []
        label_lines = []
        
        for line in lines:
            line = line.strip()
            # Look for lines containing numeric values (including decimals)
            if re.search(r'[\d,]+\.?\d*', line):
                value_lines.append(line)
                logger.debug(f"Value line detected: {line[:50]}")
            elif line and not line.replace(' ', '').replace('(', '').replace(')', '').replace('$', '').replace('in', '').replace('millions', '').isdigit():
                label_lines.append(line)
                logger.debug(f"Label line detected: {line[:50]}")
        
        # If we found multiple values, try to extract one with its label
        logger.debug(f"Found {len(value_lines)} value lines and {len(label_lines)} label lines")
        if len(value_lines) >= 2:
            # First, try to find a label-value pair in the same line pattern
            for line in lines:
                if ':' in line and re.search(r'\$?[\d,]+\.?\d*[BMK]?', line):
                    return line.strip(), True
            
            # Look for specific patterns in the table
            found_pairs = []
            
            # We need to identify the structure - is it a typical financial table with years/quarters as headers?
            header_line_idx = -1
            quarter_headers = []
            for i, line in enumerate(lines[:5]):  # Check first 5 lines for headers
                if re.search(r'\b(20\d{2}Q\d|Q\d\s*20\d{2})\b', line) and not re.search(r'[A-Za-z]{3,}', line):
                    # This line contains quarters but no significant text labels - likely a header
                    header_line_idx = i
                    # Extract quarters/years from header
                    quarter_headers = re.findall(r'\b(20\d{2}Q\d|Q\d\s*20\d{2})\b', line)
                    logger.debug(f"Found quarter headers at line {i}: {quarter_headers}")
                    break
            
            # First, try to find rows with label and values on the same line
            for i, line in enumerate(lines):
                # Skip header lines
                if any(skip in line.lower() for skip in ['as of', 'date', 'period', 'in millions', 'in thousands']):
                    continue
                
                # Skip lines that are just quarters/years (e.g., "2024Q1 2024Q2 2024Q3 2024Q4")
                # Updated pattern to match years and quarters more flexibly
                if i == header_line_idx or re.match(r'^[\d\sQ]+$', line.strip()) or re.match(r'^(\d{4}Q\d\s*)+$', line.strip()):
                    logger.debug(f"Skipping quarter header line {i}: {line}")
                    continue
                    
                # Look for lines with both text and values
                # Pattern 1: Label followed by values (e.g., "Interest Income 900.0 910.0 920.0")
                # First try to identify if this line has a label followed by numbers
                # Match pattern: text label followed by multiple numbers
                label_value_match = re.match(r'^([A-Za-z][A-Za-z\s&\-,\.]+?)\s+([\d\.\s]+)$', line.strip())
                if label_value_match:
                    potential_label = label_value_match.group(1).strip()
                    values_str = label_value_match.group(2).strip()
                    # Extract individual values
                    values = re.findall(r'[\d,]+\.?\d*', values_str)
                    parts = [potential_label] + values
                else:
                    # Fallback to space/tab splitting for other formats
                    parts = re.split(r'\s{2,}|\t', line)  # Split by multiple spaces or tabs
                if len(parts) >= 2:
                    potential_label = parts[0].strip()
                    # Check if first part is a label (contains letters, not just numbers)
                    if re.search(r'[A-Za-z]', potential_label) and not re.match(r'^[\d\s\.\-\$]+$', potential_label):
                        # Found a label, now extract values
                        values = []
                        for part in parts[1:]:
                            # Check if this part is a numeric value
                            value_match = re.match(r'^(\$?[\d,]+\.?\d*)$', part.strip())
                            if value_match:
                                values.append(value_match.group(1))
                        
                        if values:
                            # For multi-quarter tables, try to match with correct quarter
                            # based on citation context or use the most recent (last) value
                            value_to_use = values[-1] if values else None  # Default to most recent
                            
                            # If we have quarter context in the citation, try to use that
                            if quarter_headers and len(values) == len(quarter_headers):
                                # Check if citation mentions a specific quarter
                                for q_idx, quarter in enumerate(quarter_headers):
                                    if quarter in cited_text and q_idx < len(values):
                                        value_to_use = values[q_idx]
                                        logger.debug(f"Matched quarter {quarter} to value {value_to_use}")
                                        break
                            
                            if value_to_use:
                                label = potential_label
                                value = value_to_use
                                logger.debug(f"Line {i} matched: label='{label}', value='{value}' from values: {values}")
                                # Validate that the value looks like a financial number
                                if re.match(r'^\$?[\d,]+\.?\d*$', value) and len(value) > 0:
                                    # For quarterly tables with "millions" context, format appropriately
                                    if 'million' in cited_text.lower() and not value.endswith('M'):
                                        value = f"${value}M"  # Add $ and M for millions
                                    elif value.replace('.', '').replace(',', '').isdigit() and len(value) > 2:
                                        # Numbers over 100 without suffix likely in millions
                                        try:
                                            if float(value.replace(',', '')) >= 100:
                                                value = f"${value}M"
                                        except:
                                            pass
                                    found_pairs.append(f"{label}: {value}")
                                    logger.info(f"📊 Found inline pair: {label}: {value}")
                                    continue
                else:
                    logger.debug(f"Line {i} no match: {line[:50]}")
                
                # Pattern 2: Check if this line has financial values separated by spaces
                # (e.g., "14.0    15.2    16.1    17.3" after "Interest Income")
                if re.search(r'^\s*[\d,]+\.?\d*\s+[\d,]+\.?\d*', line):
                    # This looks like a values-only line, check previous line for label
                    line_idx = lines.index(line)
                    if line_idx > 0:
                        prev_line = lines[line_idx - 1].strip()
                        # Check if previous line is a label (no numbers)
                        if prev_line and not re.search(r'[\d$]', prev_line) and not re.match(r'^[\d\sQ]+$', prev_line):
                            # Extract first value from current line
                            value_match = re.search(r'(\$?[\d,]+\.?\d*)', line)
                            if value_match:
                                value = value_match.group(1)
                                if 'M' in cited_text and not value.endswith('M'):
                                    value = f"${value}M"
                                found_pairs.append(f"{prev_line}: {value}")
                                logger.info(f"📊 Found vertical pair: {prev_line}: {value}")
            
            # If no inline pairs found, try label-on-next-line pattern
            if not found_pairs:
                for i, line in enumerate(lines):
                    # Match lines like "Current Debt" followed by "$29,823"
                    if i < len(lines) - 1:
                        label = line.strip()
                        next_line = lines[i + 1].strip()
                        if (label and not re.search(r'[\d$]', label) and 
                            re.search(r'\$?[\d,]+\.?\d*[BMK]?', next_line)):
                            # Found a label-value pair
                            value = re.search(r'\$?[\d,]+\.?\d*[BMK]?', next_line).group(0)
                            found_pairs.append(f"{label}: {value}")
                            logger.info(f"📊 Found vertical pair: {label}: {value}")
            
            # Return the first meaningful pair (skip headers)
            for pair in found_pairs:
                if not any(skip in pair.lower() for skip in ['quarter', 'q1', 'q2', 'q3', 'q4', '2024', '2025', '2023']):
                    return pair, True
            
            # If all pairs are quarters/years, return the first one anyway
            if found_pairs:
                return found_pairs[0], True
    
    # Pattern to find financial values with their immediate context
    # This matches currency values like $29,823 or 29,823M or $2.5B
    value_patterns = [
        # Currency with label before: "Current Debt: $29,823"
        r'([A-Za-z\s]+(?:Debt|Revenue|Income|Assets|Liabilities|Equity|Cash|Expenses?|Profit|Loss|Ratio|Rate|Margin|Growth|Sales|Costs?)):\s*(\$?[\d,]+\.?\d*[BMK]?)',
        # Currency with label after: "$29,823 (Current Debt)"
        r'(\$?[\d,]+\.?\d*[BMK]?)\s*\(([A-Za-z\s]+(?:Debt|Revenue|Income|Assets|Liabilities|Equity|Cash|Expenses?|Profit|Loss|Ratio|Rate|Margin|Growth|Sales|Costs?))\)',
        # Financial metric with colon: "Interest Income: 14.0"
        r'([A-Za-z][A-Za-z\s&\-,\.]+?):\s*(\$?[\d,]+\.?\d*)',
        # Percentage values: "ROE: 15.2%" or "Growth Rate: 12%"
        r'([A-Za-z\s]+(?:Rate|Ratio|Margin|Growth|ROE|ROA|ROI)):\s*([\d,]+\.?\d*%)',
        # Standalone currency values (last resort)
        r'(\$[\d,]+\.?\d*[BMK]?)',
        # Numbers with units: "12.5 million" or "2.3B" - but not across lines
        r'([\d,]+\.?\d*)\s+(million|billion|thousand|M(?![A-Za-z])|B(?![A-Za-z])|K(?![A-Za-z]))'
    ]
    
    # Try each pattern to find the most specific value
    best_match = None
    best_match_length = float('inf')
    
    for pattern in value_patterns:
        matches = list(re.finditer(pattern, cited_text, re.IGNORECASE | re.MULTILINE))
        for match in matches:
            full_match = match.group(0)
            logger.debug(f"Pattern matched: '{full_match}' with pattern: {pattern[:50]}...")
            
            # Skip if this is matching across line boundaries inappropriately
            if '\n' in full_match:
                logger.debug(f"Skipping multi-line match: {full_match}")
                continue
                
            # Prefer shorter, more specific matches
            if len(full_match) < best_match_length:
                best_match = full_match
                best_match_length = len(full_match)
                
                # For patterns with label:value structure, format nicely
                if match.lastindex >= 2:
                    label = match.group(1).strip()
                    value = match.group(2).strip()
                    # Clean up the label
                    label = re.sub(r'\s+', ' ', label)
                    best_match = f"{label}: {value}"
    
    if best_match:
        logger.info(f"📊 Extracted specific value from citation: '{best_match}' from text of length {len(cited_text)}")
        return best_match, True
    
    # If no specific value found, try to extract the first sentence or line
    # that contains a number
    lines = cited_text.split('\n')
    for line in lines:
        if re.search(r'\d', line) and len(line.strip()) < 150:
            logger.info(f"📊 Extracted line with number from citation: '{line.strip()}'")
            return line.strip(), True
    
    # Last resort: return first 100 characters
    truncated = cited_text[:97] + "..." if len(cited_text) > 100 else cited_text
    logger.warning(f"⚠️ Could not extract specific value from citation, truncating: '{truncated}'")
    return truncated, True


def calculate_specific_rects(cited_text: str, extracted_value: str, original_rects: List[Dict], page_number: int) -> List[Dict]:
    """
    Calculate new rects that cover only the extracted value within the original citation.
    
    Args:
        cited_text: The original full citation text
        extracted_value: The specific value extracted (e.g., "Interest Income: $900.0M")
        original_rects: The original rects covering the full citation
        page_number: The page number
        
    Returns:
        New rects covering only the extracted value
    """
    if not original_rects or not extracted_value:
        return []
    
    # Extract just the numeric part for searching
    numeric_match = re.search(r'(\d+\.?\d*)', extracted_value)
    if not numeric_match:
        return []
    
    search_text = numeric_match.group(1)
    
    # Find where the search text appears in the original citation
    lines = cited_text.split('\n')
    for line_idx, line in enumerate(lines):
        if search_text in line:
            # Found the line containing our value
            # Calculate approximate position within the table
            # This is a rough estimate based on text position
            
            # Split the line to find column position
            parts = re.split(r'\s+', line.strip())
            col_idx = -1
            for idx, part in enumerate(parts):
                if search_text in part:
                    col_idx = idx
                    break
            
            if col_idx >= 0 and len(parts) > 0:
                # Estimate horizontal position based on column index
                # Assuming even column spacing
                col_width_ratio = 1.0 / max(len(parts), 5)  # Assume max 5 columns
                x_offset_ratio = col_idx * col_width_ratio
                
                # Create a smaller rect around the specific value
                # Use the first original rect as a base
                base_rect = original_rects[0] if original_rects else {}
                
                if 'x1' in base_rect and 'width' in base_rect:
                    new_x1 = base_rect['x1'] + (base_rect['width'] * x_offset_ratio)
                    new_width = base_rect['width'] * col_width_ratio * 0.8  # Make it slightly smaller
                    
                    # Estimate vertical position based on line index
                    total_lines = len(lines)
                    y_offset_ratio = line_idx / max(total_lines, 1)
                    
                    if 'y1' in base_rect and 'height' in base_rect:
                        line_height = base_rect['height'] / max(total_lines, 1)
                        new_y1 = base_rect['y1'] + (line_height * line_idx)
                        new_height = line_height * 0.8  # Make it slightly smaller
                        
                        return [{
                            'x1': new_x1,
                            'y1': new_y1,
                            'x2': new_x1 + new_width,
                            'y2': new_y1 + new_height,
                            'width': new_width,
                            'height': new_height,
                            'pageNumber': page_number
                        }]
    
    return []


def process_citation_for_granularity(citation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single citation to improve its granularity.
    
    Args:
        citation: Citation dictionary with cited_text and other fields
        
    Returns:
        Modified citation dictionary with improved granularity
    """
    # Check for cited_text first, then fall back to text field
    cited_text = citation.get('cited_text', '') or citation.get('text', '')
    page_number = citation.get('start_page_number')
    original_rects = citation.get('rects', [])
    
    # Log the original citation text for debugging
    logger.info(f"📊 Original citation text ({len(cited_text)} chars): {cited_text[:200]}...")
    
    # Check if we have context from the message about what specific value is being referenced
    # This can help us extract the right value from a table
    message_context = citation.get('message_context', '')
    
    # Extract specific value
    new_text, was_modified = extract_specific_value_from_citation(cited_text, page_number)
    
    if was_modified:
        # Create a copy of the citation with modified text
        processed_citation = citation.copy()
        
        # Store both the display text and the original searchable text
        processed_citation['display_text'] = new_text  # What users see
        processed_citation['cited_text'] = cited_text  # Keep original for rect finding
        processed_citation['text'] = cited_text  # Also keep original for compatibility
        processed_citation['original_cited_text'] = cited_text  # Keep original for debugging
        processed_citation['was_processed'] = True
        
        # Keep the original rects - don't clear them!
        # The frontend will use these to highlight the area where the value was found
        # Clearing rects causes full page highlight which is not what we want
        if original_rects:
            # Try to calculate more specific rects
            new_rects = calculate_specific_rects(cited_text, new_text, original_rects, page_number)
            if new_rects:
                processed_citation['rects'] = new_rects
                logger.info(f"✅ Calculated specific rects for value: {len(new_rects)} rects")
            else:
                # Keep original rects instead of clearing
                logger.info(f"✅ Keeping original {len(original_rects)} rects for highlighting")
        
        # Extract just the numeric part that would exist in the PDF for searching
        numeric_match = re.search(r'(\d+\.?\d*)', new_text)
        if numeric_match:
            numeric_value = numeric_match.group(1)
            processed_citation['searchable_text'] = numeric_value
            logger.info(f"✅ Set searchable_text to: '{numeric_value}' for highlighting")
        
        logger.info(f"✅ Improved citation granularity: {len(cited_text)} chars -> {len(new_text)} chars")
        logger.info(f"✅ Extracted value: '{new_text}'")
        return processed_citation
    
    # Even if not modified, ensure cited_text field exists
    citation['cited_text'] = cited_text
    return citation


def process_citations_list(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process a list of citations to improve their granularity.
    
    Args:
        citations: List of citation dictionaries
        
    Returns:
        List of processed citations with improved granularity
    """
    processed_citations = []
    used_values = set()  # Track which values have been used to avoid duplicates
    
    # Group citations by their original text to detect when multiple citations
    # are referencing different parts of the same table
    citations_by_text = {}
    for i, citation in enumerate(citations):
        text = citation.get('cited_text', '')
        if text not in citations_by_text:
            citations_by_text[text] = []
        citations_by_text[text].append((i, citation))
    
    # Process each group
    for cited_text, citation_group in citations_by_text.items():
        if len(citation_group) > 1:
            # Multiple citations from same table - need to ensure each gets a unique value
            logger.info(f"📊 Found {len(citation_group)} citations from same table/text block")
            
            # For tables, we need to distribute values across citations
            # First, extract all possible label-value pairs from the table
            lines = cited_text.strip().split('\n')
            all_pairs = []
            
            if len(lines) > 3:  # Likely a table
                # Extract all label-value pairs using same logic as extract_specific_value_from_citation
                for i, line in enumerate(lines):
                    parts = re.split(r'\s{2,}|\t', line)
                    if len(parts) >= 2:
                        potential_label = parts[0].strip()
                        if re.search(r'[A-Za-z]', potential_label) and not re.match(r'^[\d\s\.\-\$]+$', potential_label):
                            values = []
                            for part in parts[1:]:
                                value_match = re.match(r'^(\$?[\d,]+\.?\d*)$', part.strip())
                                if value_match:
                                    values.append(value_match.group(1))
                            
                            if values:
                                # Use the last (most recent) value by default
                                value = values[-1]
                                if 'million' in cited_text.lower() and not value.endswith('M'):
                                    value = f"${value}M"
                                elif value.replace('.', '').replace(',', '').isdigit() and len(value) > 2:
                                    try:
                                        if float(value.replace(',', '')) >= 100:
                                            value = f"${value}M"
                                    except:
                                        pass
                                pair = f"{potential_label}: {value}"
                                all_pairs.append(pair)
                                logger.debug(f"📊 Extracted pair: {pair}")
            
            # Now assign unique pairs to each citation
            for idx, (orig_idx, citation) in enumerate(citation_group):
                if idx < len(all_pairs) and all_pairs[idx] not in used_values:
                    # Assign a unique pair to this citation
                    processed = citation.copy()
                    processed['cited_text'] = all_pairs[idx]
                    processed['original_cited_text'] = cited_text
                    processed['was_processed'] = True
                    used_values.add(all_pairs[idx])
                    processed_citations.append((orig_idx, processed))
                    logger.info(f"✅ Assigned unique value to citation {idx+1}/{len(citation_group)}: '{all_pairs[idx]}'")
                else:
                    # Fallback to normal processing
                    processed = process_citation_for_granularity(citation)
                    # Ensure we don't reuse the same value
                    if processed.get('cited_text') in used_values and processed.get('was_processed'):
                        # Try to find an alternative value
                        logger.warning(f"⚠️ Value already used: '{processed.get('cited_text')}', keeping original")
                        processed = citation  # Keep original
                    else:
                        used_values.add(processed.get('cited_text', ''))
                    processed_citations.append((orig_idx, processed))
        else:
            # Single citation - process normally
            orig_idx, citation = citation_group[0]
            processed = process_citation_for_granularity(citation)
            used_values.add(processed.get('cited_text', ''))
            processed_citations.append((orig_idx, processed))
    
    # Sort by original index to maintain order
    processed_citations.sort(key=lambda x: x[0])
    final_citations = [citation for _, citation in processed_citations]
    
    # Log summary
    total = len(citations)
    modified = sum(1 for c in final_citations if c.get('was_processed', False))
    
    if total > 0:
        logger.info(f"📊 Citation processing summary: {modified}/{total} citations improved ({modified/total*100:.1f}%)")
    
    return final_citations