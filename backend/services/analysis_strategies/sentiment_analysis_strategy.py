"""
Sentiment Analysis Strategy

This module implements sentiment analysis for financial documents, focusing on tone,
market sentiment, and qualitative insights extraction from financial communications,
earnings reports, and other text-based financial content.

Upstream Dependencies:
- base_strategy.AnalysisStrategy: Abstract base class for strategy implementation
- models.database_models.Document: Document metadata model (not used directly for text analysis)
- pdf_processing.api_service.ClaudeService: Core Claude API service for text analysis
- utils.exceptions.ToolSchemaValidationError: Custom exception handling for tool validation
- anthropic.types.Message/TextBlock: Anthropic API response types for message construction

Downstream Dependencies:
- Invoked by services.analysis_service.AnalysisService when analysis_type="sentiment_analysis"
- Results consumed by API routes in app.routes.analysis.py
- Sentiment insights displayed in frontend analysis interface
- Used for qualitative analysis complementing quantitative financial metrics

Key Features:
- Text-focused analysis using aggregated document content (not PDF-native processing)
- Multi-turn conversation support (max 5 turns) for comprehensive sentiment extraction
- Tool integration capability for potential sentiment visualization/metrics
- User query context integration for targeted sentiment analysis
- Robust error handling with HTTP exception mapping
- Mock message construction for final result processing

Analysis Flow:
1. Process aggregated text content from uploaded documents
2. Integrate user query context for focused sentiment analysis
3. Execute multi-turn conversation using specialized sentiment analysis prompts
4. Handle any tool calls for sentiment metrics or visualizations
5. Construct final sentiment analysis results with standard format
6. Return sentiment insights as structured analysis response

Note: Unlike other strategies, this focuses on qualitative text analysis rather than
quantitative financial metrics, making it complementary to numerical analysis strategies.
"""

import logging
import json
from typing import List, Dict, Any, Optional

from importlib.resources import files
from fastapi import HTTPException
from anthropic.types import Message, TextBlock

from models.database_models import Document # For documents parameter type hint
from pdf_processing.api_service import ClaudeService # For self.claude_service
from .base_strategy import AnalysisStrategy
from utils.exceptions import ToolSchemaValidationError

logger = logging.getLogger(__name__)

class SentimentAnalysisStrategy(AnalysisStrategy):
    """
    Strategy for sentiment analysis.
    This strategy replicates the logic previously in AnalysisService for "sentiment_analysis" type.
    """
    PROMPT_PATH = files('services.analysis_strategies').joinpath('prebuilt_prompts/sentiment_analysis_prompt.md')
    LOADED_PROMPT = PROMPT_PATH.read_text(encoding='utf-8')

    def __init__(self, claude_service: ClaudeService):
        super().__init__(claude_service)
        if not SentimentAnalysisStrategy.LOADED_PROMPT:
            logger.error("Sentiment analysis prompt could not be loaded.")
            raise ValueError("Sentiment analysis prompt could not be loaded.")

    async def execute(
        self,
        aggregated_text: str, # Text from documents
        documents: List[Document], # List of Document objects (metadata, not directly used for text here)
        parameters: Dict[str, Any], # Additional parameters (not typically used by this basic version)
        user_query: Optional[str], # User's query (can augment the analysis text)
        pdf_base64_contents: Optional[List[str]] = None # Not used by sentiment which operates on text
    ) -> Dict[str, Any]:
        logger.info(f"Executing SentimentAnalysisStrategy for query: '{user_query}'")

        # Sentiment analysis primarily uses aggregated_text.
        # If a user_query is provided, it can be appended to the text to be analyzed.
        text_to_analyze = aggregated_text
        if user_query:
            text_to_analyze = f"{aggregated_text}\n\nUser Query Context: {user_query}"

        if not text_to_analyze: # Handle empty text case
            logger.warning("No text provided for sentiment analysis.")
            return { # Return a default or error structure
                "analysis_text": "No text provided for analysis.",
                "visualizations": {"charts": [], "tables": []}, # Match expected structure
                "metrics": []
            }

        current_messages: List[Dict[str, Any]] = [
            {"role": "user", "content": [{"type": "text", "text": text_to_analyze}]}
        ]

        final_assistant_responses_content: List[Dict[str, Any]] = []
        max_turns = 5  # Max turns, though sentiment usually finishes in fewer.

        for turn in range(max_turns):
            logger.info(f"Sentiment analysis - Turn {turn + 1}/{max_turns}")
            try:
                if not hasattr(self.claude_service, 'execute_tool_interaction_turn'):
                    logger.error("ClaudeService.execute_tool_interaction_turn is not available.")
                    return {
                        "analysis_text": "Error: ClaudeService.execute_tool_interaction_turn not implemented.",
                        "visualizations": {"charts": [], "tables": []},
                        "metrics": []
                    }

                api_response: Message = await self.claude_service.execute_tool_interaction_turn(
                    system_prompt=SentimentAnalysisStrategy.LOADED_PROMPT,
                    messages=current_messages,
                    tools=self.claude_service.tools_for_api # ClaudeService provides available tools
                )

                if api_response.content is None:
                    logger.warning(f"API response content is None in turn {turn + 1}. Stop reason: {api_response.stop_reason}")
                    if api_response.stop_reason not in ["tool_use", "stop_sequence", "end_turn"]:
                         final_assistant_responses_content.append({"type": "text", "text": "No further content from assistant."})
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

                        tool_output_str = ""
                        tool_schema = self.claude_service.tool_schemas_map.get(tool_name)
                        if tool_schema and tool_schema.processor:
                            try:
                                processed_data = tool_schema.processor(tool_input)
                                tool_output_str = json.dumps(processed_data) if processed_data is not None else json.dumps({"status": "Tool processed, no output."})
                            except Exception as proc_e:
                                logger.error(f"Error processing tool {tool_name} (ID: {tool_use_id}): {proc_e}", exc_info=True)
                                tool_output_str = json.dumps({"error": f"Failed to process tool {tool_name}: {str(proc_e)}"})
                        else:
                            logger.warning(f"No processor for tool {tool_name} (ID: {tool_use_id})")
                            tool_output_str = json.dumps({"error": f"No processor for tool {tool_name}"})

                        tool_results_for_next_turn.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": tool_output_str,
                        })

                if tool_results_for_next_turn:
                    current_messages.append({"role": "user", "content": tool_results_for_next_turn})

                if api_response.stop_reason == "stop_sequence" or not contains_tool_use:
                    logger.info(f"Sentiment analysis conversation loop finished in turn {turn + 1}. Stop Reason: {api_response.stop_reason}")
                    final_assistant_responses_content.extend(assistant_message_content_blocks)
                    break

                if turn == max_turns - 1:
                    logger.warning(f"Sentiment analysis reached max_turns ({max_turns}). Last assistant message content: {assistant_message_content_blocks}")
                    final_assistant_responses_content.extend(assistant_message_content_blocks)

            except ToolSchemaValidationError as tsve:
                logger.error(f"Tool schema validation error during SentimentAnalysisStrategy execution, turn {turn+1}: {tsve}", exc_info=True)
                error_detail = f"Tool input/output validation failed: {str(tsve)}."
                if tsve.original_exception and hasattr(tsve.original_exception, 'errors'):
                    try:
                        pydantic_errors = json.dumps(tsve.original_exception.errors(), indent=2) # type: ignore
                        error_detail += f" Details: {pydantic_errors}"
                    except Exception: pass
                raise HTTPException(status_code=422, detail=error_detail)
            except Exception as e:
                logger.error(f"Error during SentimentAnalysisStrategy turn {turn + 1}: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"An unexpected error occurred during turn {turn + 1} of sentiment analysis: {str(e)}")

        # Process the final response using ClaudeService._process_tool_calls
        # This requires constructing a mock Message object from final_assistant_responses_content
        processed_content_blocks_for_final_message = []
        for block_dict in final_assistant_responses_content:
            block_type = block_dict.get("type")
            if block_type == "text":
                processed_content_blocks_for_final_message.append(TextBlock(type="text", text=block_dict.get("text","")))
            elif block_type == "tool_use":
                # _process_tool_calls expects tool_use blocks to be present if they were part of the final message
                # However, for sentiment, the final message should ideally be text after tool results are processed.
                # If a tool_use is in the final message, it implies something might be off or it's a complex final state.
                logger.warning(f"Tool use block found in final_assistant_responses_content for sentiment analysis: {block_dict.get('name')}")
                # We might need to reconsider if tool_use blocks should be passed to _process_tool_calls
                # For now, including it as per the original logic structure.
                # from anthropic.types.beta.tools import ToolUseBlock
                # processed_content_blocks_for_final_message.append(ToolUseBlock(**block_dict)) # This might need specific model from anthropic
                pass # For now, skipping adding tool_use to the mock final message as _process_tool_calls usually handles results.


        # If there's no actual content (e.g. all turns failed or no text produced),
        # _process_tool_calls might not be meaningful.
        if not processed_content_blocks_for_final_message and not any(block.get("type") == "tool_use" for block in final_assistant_responses_content) :
             logger.warning("No text or tool_use content in final_assistant_responses_content for sentiment analysis. Returning empty result.")
             return {
                "analysis_text": "No meaningful output from sentiment analysis.",
                "visualizations": {"charts": [], "tables": []},
                "metrics": []
            }


        # Construct the mock final API response for _process_tool_calls
        # The original logic in AnalysisService used a Message object.
        # We need to ensure `content` is a list of TextBlock or other valid anthropic types.
        mock_final_api_response = Message(
            id="final_mock_response_sentiment_strategy", # Unique ID
            type="message",
            role="assistant",
            model="mock_model_for_sentiment", # Or a relevant model name
            content=processed_content_blocks_for_final_message, # Content should be List[TextBlock | ImageBlock ...]
            stop_reason="stop_sequence", # Assuming it ended normally
            stop_sequence=None,
            usage={"input_tokens": 0, "output_tokens": 0} # Mock usage
        )

        if not hasattr(self.claude_service, '_process_tool_calls'):
            logger.error("ClaudeService._process_tool_calls is not available.")
            # Fallback or error
            return {
                "analysis_text": "Error: ClaudeService._process_tool_calls not implemented.",
                "visualizations": {"charts": [], "tables": []},
                "metrics": []
            }

        try:
            # _process_tool_calls is expected to structure the final output, including text, charts, tables, metrics
            result_data = self.claude_service._process_tool_calls(mock_final_api_response)
        except Exception as e:
            logger.error(f"Error calling _process_tool_calls in SentimentAnalysisStrategy: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error finalizing sentiment analysis results: {str(e)}")

        return result_data
