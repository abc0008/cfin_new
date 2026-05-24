"""
Citation instruction utilities for guiding Claude to create granular citations.
"""

GRANULAR_CITATION_INSTRUCTIONS = """
CITATION GUIDELINES:
When citing information from documents, follow these critical rules:

1. **BE SPECIFIC AND GRANULAR**: 
   - Cite individual values, not entire tables or sections
   - For example, cite "$29,823" instead of the entire debt table
   - When referencing a metric, cite just that number and its label

2. **CITE AT THE VALUE LEVEL**:
   - Good: "Current Debt: $29,823"
   - Bad: "As of 12/31/2023 ($ in millions) Current Debt Long-term Debt Total Debt..."
   
3. **MULTIPLE SPECIFIC CITATIONS**:
   - If discussing multiple values from the same table, create separate citations for each
   - Each financial figure should have its own citation
   
4. **CONTEXT IN CITATIONS**:
   - Include minimal context (metric name + value)
   - Example: "Net Revenue: $2.5B" not the entire income statement
   
5. **CITATION PLACEMENT**:
   - Place citations immediately after mentioning specific values
   - Don't wait until the end of a paragraph to cite

6. **NUMBER-FIRST SELECTION**:
   - When choosing what to cite, prioritize concrete numeric financial data: dollar amounts, percentages, ratios, EPS, counts, and basis points
   - Do not cite purely narrative sentences, section headers, or qualitative commentary unless no numeric source exists for that claim
   - Each cited block should contain at least one numeric token the user can highlight in the PDF

7. **TABLE SOURCE PREFERENCE**:
   - When the same figure appears in narrative text and a financial table, cite the table cell using "Row label: value" (e.g., "Net sales: $997.7 million")
   - If multiple table cells are relevant, create separate citations for each value rather than citing the table header or an entire row string
   - Source priority when the same number appears in multiple places: table cell > chart label > narrative mention

Remember: Users want to highlight specific numbers in the PDF, not entire pages or tables. Your citations should be surgical, numeric, and table-sourced when possible.
"""

def enhance_system_prompt_with_citation_instructions(base_prompt: str) -> str:
    """
    Enhance a system prompt with granular citation instructions.
    
    Args:
        base_prompt: The original system prompt
        
    Returns:
        Enhanced prompt with citation instructions
    """
    # Check if citation instructions already exist
    if "CITATION GUIDELINES" in base_prompt:
        return base_prompt
        
    # Add citation instructions after the main instructions
    return base_prompt + "\n\n" + GRANULAR_CITATION_INSTRUCTIONS