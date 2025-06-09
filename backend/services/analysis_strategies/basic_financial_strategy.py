import logging
import json
from typing import List, Dict, Any, Optional

from importlib.resources import files
from fastapi import HTTPException
from anthropic.types import Message # Assuming Message is used for api_response type

from models.analysis import FinancialMetric # For collected_metrics
from models.visualization import ChartData, TableData # For collected_charts, collected_tables
from models.database_models import Document # For documents parameter
from pdf_processing.api_service import ClaudeService # For self.claude_service
from .base_strategy import AnalysisStrategy
from utils.exceptions import ToolSchemaValidationError
from settings import MODEL_HAIKU # For model override in multi-turn

logger = logging.getLogger(__name__)

class BasicFinancialStrategy(AnalysisStrategy):
    """
    Strategy for basic financial analysis.
    This strategy replicates the logic previously in AnalysisService for "basic_financial" type.
    """
    PROMPT_PATH = files('services.analysis_strategies').joinpath('prebuilt_prompts/basic_financial_prompt.md')
    LOADED_PROMPT = PROMPT_PATH.read_text(encoding='utf-8')

    def __init__(self, claude_service: ClaudeService):
        super().__init__(claude_service)
        if not BasicFinancialStrategy.LOADED_PROMPT:
            logger.error("Basic financial prompt could not be loaded.")
            raise ValueError("Basic financial prompt could not be loaded.")

    async def execute(
        self,
        aggregated_text: str, # Text from documents if PDFs are not used directly
        documents: List[Document], # List of Document objects
        parameters: Dict[str, Any], # Additional parameters
        user_query: Optional[str], # User's query
        pdf_base64_contents: Optional[List[str]] = None # Base64 encoded PDF contents
    ) -> Dict[str, Any]:
        logger.info(f"Executing BasicFinancialStrategy for query: '{user_query}'")

        # Build initial message with PDF content using Claude's native PDF support
        content_blocks = []

        if pdf_base64_contents:
            logger.info(f"Using {len(pdf_base64_contents)} PDF documents with Claude's native PDF support")
            for pdf_base64 in pdf_base64_contents: # Iterate through all provided PDFs
                content_blocks.append({
                    "type": "document", # Changed from "image" to "document" for PDFs
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf", # Correct media type for PDF
                        "data": pdf_base64
                    }
                })
            prompt_text = "Please analyze the financial documents provided above."
            if user_query:
                prompt_text += f"\n\nUser query: {user_query}"
            content_blocks.append({"type": "text", "text": prompt_text})
        else:
            logger.warning("No PDF content available, falling back to aggregated text")
            # Ensure aggregated_text is not empty, provide a default if it is.
            current_text_content = aggregated_text if aggregated_text else "No document content available to analyze."
            content_blocks.append({"type": "text", "text": current_text_content})
            if user_query: # Append user query if it exists
                content_blocks.append({"type": "text", "text": f"User query: {user_query}"})

        current_messages: List[Dict[str, Any]] = [
            {"role": "user", "content": content_blocks}
        ]

        final_assistant_responses_content: List[Dict[str, Any]] = []
        collected_charts: List[ChartData] = []
        collected_tables: List[TableData] = []
        collected_metrics: List[FinancialMetric] = []
        final_text_summary_parts: List[str] = []

        max_turns = 5  # Max turns to prevent infinite loops
        for turn in range(max_turns):
            logger.info(f"Basic financial analysis - Turn {turn + 1}/{max_turns}")
            try:
                model_for_this_turn_override = MODEL_HAIKU if turn > 0 else None
                log_msg = f"Basic financial analysis - Turn {turn + 1}: Using "
                log_msg += f"Haiku model ({MODEL_HAIKU})" if model_for_this_turn_override else "default model selection (expected Sonnet)"
                logger.info(log_msg)

                if not hasattr(self.claude_service, 'execute_tool_interaction_turn'):
                    logger.error("ClaudeService.execute_tool_interaction_turn is not available.")
                    # This matches how FinancialTemplateStrategy handles it
                    return {
                        "analysis_text": "Error: ClaudeService.execute_tool_interaction_turn not implemented.",
                        "visualizations": {"charts": [], "tables": []},
                        "metrics": []
                    }

                api_response: Message = await self.claude_service.execute_tool_interaction_turn(
                    system_prompt=BasicFinancialStrategy.LOADED_PROMPT,
                    messages=current_messages,
                    tools=self.claude_service.tools_for_api, # Assuming tools_for_api is prepared by ClaudeService
                    model_override=model_for_this_turn_override
                )

                # Ensure api_response.content is not None before processing
                if api_response.content is None:
                    logger.warning(f"API response content is None in turn {turn + 1}. Stop reason: {api_response.stop_reason}")
                    # Decide if to break or continue based on stop_reason or other conditions
                    if api_response.stop_reason not in ["tool_use", "stop_sequence", "end_turn"]: # if it's an unexpected stop
                         final_assistant_responses_content.append({"type": "text", "text": "No further content from assistant."}) # Add a placeholder if needed
                    break

                assistant_message_content_blocks = [block.model_dump() for block in api_response.content]
                current_messages.append({"role": "assistant", "content": assistant_message_content_blocks})

                tool_results_for_next_turn: List[Dict[str, Any]] = []
                contains_tool_use = any(block.type == 'tool_use' for block in api_response.content)

                for block in api_response.content:
                    if block.type == 'tool_use':
                        tool_name = block.name
                        tool_use_id = block.id
                        tool_input = block.input

                        logger.info(f"Assistant requested tool: {tool_name} (ID: {tool_use_id}) with input: {tool_input}")

                        processed_data_for_tool: Optional[Dict[str, Any]] = None
                        tool_output_content_for_claude = ""

                        # Use the shared tool processing logic from ClaudeService
                        # This assumes _process_visualization_input can be adapted or a similar method exists
                        # For now, let's replicate the direct processing logic
                        tool_schema = self.claude_service.tool_schemas_map.get(tool_name)
                        if tool_schema and tool_schema.processor:
                            try:
                                processed_data_for_tool = tool_schema.processor(tool_input)
                                if processed_data_for_tool is not None:
                                    if tool_name == "generate_graph_data":
                                        collected_charts.append(ChartData(**processed_data_for_tool))
                                    elif tool_name == "generate_table_data":
                                        collected_tables.append(TableData(**processed_data_for_tool))
                                    elif tool_name == "generate_financial_metric":
                                        collected_metrics.append(FinancialMetric(**processed_data_for_tool))
                                    tool_output_content_for_claude = json.dumps(processed_data_for_tool)
                                else:
                                    tool_output_content_for_claude = json.dumps({"status": "Tool processed, no output."})
                            except Exception as proc_e:
                                logger.error(f"Error processing tool {tool_name} (ID: {tool_use_id}): {proc_e}", exc_info=True)
                                tool_output_content_for_claude = json.dumps({"error": f"Failed to process tool {tool_name}: {str(proc_e)}"})
                        else:
                            logger.warning(f"No processor for tool {tool_name} (ID: {tool_use_id})")
                            tool_output_content_for_claude = json.dumps({"error": f"No processor for tool {tool_name}"})

                        tool_results_for_next_turn.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": tool_output_content_for_claude,
                        })
                    elif block.type == 'text':
                        # Text from intermediate assistant messages is not directly added to final summary here
                        # It's part of current_messages for context.
                        # Final text summary is built from the very last assistant message after loop.
                        pass

                if tool_results_for_next_turn:
                    current_messages.append({"role": "user", "content": tool_results_for_next_turn})

                if api_response.stop_reason == "stop_sequence" or not contains_tool_use:
                    logger.info(f"Basic financial analysis conversation loop finished in turn {turn + 1}. Stop Reason: {api_response.stop_reason}")
                    final_assistant_responses_content.extend(assistant_message_content_blocks)
                    break

                if turn == max_turns - 1:
                    logger.warning(f"Basic financial analysis reached max_turns ({max_turns}). Last assistant message content: {assistant_message_content_blocks}")
                    final_assistant_responses_content.extend(assistant_message_content_blocks)

            except ToolSchemaValidationError as tsve:
                logger.error(f"Tool schema validation error during BasicFinancialStrategy execution, turn {turn+1}: {tsve}", exc_info=True)
                error_detail = f"Tool input/output validation failed: {str(tsve)}."
                if tsve.original_exception and hasattr(tsve.original_exception, 'errors'):
                    try:
                        pydantic_errors = json.dumps(tsve.original_exception.errors(), indent=2) # type: ignore
                        error_detail += f" Details: {pydantic_errors}"
                    except Exception: pass # Ignore if errors() method is not as expected
                raise HTTPException(status_code=422, detail=error_detail)
            except Exception as e:
                logger.error(f"Error during BasicFinancialStrategy turn {turn + 1}: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"An unexpected error occurred during turn {turn + 1} of basic_financial analysis: {str(e)}")

        if final_assistant_responses_content:
            for block_dict in final_assistant_responses_content:
                if block_dict.get("type") == "text":
                    final_text_summary_parts.append(block_dict.get("text", ""))

        final_text_summary = "\n".join(final_text_summary_parts).strip()

        return {
            "analysis_text": final_text_summary,
            "visualizations": {
                "charts": collected_charts,
                "tables": collected_tables
            },
            "metrics": collected_metrics
        }
