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

Remember: Users want to highlight specific numbers in the PDF, not entire pages or tables. Your citations should be surgical and precise.
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