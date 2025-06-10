"""
Comprehensive Financial Analysis Strategy

This module implements the most thorough financial analysis strategy, providing detailed
multi-turn analysis with extensive visualizations, metrics, and insights. It uses the
most sophisticated prompts and allows for complex analytical workflows.

Upstream Dependencies:
- base_strategy.AnalysisStrategy: Abstract base class defining strategy interface
- models.database_models.Document: Document entity model
- models.visualization.ChartData/TableData: Visualization data models
- models.analysis.FinancialMetric: Financial metric data model
- pdf_processing.api_service.ClaudeService: Core Claude API service
- utils.tool_processing: Shared tool processing utilities for visualization generation

Downstream Dependencies:
- Invoked by services.analysis_service.AnalysisService when analysis_type="comprehensive"
- Results consumed by API endpoints in app.routes.analysis.py
- Rich visualization data rendered by frontend chart components
- Used for the most detailed financial analysis reports requiring multiple charts/tables

Key Features:
- Extended multi-turn conversation flow (max 7 turns) for complex analysis
- Comprehensive system prompt loaded from external file for maintainability
- Advanced tool processing for generating multiple visualization types
- Accumulates extensive text, charts, tables, and metrics across conversation turns
- Designed for high-value, detailed financial analysis use cases
- Supports both PDF and text-based document analysis

Analysis Flow:
1. Load comprehensive analysis prompt from external template
2. Initialize multi-turn conversation with user query and document context
3. Execute up to 7 turns of Claude interaction with tool support
4. Process visualization tools (charts, tables, metrics) at each turn
5. Accumulate rich analysis content across all conversation turns
6. Return comprehensive structured results with extensive visualizations
"""

import json
from typing import List, Dict, Any, Optional
import logging
from importlib.resources import files # Added for PlanPlanPlan.md item 1.1

from .base_strategy import AnalysisStrategy
from pdf_processing.api_service import ClaudeService # Removed ALL_TOOLS_DICT import
# ALL_TOOLS_DICT is no longer directly used here for passing to execute_tool_interaction_turn
# from pdf_processing.claude_service import ClaudeService, ALL_TOOLS_DICT
from models.database_models import Document
from models.visualization import ChartData, TableData
from models.analysis import FinancialMetric
from utils import tool_processing # Added for Story #9

logger = logging.getLogger(__name__)

# Updated for PlanPlanPlan.md item 1.1 and user-provided path
PROMPT_PATH = files('services.analysis_strategies').joinpath(
    'prebuilt_prompts/Claude Financial Analysis Prompt.md'
)
COMPREHENSIVE_SYSTEM_PROMPT: str = PROMPT_PATH.read_text(encoding='utf-8')

class ComprehensiveAnalysisStrategy(AnalysisStrategy):
    """
    Strategy for performing comprehensive financial analysis using a multi-turn approach.
    """

    def __init__(self, claude_service: ClaudeService):
        super().__init__(claude_service)
        # Max turns specific to this strategy, as per AC for Story #6 (Loops ≤7 turns)
        self.max_turns = 7 

    async def execute(
        self,
        aggregated_text: str,
        documents: List[Document],
        parameters: Dict[str, Any],
        user_query: Optional[str],
        pdf_base64_contents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        logger.info(f"Executing ComprehensiveAnalysisStrategy for query: '{user_query}'")

        initial_user_message_content = aggregated_text
        if user_query:
            initial_user_message_content = f"User Query: {user_query}\n\nDocument Text:\n{aggregated_text}"
        
        # Consider adding PDF base64 content to the initial message if provided and claude_service supports it
        # For now, assuming text-based interaction primarily for this example structure.
        # If pdf_base64_contents is used, it would typically be part of a multi-modal message.
        # Example: conversation_messages = [{"role": "user", "content": [{"type": "text", "text": initial_user_message_content}] + [{"type": "image", ...} for pdf_content in pdf_base64_contents]}]
        # This part depends on how ClaudeService and execute_tool_interaction_turn handle multi-modal inputs.
        # The base_strategy signature includes pdf_base64_contents, so it should be handled or acknowledged.
        
        conversation_messages = [{"role": "user", "content": initial_user_message_content}]
        
        accumulated_text = ""
        accumulated_charts: List[ChartData] = []
        accumulated_tables: List[TableData] = []
        accumulated_metrics: List[FinancialMetric] = []

        for turn in range(self.max_turns):
            logger.info(f"ComprehensiveAnalysisStrategy - Turn {turn + 1}/{self.max_turns}")

            if not hasattr(self.claude_service, 'execute_tool_interaction_turn'):
                logger.error("ClaudeService.execute_tool_interaction_turn is not available.")
                # Fallback or error, for now, let's simulate an empty response or error structure
                return {
                    "analysis_text": "Error: ClaudeService.execute_tool_interaction_turn not implemented.",
                    "visualizations": {"charts": [], "tables": []},
                    "metrics": []
                }

            # Ensure ALL_TOOLS_DICT is available. It might be better to pass it from AnalysisService
            # or ensure ClaudeService provides access to it if it's not globally available here.
            # tools_to_use = getattr(self.claude_service, 'ALL_TOOLS_DICT', ALL_TOOLS_DICT) # Defensive
            # Use tools_for_api from claude_service instance, which is CLAUDE_API_TOOLS_LIST
            tools_for_api_call = self.claude_service.tools_for_api
            
            api_response = await self.claude_service.execute_tool_interaction_turn(
                system_prompt=COMPREHENSIVE_SYSTEM_PROMPT,
                messages=conversation_messages,
                tools=tools_for_api_call, # Pass the correct list of dicts
                # temperature=0.3, # Optional: can be set here or in ClaudeService
                # max_tokens=4096   # Optional: can be set here or in ClaudeService
            )

            assistant_response_content_blocks = []
            if api_response.content:
                for block in api_response.content:
                    if block.type == "text":
                        accumulated_text += block.text + "\n"
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
            elif api_response.stop_reason != 'tool_use':
                logger.warning(f"ComprehensiveStrategy: Assistant response empty, stop_reason not tool_use: {api_response.stop_reason}")

            tool_results_for_this_turn = []
            if api_response.stop_reason == "tool_use" and api_response.content:
                for block in api_response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id
                        logger.info(f"ComprehensiveStrategy: Processing tool {tool_name} (ID: {tool_use_id})")
                        try:
                            if not hasattr(self.claude_service, '_process_visualization_input'):
                                logger.error("ClaudeService._process_visualization_input is not available.")
                                raise NotImplementedError("ClaudeService._process_visualization_input needed for tool processing.")
                            
                            processed_data = tool_processing.process_visualization_input(tool_name, tool_input, tool_use_id)
                            if processed_data:
                                if tool_name == "generate_graph_data":
                                    # Already returns a dict from process_visualization_input
                                    accumulated_charts.append(processed_data)
                                elif tool_name == "generate_table_data":
                                    # Already returns a dict from process_visualization_input
                                    accumulated_tables.append(processed_data)
                                elif tool_name == "generate_financial_metric":
                                    # Already returns a dict from process_visualization_input
                                    accumulated_metrics.append(processed_data)
                                
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
                    logger.warning("ComprehensiveStrategy: stop_reason tool_use but no tool results. Appending generic message.")
                    conversation_messages.append({"role": "user", "content": [{"type": "text", "text": "Tool processing phase completed with no specific tool outputs generated in this turn. Please proceed."}]})

            if api_response.stop_reason in ["stop_sequence", "end_turn"]:
                logger.info(f"ComprehensiveAnalysisStrategy finished: {api_response.stop_reason}")
                break
            if turn == self.max_turns - 1:
                logger.warning(f"ComprehensiveAnalysisStrategy reached max turns ({self.max_turns}).")
                break
        
        return {
            "analysis_text": accumulated_text.strip(),
            "visualizations": {
                "charts": accumulated_charts,
                "tables": accumulated_tables
            },
            "metrics": accumulated_metrics
        } 