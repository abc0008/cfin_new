"""
Citation and financial metric instruction utilities for guiding Claude during analysis.
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
   - Default to financial tables over narrative sentences when both contain the same figure
   - Scan tabular sources first (KPI tables, summary financials, capital/ratio tables, loan/deposit schedules) before citing prose that repeats the same number
   - When the same figure appears in narrative text and a financial table, cite the table cell using "Row label: value" (e.g., "Net sales: $997.7 million")
   - If multiple table cells are relevant, create separate citations for each value rather than citing the table header or an entire row string
   - Source priority when the same number appears in multiple places: table cell > chart label > narrative mention
   - Use narrative sentences for citations only when no table or chart source exists for that value

Remember: Users want to highlight specific numbers in the PDF, not entire pages or tables. Your citations should be surgical, numeric, and table-sourced when possible.
"""

BANKING_METRIC_FORMAT_INSTRUCTIONS = """
BANKING METRIC FORMATTING:
When stating, citing, or emitting financial metrics in analysis text, citations, generate_financial_metric, generate_table_data, or generate_graph_data, use consistent precision:

- **Rates / yields / margins / capital ratios (as %)**: two decimal places (e.g., 4.25%, 12.37%, CET1 ratio 11.04%)
- **Basis points**: integer when whole (e.g., 125 bps); two decimals when fractional (e.g., 12.50 bps). Do not express the same figure as both bps and %
- **Dollar balances** (loans, deposits, assets, revenue, net income, allowance): match the document's unit scale ($, $M, $B, or "in millions/thousands") and decimal precision from the source table (e.g., $997.7M, $29,823)
- **Per-share amounts** (EPS, tangible book value per share): two decimals with $ prefix (e.g., $1.27)
- **Counts** (accounts, branches, FTEs, loan/deposit accounts): integers; use thousands separators at 1,000+ (e.g., 1,245,000)
- **Multiples** (P/E, price/tangible book): two decimals with "x" suffix (e.g., 14.25x)
- **Credit / allowance metrics** (NCO rate, ALLL ratio, charge-off rate): two decimal % (e.g., 0.42%, 1.05%)
- **Spreads** (NIM, loan yield minus cost of funds): two decimal % or bps per document convention; stay consistent within a response
- **Period labels**: match the source (Q3 2024, FY 2023, 12/31/2023, nine months ended 9/30/2024)

For cited_text, use the formatted "Row label: value" string with the same precision you use in the narrative. Prefer the table cell's formatting when table-sourced.
"""

VISUALIZATION_TOOL_OUTPUT_INSTRUCTIONS = """
VISUALIZATION TOOL OUTPUT (CHAT & ADHOC ANALYSIS):
These rules apply whenever you emit charts, tables, or metric cards via tools during conversational chat or adhoc document analysis — not only batch analysis runs.

**Source data**: Prefer financial table cells over narrative sentences when populating tool inputs. Do not round or restate approximations from prose when an exact table value exists.

**generate_financial_metric (metric cards)**:
- Keep `value` numeric; put scale/symbol in `unit` (e.g., value: 4.25, unit: "%"; value: 997.7, unit: "$M")
- Rates/yields/margins: two decimal precision with unit "%"
- Dollar balances: match document scale in unit and value precision
- EPS / per-share: two decimals; unit "$" or "$/share"

**generate_table_data (tables)**:
- Set each column's `format`: `percentage` for rates/margins/ratios, `currency` for dollar amounts, `number` for counts and multiples, `text` for labels/periods
- Cell values should match source-table precision (do not pad rates to whole numbers or truncate cents on balances)
- Comparison and trend tables should use period labels consistent with the document

**generate_graph_data (charts)**:
- Series values in `data` must use the same precision as the source table
- In `chartConfig`, set `unit`, `precision` (typically 2 for rates and scaled currency, 0 for integer counts), and `formatter` when applicable (`percentage`, `currency`, `number`)
- Axis labels and config titles should reflect units ($M, %, bps) when relevant
- Time-series charts should use table-sourced period columns, not paraphrased narrative dates
"""

VISUALIZATION_TOOL_FORMAT_SUFFIX = (
    "\n\nBanking output rules: prefer table-sourced values; rates/yields/margins to 2 decimal %; "
    "balances at document scale; set table column format (percentage/currency/number) and chartConfig "
    "unit/precision/formatter accordingly; keep metric card value numeric with unit separate."
)

FINANCIAL_AGENT_INSTRUCTIONS = (
    GRANULAR_CITATION_INSTRUCTIONS.strip()
    + "\n\n"
    + BANKING_METRIC_FORMAT_INSTRUCTIONS.strip()
    + "\n\n"
    + VISUALIZATION_TOOL_OUTPUT_INSTRUCTIONS.strip()
    + "\n"
)


def enhance_system_prompt_with_citation_instructions(base_prompt: str) -> str:
    """
    Enhance a system prompt with citation and banking metric formatting instructions.

    Args:
        base_prompt: The original system prompt

    Returns:
        Enhanced prompt with financial agent instructions
    """
    has_citation_guidelines = "CITATION GUIDELINES" in base_prompt
    has_metric_formatting = "BANKING METRIC FORMATTING" in base_prompt
    has_visualization_output = "VISUALIZATION TOOL OUTPUT" in base_prompt

    if has_citation_guidelines and has_metric_formatting and has_visualization_output:
        return base_prompt

    additions = []
    if not has_citation_guidelines:
        additions.append(GRANULAR_CITATION_INSTRUCTIONS.strip())
    if not has_metric_formatting:
        additions.append(BANKING_METRIC_FORMAT_INSTRUCTIONS.strip())
    if not has_visualization_output:
        additions.append(VISUALIZATION_TOOL_OUTPUT_INSTRUCTIONS.strip())

    return base_prompt + "\n\n" + "\n\n".join(additions) + "\n"
