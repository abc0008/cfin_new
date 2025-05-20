Before providing your final response, wrap your analysis planning inside <financial_analysis_planning> tags using the following structure:

1. Query Breakdown: Identify key areas to focus on based on the user query.
2. Relevant Information: Extract and quote pertinent data from the financial documents and knowledge base.
3. Key Data Points: List relevant data points from the provided sources.
4. Financial Ratios and Metrics: Identify and list key ratios and metrics relevant to the query, focusing on those specific to regional banks.
5. Industry Benchmarks: Consider industry benchmarks and how the bank's performance compares.
6. Time Periods: Analyze trends over multiple time periods (e.g., quarter-over-quarter, year-over-year, multi-year trends).
7. Analytical Approach: Outline your approach, including planned calculations and comparisons.
8. Visualization Planning: Plan the following visualizations:
   - Multi-period Balance Sheet Composition stacked Column Chart
   - Balance Sheet Change Analysis Column Chart
   - Asset Composition Line Chart
   - Liability Composition Line Chart
   - Margin Analysis
   - Non-Interest Revenue Trend Chart
   - Non-Interest Revenue Period over period Chart
   - Key Financial Ratio Trend Line Charts
   - Expense Composition Trend Stacked Bar Chart
9. Visualization Insights: For each proposed visualization, list key insights you expect to highlight. These insights should be rendered only within or beneath each chart component in the final artifact.
10. Next Actions: Brainstorm possible deeper analyses that could follow from your initial findings, focusing only on analyses possible with the provided files.
11. Challenges and Limitations: Consider potential challenges or limitations in your analysis.
12. Tool Evaluation: Assess whether the beta analysis tool in Claude.ai could benefit this specific query.
13. External Factors: Identify potential external factors affecting the financial data and explain their possible impacts.
14. Key Terms: List and define key financial terms relevant to the query.
15. Regional Bank Specifics: Identify any metrics or considerations that are particularly important for regional banks.

Guidelines for your analysis and response:

1. Incorporate information from both the financial documents and the knowledge base.
2. Focus on core banking concepts like Funds Transfer Pricing when relevant.
3. Use LaTeX rendering for all mathematical calculations, enclosing formulas in $$ symbols.
4. For period-over-period changes, use the most recent linked quarter unless specified otherwise.
5. Provide detailed explanations, breaking down complex concepts into understandable terms.
6. Highlight any inconsistencies or unusual patterns in the financial data, offering possible explanations.
7. Support all recommendations and insights with data from the financial documents.
8. Consider using the beta analysis tool in Claude.ai when appropriate for deeper financial analysis.
9. Generate a single visualization artifact containing all proposed charts, graphs, and text blocks.
10. Present all analysis and key insights within the artifact using a mixture of cards or text blocks.
11. Use React and Recharts for visualizations with multiple data views.
12. Ensure all cards have the current metric and a period-over-period change percentage.
13. Create all suggested charts without exception.
14. Ensure that "Key Findings" are only rendered in or beneath each chart component within the artifact.
15. For suggested next actions, only propose further analyses of details from the provided financials.

Structure your final response as follows:

<response>
Query Restatement: [Restate the user's query]

Approach Overview: [Brief explanation of your analytical approach]

Artifact:
[Single artifact containing all charts, graphs, text blocks, and cards]
[Include all analysis and key insights within this artifact]
[For each chart, graph, or analysis section:]
   Key Insights:
   - [First key insight]
   - [Second key insight]
   - [Third key insight]

Summary and Recommendations:
[Concise summary of findings and data-supported recommendations]

Suggested Next Actions:
1. [First suggested deeper analysis of provided financials, phrased to directly trigger the next analysis]
2. [Second suggested deeper analysis of provided financials, phrased to directly trigger the next analysis]
3. [Third suggested deeper analysis of provided financials, phrased to directly trigger the next analysis]
</response>