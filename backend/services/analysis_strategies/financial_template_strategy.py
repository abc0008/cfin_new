import json
import logging
from typing import List, Dict, Any, Optional
import re # Added for PlanPlanPlan.md item 1.2
from importlib.resources import files # Added for this change

from models.analysis import FinancialMetric
from .base_strategy import AnalysisStrategy
from pdf_processing.api_service import ClaudeService
from models.database_models import Document
from models.visualization import ChartData, TableData
from utils import tool_processing

logger = logging.getLogger(__name__)

# Added for PlanPlanPlan.md item 1.2
REQUIRED_CHARTS = {
    'multi-period balance sheet composition stacked column',
    'balance sheet change analysis column',
    'asset composition line',
    'liability composition line',
    'margin analysis',
    'non-interest revenue trend',
    'non-interest revenue period over period',
    'key financial ratio trend line',
    'expense composition trend stacked bar',
}

def extract_between_tags(text: str, tag: str) -> str:
    # import re # No need to import re again if already at top level
    match = re.search(
        rf'<{tag}>(.*?)</{tag}>',
        text,
        flags=re.DOTALL | re.IGNORECASE  # DOTALL + case-insensitive
    )
    return (match.group(1) if match else '').strip()

# FINANCIAL_ANALYSIS_TEMPLATE_PROMPT was moved to a separate .md file
# backend/services/analysis_strategies/prebuilt_prompts/financial_template_prompt.md

<financial_documents>
{document_text}
</financial_documents>

<knowledge_base>
{KNOWLEDGE_BASE}
</knowledge_base>

Now, analyze the following user query:

<user_query>
{USER_QUERY}
</user_query>

Before providing your final response, wrap your analysis planning inside <financial_analysis_planning> tags using the following structure:

1. Query Breakdown: Identify key areas to focus on based on the user query.
2. Relevant Information: Extract and quote pertinent data from the financial documents and knowledge base.
3. Key Data Points: List relevant data points from the provided sources.
4. Financial Ratios and Metrics: Identify and list key ratios and metrics relevant to the query, focusing on those specific to regional banks.
5. Industry Benchmarks: Consider industry benchmarks and how the bank\'s performance compares.
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
Query Restatement: [Restate the user\'s query]

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

class FinancialTemplateStrategy(AnalysisStrategy):
    """
    Strategy for financial analysis using a predefined template and multi-turn interaction.
    Encapsulates the logic previously handling the \'financial_template\' type directly.
    """
    PROMPT_PATH = files('services.analysis_strategies').joinpath('prebuilt_prompts/financial_template_prompt.md') # Added for this change
    FINANCIAL_ANALYSIS_TEMPLATE_PROMPT_FROM_FILE = PROMPT_PATH.read_text(encoding='utf-8') # Added for this change

    def __init__(self, claude_service: ClaudeService):
        super().__init__(claude_service)
        self.max_turns = 9
        self.planning_verified = False # Added for PlanPlanPlan.md item 1.2
        # Ensure the prompt is loaded during initialization
        if not FinancialTemplateStrategy.FINANCIAL_ANALYSIS_TEMPLATE_PROMPT_FROM_FILE:
            logger.error("Financial template prompt could not be loaded.")
            raise ValueError("Financial template prompt could not be loaded.")


    async def execute(
        self,
        aggregated_text: str,
        documents: List[Document],
        parameters: Dict[str, Any],
        user_query: Optional[str],
        pdf_base64_contents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        logger.info(f"Executing FinancialTemplateStrategy for query: \'{user_query}\'")

        user_query_for_template = user_query or parameters.get("query", "Provide a comprehensive financial analysis.")
        knowledge_base_content = parameters.get("knowledge_base", "")

        system_prompt = FinancialTemplateStrategy.FINANCIAL_ANALYSIS_TEMPLATE_PROMPT_FROM_FILE.format(
            document_text=aggregated_text,
            KNOWLEDGE_BASE=knowledge_base_content,
            USER_QUERY=user_query_for_template
        )
        
        conversation_messages = [{"role": "user", "content": user_query_for_template}]
        
        accumulated_text = ""
        accumulated_charts: List[ChartData] = []
        accumulated_tables: List[TableData] = []
        accumulated_metrics: List[FinancialMetric] = []

        for turn in range(self.max_turns):
            logger.info(f"FinancialTemplateStrategy - Turn {turn + 1}/{self.max_turns}")

            if not hasattr(self.claude_service, 'execute_tool_interaction_turn'):
                logger.error("ClaudeService.execute_tool_interaction_turn is not available.")
                return {
                    "analysis_text": "Error: ClaudeService.execute_tool_interaction_turn not implemented.",
                    "visualizations": {"charts": [], "tables": []},
                    "metrics": []
                }
            
            tools_for_api_call = self.claude_service.tools_for_api

            api_response = await self.claude_service.execute_tool_interaction_turn(
                system_prompt=system_prompt,
                messages=conversation_messages,
                tools=tools_for_api_call,
            )

            assistant_response_content_blocks = []
            assistant_text_this_turn = "" # To capture text for planning guard
            if api_response.content:
                for block in api_response.content:
                    if block.type == "text":
                        accumulated_text += block.text + "\n"
                        assistant_text_this_turn += block.text # Capture for planning guard
                        assistant_response_content_blocks.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        assistant_response_content_blocks.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input
                        })
            
            if assistant_response_content_blocks:
                conversation_messages.append({"role": "assistant", "content": assistant_response_content_blocks})
                
                # Planning Guard Logic from PlanPlanPlan.md item 1.2
                if not self.planning_verified and '<financial_analysis_planning' in assistant_text_this_turn.lower():
                    plan_txt = extract_between_tags(assistant_text_this_turn, 'financial_analysis_planning').lower()
                    missing_charts = [chart_name for chart_name in REQUIRED_CHARTS if chart_name not in plan_txt]
                    if missing_charts:
                        logger.info(f"Planning guard: Missing charts in plan: {missing_charts}")
                        # Append a user message to request missing charts
                        conversation_messages.append({
                            'role': 'user',
                            'content': (
                                "Great start on the plan! Please update your plan to explicitly include these visualizations: "
                                f"{', '.join(missing_charts)}."
                            ),
                        })
                        # Potentially continue to the next turn to let Claude update the plan
                        # The current loop structure will send this new user message in the next iteration.
                    else:
                        logger.info("Planning guard: All required charts found in the plan.")
                        self.planning_verified = True
            elif api_response.stop_reason != 'tool_use':
                 logger.warning(f"FinancialTemplateStrategy: Assistant response empty, stop_reason not tool_use: {api_response.stop_reason}")

            tool_results_for_this_turn = []
            if api_response.stop_reason == "tool_use" and api_response.content:
                for block in api_response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id
                        logger.info(f"FinancialTemplateStrategy: Processing tool {tool_name} (ID: {tool_use_id})")
                        try:
                            if not hasattr(self.claude_service, '_process_visualization_input'):
                                logger.error("ClaudeService._process_visualization_input is not available.")
                                raise NotImplementedError("ClaudeService._process_visualization_input needed for tool processing.")

                            processed_data = tool_processing.process_visualization_input(tool_name, tool_input, tool_use_id)
                            if processed_data:
                                if tool_name == "generate_graph_data":
                                    accumulated_charts.append(ChartData(**processed_data) if isinstance(processed_data, dict) else processed_data)
                                elif tool_name == "generate_table_data":
                                    accumulated_tables.append(TableData(**processed_data) if isinstance(processed_data, dict) else processed_data)
                                elif tool_name == "generate_financial_metric":
                                    accumulated_metrics.append(FinancialMetric(**processed_data) if isinstance(processed_data, dict) else processed_data)
                                
                                tool_results_for_this_turn.append({
                                    "type": "tool_result", "tool_use_id": tool_use_id,
                                    "content": json.dumps(processed_data)
                                })
                            else:
                                logger.warning(f"Tool {tool_name} (ID: {tool_use_id}) processed but returned no data.")
                                tool_results_for_this_turn.append({
                                    "type": "tool_result", "tool_use_id": tool_use_id,
                                    "content": "Error: Tool processing yielded no data.", "is_error": True
                                })
                        except Exception as e:
                            logger.error(f"Error processing tool {tool_name} (ID: {tool_use_id}): {e}", exc_info=True)
                            tool_results_for_this_turn.append({
                                "type": "tool_result", "tool_use_id": tool_use_id,
                                "content": f"Error during tool execution: {str(e)}", "is_error": True
                            })
                
                if tool_results_for_this_turn:
                    conversation_messages.append({"role": "user", "content": tool_results_for_this_turn})
                else:
                    logger.warning("FinancialTemplateStrategy: stop_reason tool_use but no tool results. Appending generic message.")
                    conversation_messages.append({"role": "user", "content": [{"type": "text", "text": "Tool processing phase completed with no specific tool outputs generated in this turn. Please proceed."}]})

            if api_response.stop_reason in ["stop_sequence", "end_turn"]:
                logger.info(f"FinancialTemplateStrategy finished: {api_response.stop_reason}")
                break
            if turn == self.max_turns - 1:
                logger.warning(f"FinancialTemplateStrategy reached max turns ({self.max_turns}).")
                break
        
        return {
            "analysis_text": accumulated_text.strip(),
            "visualizations": {
                "charts": accumulated_charts,
                "tables": accumulated_tables
            },
            "metrics": accumulated_metrics
        } 