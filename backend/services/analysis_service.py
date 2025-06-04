"""
Analysis Service Module
======================

This module provides the main backend service for orchestrating financial document analysis workflows. It acts as the central point for running, managing, and retrieving analyses on financial documents, supporting both single and multi-document scenarios, and leveraging advanced AI/LLM services for tool-based visualizations and insights.

Key Responsibilities:
---------------------
- Route analysis requests to the appropriate AI/LLM service (e.g., ClaudeService) or internal agent (FinancialAnalysisAgent) based on analysis type.
- Aggregate and validate content from one or more financial documents, including extracting raw text and PDF content.
- Support a variety of analysis types (comprehensive, ratios, trends, benchmarking, sentiment, etc.) with extensible logic for new types.
- Manage the full lifecycle of an analysis: input validation, execution, result formatting, and storage via repositories.
- Format and enrich analysis results with metadata, visualizations (charts/tables/metrics), insights, and summary statistics for downstream API and frontend consumption.
- Provide utility methods for listing, retrieving, and summarizing analyses, including support for pagination and filtering.

Integration Points:
-------------------
- `ClaudeService`: For AI-powered analysis, tool-based visualizations, and sentiment analysis.
- `FinancialAnalysisAgent`: For internal calculations (ratios, trends, benchmarks) and chart/table data preparation.
- `AnalysisRepository` and `DocumentRepository`: For persistent storage and retrieval of analyses and document metadata/content.
- `visualization_helpers`: For post-processing and structuring visualization data.
- Models: Uses data models from `models.analysis`, `models.visualization`, and `models.database_models` for type safety and result formatting.

Typical Usage:
--------------
- Called by API endpoints or other backend services to run a new analysis on one or more documents, specifying the analysis type and parameters.
- Used to retrieve, list, or summarize past analyses for a document or user.
- Supports both synchronous and asynchronous workflows, with robust error handling and logging for traceability.
- Designed to be extensible for new analysis types, additional AI services, or custom business logic.

Design Notes:
-------------
- Centralizes all analysis orchestration logic to ensure consistency and maintainability.
- Supports multi-document aggregation and validation, with future extensibility for user-specific access control.
- Leverages tool-based AI analysis for rich, structured outputs (charts, tables, metrics) compatible with modern frontend frameworks.
- Provides detailed logging at each step for debugging and auditability.
- Designed for modularity: new analysis types or AI services can be added with minimal changes to the core workflow.
- Ensures all outputs are formatted for downstream API and UI consumption, including metadata, visualizations, and insights.
"""

import os
import logging
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import base64 # Added for PDF content encoding
from fastapi import HTTPException # Added for Story #17
from anthropic.types import Message, TextBlock, ToolUseBlock # Moved import

from settings import MODEL_HAIKU, MODEL_SONNET # Changed to import from effective project root
from repositories.analysis_repository import AnalysisRepository
from repositories.document_repository import DocumentRepository
from pdf_processing.api_service import ClaudeService, ALL_TOOLS_DICT
from pdf_processing.financial_agent import FinancialAnalysisAgent
from models.database_models import AnalysisResult, Document
from utils.visualization_helpers import (
    generate_monetary_values_data,
    generate_percentage_data,
    generate_keyword_frequency_data,
    get_data_for_visualization_type,
)
from models.analysis import FinancialMetric, FinancialRatio, ComparativePeriod
from models.visualization import ChartData, TableData # Assuming these are defined

from .analysis_strategies import strategy_map # Added for Story #1
from utils import tool_processing # Corrected import
from utils.exceptions import ToolSchemaValidationError # Corrected import

logger = logging.getLogger(__name__)

# Added for PlanPlanPlan.md item 3
# TODO: Make this environment-driven as per plan
KW_FREQ_ENABLED = False 

# System prompts for Story #2
BASIC_FINANCIAL_SYSTEM_PROMPT = """You are an AI financial analyst. Your task is to analyze the provided financial document and extract key insights.

The PDF document is automatically available to you through Claude's native PDF support, which provides both text and visual understanding of tables, charts, and financial data.

You MUST perform the following actions in this exact order:
1. Analyze the financial document to identify key metrics and data
2. Call the `generate_financial_metric` tool exactly twice to highlight two important financial metrics
3. Call the `generate_table_data` tool exactly once to create a table with at least 3 relevant metrics
4. Call the `generate_graph_data` tool exactly once to create a visualization of the data
5. Provide a concise summary (2-3 paragraphs) explaining the financial insights and trends

Use the actual financial data from the document. If specific metrics are not available, state this clearly."""

SENTIMENT_ANALYSIS_SYSTEM_PROMPT = """You are an AI sentiment analysis expert. Your task is to analyze the sentiment of the provided text.
You MUST perform the following actions in this exact order:
1. Provide an overall sentiment (e.g., Positive, Negative, Neutral) and a sentiment score (a float between -1.0 and 1.0) as text.
2. Call the `generate_table_data` tool exactly once to create a table listing up to 5 key phrases from the text that most contribute to this sentiment, along with their individual sentiment if determinable.
3. Provide a brief textual summary explaining the sentiment based on these phrases.
Adhere strictly to the Pydantic models provided in the tool descriptions for tool inputs.
"""

class AnalysisService:
    """Service for managing financial analysis."""
    
    SUPPORTED_ANALYSIS_TYPES = [
        {
            "type": "comprehensive_tools",
            "display_name": "Comprehensive Analysis",
            "description": "Performs a comprehensive financial analysis, generating relevant charts and tables using advanced tools."
        },
        {
            "type": "financial_ratios",
            "display_name": "Financial Ratios",
            "description": "Calculates and interprets key financial ratios from the provided documents."
        },
        {
            "type": "trend_analysis",
            "display_name": "Trend Analysis",
            "description": "Analyzes trends across financial periods and highlights significant changes."
        },
        {
            "type": "benchmarking",
            "display_name": "Benchmarking",
            "description": "Compares financial performance against benchmarks or peer groups."
        },
        {
            "type": "sentiment_analysis",
            "display_name": "Sentiment Analysis",
            "description": "Assesses sentiment in financial documents or management commentary."
        },
        {
            "type": "basic_financial",
            "display_name": "Basic Financial Analysis",
            "description": "Provides a concise textual summary of the key financial highlights, extracts key financial metrics, and presents a summary table of important figures."
        },
        {
            "type": "financial_template",
            "display_name": "Template-Driven Financial Analysis",
            "description": "Runs the custom financial analysis template for advanced, structured analysis and visualization."
        }
    ]

    @staticmethod
    def get_supported_analysis_types() -> list:
        """
        Return the list of supported analysis types with display names and descriptions.
        """
        return AnalysisService.SUPPORTED_ANALYSIS_TYPES

    def __init__(
        self,
        analysis_repository: AnalysisRepository,
        document_repository: DocumentRepository
    ):
        """
        Initialize the analysis service.
        
        Args:
            analysis_repository: Repository for analysis operations
            document_repository: Repository for document operations
        """
        self.analysis_repository = analysis_repository
        self.document_repository = document_repository
        self.claude_service = ClaudeService()
        self.financial_agent = FinancialAnalysisAgent()
    
    async def run_analysis(
        self,
        document_ids: List[str],
        analysis_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        custom_knowledge_base: Optional[str] = None,
        query: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Run financial analysis on one or more documents.
        Routes to the appropriate analysis method based on analysis_type.

        Args:
            document_ids: List of document IDs to analyze
            analysis_type: Type of analysis to run
            parameters: Optional parameters for the analysis
            custom_knowledge_base: Optional knowledge base ID to use for context
            query: Optional user query for the analysis

        Returns:
            Tuple of (analysis_id, result_data_with_metadata)
        """
        if parameters is None:
            parameters = {}

        if custom_knowledge_base:
            parameters["knowledge_base"] = custom_knowledge_base

        # Generate a unique ID for this analysis run
        analysis_id = str(uuid.uuid4())
        logger.info(f"Starting analysis {analysis_id} of type '{analysis_type}' for documents: {document_ids}")

        documents: List[Document] = []
        aggregated_text = ""
        pdf_base64_contents: List[str] = []

        # Initial error handling for document_ids (can be refined)
        if not document_ids:
            logger.error("No document IDs provided for analysis.")
            raise HTTPException(status_code=400, detail="At least one document ID must be provided for analysis.")

        try: # Main try for document loading and overall analysis orchestration
            docs_data = await asyncio.gather(*[self.document_repository.get_document(doc_id) for doc_id in document_ids])
            
            loaded_docs_count = 0
            for doc_data in docs_data:
                if doc_data is None:
                    # Log and continue for now, or decide if this should be a hard error
                    logger.warning(f"Document not found for one of the provided IDs. Analysis {analysis_id} may be incomplete.")
                    continue 

                doc = Document(**doc_data) if isinstance(doc_data, dict) else doc_data
                documents.append(doc)
                loaded_docs_count += 1
                
                # Use optimized text retrieval with Claude Files API caching
                try:
                    optimized_text = await self.claude_service.get_document_text(doc.id, self.document_repository)
                    aggregated_text += optimized_text + "\n\n"
                    logger.info(f"Using cached text for document {doc.id} in analysis ({len(optimized_text)} chars)")
                except Exception as e:
                    logger.warning(f"Failed to get cached text for document {doc.id}: {e}")
                    if doc.raw_text:
                        aggregated_text += doc.raw_text + "\n\n"
                
                # Aggregate PDF base64 content if needed by strategies (and if available)
                if hasattr(doc, 'content_pdf_path') and doc.content_pdf_path: # Assuming PDF path is stored
                    try:
                        # This is a placeholder for actual PDF to base64 conversion logic
                        # You would typically read the file from doc.content_pdf_path and encode it
                        # For example:
                        # with open(doc.content_pdf_path, "rb") as pdf_file:
                        #     encoded_string = base64.b64encode(pdf_file.read()).decode('utf-8')
                        #     pdf_base64_contents.append(encoded_string)
                        # This logic depends on how PDF paths are stored and accessed.
                        # For now, we are not populating pdf_base64_contents to avoid file I/O here.
                        pass
                    except Exception as e:
                        logger.error(f"Error encoding PDF for document {doc.id}: {e}")

                # Get PDF content for Claude's native PDF support
                try:
                    # Get the PDF binary content from storage
                    pdf_content = await self.document_repository.storage_service.get_file(f"{doc.id}.pdf")
                    if pdf_content:
                        # Convert to base64 for Claude API
                        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
                        pdf_base64_contents.append(pdf_base64)
                        logger.info(f"Loaded PDF content for document {doc.id}: {len(pdf_content)} bytes")
                    else:
                        logger.warning(f"No PDF content found for document {doc.id}")
                except Exception as e:
                    logger.error(f"Error loading PDF content for document {doc.id}: {e}")

            if loaded_docs_count == 0:
                logger.error(f"No valid documents could be loaded for analysis {analysis_id} with IDs: {document_ids}.")
                raise HTTPException(status_code=404, detail="None of the provided document IDs could be loaded.")

            logger.info(f"Aggregated text for analysis {analysis_id}. Total length: {len(aggregated_text)}")

            result_data: Dict[str, Any] = {}
            
            strategy_cls = strategy_map.get(analysis_type)

            if strategy_cls:
                logger.info(f"Using strategy {strategy_cls.__name__} for analysis type \'{analysis_type}\'")
                strategy = strategy_cls(self.claude_service)
                
                strategy_input_args = {
                    "aggregated_text": aggregated_text,
                    "documents": documents,
                    "parameters": parameters,
                    "user_query": query,
                    "pdf_base64_contents": pdf_base64_contents
                }
                
                try: # Inner try for strategy execution
                    result_data = await strategy.execute(**strategy_input_args)

                    # Derived Visuals Logic (PlanPlanPlan.md item 3)
                    # Ensure 'visualizations' key exists and is a dict
                    if 'visualizations' not in result_data or not isinstance(result_data['visualizations'], dict):
                        result_data['visualizations'] = {}
                    viz = result_data['visualizations']

                    # Ensure 'metrics' key exists and is a list (or at least iterable)
                    metrics_data = result_data.get('metrics')
                    if metrics_data and isinstance(metrics_data, list):
                        logger.info(f"Generating monetary values and percentages from {len(metrics_data)} metrics.")
                        # Assuming generate_monetary_values_data and generate_percentage_data can handle empty lists if necessary
                        viz['monetary_values'] = generate_monetary_values_data(metrics_data, result_data.get('insights', [])) # insights added based on deep dive
                        viz['percentages']    = generate_percentage_data(metrics_data, result_data.get('insights', [])) # insights added based on deep dive
                    else:
                        logger.warning("Metrics data not found or not in expected format for derived visuals.")
                        viz['monetary_values'] = {}
                        viz['percentages']    = {}

                    if KW_FREQ_ENABLED and aggregated_text:
                        logger.info("Generating keyword frequency data.")
                        viz['keyword_frequency'] = generate_keyword_frequency_data(aggregated_text)
                    elif KW_FREQ_ENABLED:
                        logger.warning("KW_FREQ_ENABLED is true, but aggregated_text is empty.")
                        viz['keyword_frequency'] = {}
                    # If KW_FREQ_ENABLED is False, keywordFrequency will not be added, which is fine.

                except ToolSchemaValidationError as tsve: # Story #17 - Specific error for tool schema issues
                    logger.error(f"Tool schema validation error during strategy execution for analysis {analysis_id}: {tsve}", exc_info=True)
                    error_detail = f"Tool input/output validation failed: {str(tsve)}."
                    if tsve.original_exception and hasattr(tsve.original_exception, 'errors'):
                        try:
                            pydantic_errors = json.dumps(tsve.original_exception.errors(), indent=2) # type: ignore
                            error_detail += f" Details: {pydantic_errors}"
                        except Exception:
                            pass
                    raise HTTPException(status_code=422, detail=error_detail)
                except Exception as e: # Added general exception for strategy execution
                    logger.error(f"Error executing strategy {strategy_cls.__name__} for analysis {analysis_id}: {e}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"An unexpected error occurred while running the \'{analysis_type}\' strategy: {str(e)}")

            elif analysis_type == "basic_financial":
                logger.info(f"Executing basic_financial analysis for analysis {analysis_id}")
                
                # Build initial message with PDF content using Claude's native PDF support
                content_blocks = []
                
                # Add PDF documents using Claude's native PDF support
                if pdf_base64_contents:
                    logger.info(f"Using {len(pdf_base64_contents)} PDF documents with Claude's native PDF support")
                    for i, pdf_base64 in enumerate(pdf_base64_contents):
                        content_blocks.append({
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        })
                    # Add a text prompt after the PDFs
                    prompt_text = "Please analyze the financial documents provided above."
                    if query:
                        prompt_text += f"\n\nUser query: {query}"
                    content_blocks.append({"type": "text", "text": prompt_text})
                else:
                    # Fallback to text if no PDFs available
                    logger.warning("No PDF content available, falling back to text")
                    content_blocks.append({
                        "type": "text", 
                        "text": aggregated_text if aggregated_text else "No document content available."
                    })
                    if query:
                        content_blocks.append({"type": "text", "text": f"User query: {query}"})
                
                # Initial message from user to assistant
                current_messages: List[Dict[str, Any]] = [
                    {"role": "user", "content": content_blocks}
                ]

                # Store all assistant responses that include text or final (non-tool_use) content blocks
                final_assistant_responses_content: List[Dict[str, Any]] = []
                
                # Initialize collectors for processed tool outputs
                collected_charts: List[Dict[str, Any]] = []
                collected_tables: List[Dict[str, Any]] = []
                collected_metrics: List[Dict[str, Any]] = []
                final_text_summary_parts: List[str] = []

                max_turns = 5 # Max turns to prevent infinite loops
                for turn in range(max_turns):
                    logger.info(f"Basic financial analysis - Turn {turn + 1}")
                    try:
                        # Determine model for this turn: Sonnet (via model_router) for first turn, Haiku for subsequent turns
                        model_for_this_turn_override = None
                        if turn > 0:
                            model_for_this_turn_override = MODEL_HAIKU
                            logger.info(f"Basic financial analysis - Turn {turn + 1}: Switching to Haiku model ({MODEL_HAIKU})")
                        else:
                            # For turn 0, model_override is None, ClaudeService will use its model_router (expected to be Sonnet)
                            logger.info(f"Basic financial analysis - Turn {turn + 1}: Using default model selection (expected Sonnet via model_router)")

                        api_response: Message = await self.claude_service.execute_tool_interaction_turn(
                            system_prompt=BASIC_FINANCIAL_SYSTEM_PROMPT,
                            messages=current_messages,
                            tools=self.claude_service.tools_for_api,
                            model_override=model_for_this_turn_override # Pass Haiku for subsequent turns, None for first
                        )
                        
                        # Add assistant's response to message history
                        # The content should be a list of blocks (text or tool_use)
                        assistant_message_content_blocks = [block.model_dump() for block in api_response.content]
                        current_messages.append({"role": "assistant", "content": assistant_message_content_blocks})
                        
                        tool_results_for_next_turn: List[Dict[str, Any]] = []
                        contains_tool_use = False

                        for block in api_response.content:
                            if block.type == 'tool_use':
                                contains_tool_use = True
                                tool_name = block.name
                                tool_use_id = block.id
                                tool_input = block.input
                                
                                logger.info(f"Assistant requested tool: {tool_name} (ID: {tool_use_id}) with input: {tool_input}")
                                
                                processed_data_for_tool: Optional[Dict[str, Any]] = None
                                tool_output_content_for_claude = "" # String representation for Claude

                                tool_schema = self.claude_service.tool_schemas_map.get(tool_name)
                                if tool_schema and tool_schema.processor:
                                    try:
                                        processed_data_for_tool = tool_schema.processor(tool_input) # Actual processed data
                                        if processed_data_for_tool is not None:
                                            # Store the structured data
                                            if tool_name == "generate_graph_data":
                                                collected_charts.append(processed_data_for_tool)
                                            elif tool_name == "generate_table_data":
                                                collected_tables.append(processed_data_for_tool)
                                            elif tool_name == "generate_financial_metric":
                                                collected_metrics.append(processed_data_for_tool)
                                            tool_output_content_for_claude = json.dumps(processed_data_for_tool)
                                        else:
                                            tool_output_content_for_claude = json.dumps({"status": "Tool processed, no output."})
                                    except Exception as proc_e:
                                        logger.error(f"Error processing tool {tool_name} (ID: {tool_use_id}): {proc_e}")
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
                                # This text block is part of an intermediate assistant message.
                                # We'll collect text from the *final* assistant message after the loop.
                                pass

                        if tool_results_for_next_turn:
                            current_messages.append({"role": "user", "content": tool_results_for_next_turn})
                        
                        if api_response.stop_reason == "stop_sequence" or not contains_tool_use:
                            logger.info(f"Basic financial analysis conversation loop finished in turn {turn + 1}. Stop Reason: {api_response.stop_reason}")
                            # The last assistant message (assistant_message_content_blocks) is the final one.
                            final_assistant_responses_content.extend(assistant_message_content_blocks)
                            break
                        
                        if turn == max_turns - 1:
                            logger.warning(f"Basic financial analysis reached max_turns ({max_turns}). Last assistant message content: {assistant_message_content_blocks}")
                            final_assistant_responses_content.extend(assistant_message_content_blocks) # Store last attempt

                    except ToolSchemaValidationError as e: # Handle specific validation errors
                        logger.error(f"Tool schema validation error during basic_financial analysis {analysis_id}, turn {turn+1}: {e}", exc_info=True)
                        raise HTTPException(status_code=422, detail=f"Tool input/output validation failed: {str(e)}.")
                    except Exception as e: # General errors during a turn
                        logger.error(f"Error during basic_financial analysis turn {turn + 1} for analysis {analysis_id}: {e}", exc_info=True)
                        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during turn {turn + 1} of basic_financial analysis: {str(e)}")
                
                # Process the final assistant response(s) for text
                if final_assistant_responses_content:
                    for block_dict in final_assistant_responses_content:
                        if block_dict.get("type") == "text":
                            final_text_summary_parts.append(block_dict.get("text", ""))
                
                final_text_summary = "\\n".join(final_text_summary_parts).strip()

                result_data = {
                    "analysis_text": final_text_summary,
                    "visualizations": {
                        "charts": collected_charts,
                        "tables": collected_tables
                    },
                    "metrics": collected_metrics
                }

            elif analysis_type == "sentiment_analysis":
                logger.info(f"Executing sentiment_analysis for analysis {analysis_id}")
                current_messages: List[Dict[str, Any]] = [
                    {"role": "user", "content": [{"type": "text", "text": aggregated_text if aggregated_text else "No document text available."}]}
                ]
                if query:
                    current_messages[0]["content"].append({"type": "text", "text": f"User query: {query}"}) # type: ignore

                final_assistant_responses_content: List[Dict[str, Any]] = []
                max_turns = 5 
                for turn in range(max_turns):
                    logger.info(f"Sentiment analysis - Turn {turn + 1}")
                    try:
                        api_response: Message = await self.claude_service.execute_tool_interaction_turn(
                            system_prompt=SENTIMENT_ANALYSIS_SYSTEM_PROMPT,
                            messages=current_messages,
                            tools=self.claude_service.tools_for_api
                        )
                        
                        assistant_message_content_blocks = [block.model_dump() for block in api_response.content]
                        current_messages.append({"role": "assistant", "content": assistant_message_content_blocks})
                        
                        tool_results_for_next_turn: List[Dict[str, Any]] = []
                        contains_tool_use = False
                        for block in api_response.content:
                            if block.type == 'tool_use':
                                contains_tool_use = True
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
                                        logger.error(f"Error processing tool {tool_name} (ID: {tool_use_id}): {proc_e}")
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

                    except ToolSchemaValidationError as e:
                        logger.error(f"Tool schema validation error during sentiment_analysis {analysis_id}, turn {turn+1}: {e}", exc_info=True)
                        raise HTTPException(status_code=422, detail=f"Tool input/output validation failed: {str(e)}.")
                    except Exception as e:
                        logger.error(f"Error during sentiment_analysis turn {turn + 1} for analysis {analysis_id}: {e}", exc_info=True)
                        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during turn {turn + 1} of sentiment_analysis: {str(e)}")
                
                processed_content_blocks = []
                for block_dict in final_assistant_responses_content: # Iterate over the collected final content
                    block_type = block_dict.get("type")
                    if block_type == "text":
                        processed_content_blocks.append(TextBlock(type="text", text=block_dict.get("text","")))
                    elif block_type == "tool_use":
                        logger.debug(f"Skipping tool_use block (id: {block_dict.get('id')}) when creating mock for _process_tool_calls in sentiment_analysis.")
                        pass # Pass for now
                
                mock_final_api_response = Message(
                    id="final_mock_response_sentiment", type="message", role="assistant", model="mock_model",
                    content=processed_content_blocks, stop_reason="stop_sequence", stop_sequence=None,
                    usage={"input_tokens": 0, "output_tokens": 0}
                )
                result_data = self.claude_service._process_tool_calls(mock_final_api_response)

            else:
                logger.warning(f"Unsupported analysis type: {analysis_type}")
                raise HTTPException(status_code=400, detail=f"Unsupported analysis type: {analysis_type}")
            
            # Save and return the analysis result (if not raised by this point)
            return await self._save_and_return_analysis_result(
                analysis_id, document_ids, analysis_type, result_data, query, parameters
            )

        except HTTPException: # Re-raise HTTPExceptions directly
            raise
        except ValueError as e: # Catch ValueErrors (e.g., no documents)
            logger.error(f"ValueError during analysis {analysis_id}: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"Unexpected error during analysis {analysis_id}: {e}", exc_info=True)
            # Consider a more generic server error for truly unexpected issues
            raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

    async def _run_financial_ratio_analysis(
        self,
        document: Document,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run financial ratio analysis.
        
        Args:
            document: Document to analyze
            parameters: Analysis parameters
            
        Returns:
            Dictionary containing the analysis results
        """
        # Extract financial data from the document
        financial_data = document.extracted_data.get("financial_data", {})
        
        if not financial_data:
            raise ValueError("No financial data found in document")
        
        # Use the financial agent to calculate ratios
        ratios = await self.financial_agent.calculate_financial_ratios(
            financial_data=financial_data,
            parameters=parameters
        )
        
        # Build the result data
        result_data = {
            "ratios": ratios,
            "document_type": document.document_type.value if document.document_type else "other",
            "periods": document.periods or [],
            "insights": []
        }
        
        # Generate insights if requested
        if parameters.get("generate_insights", True):
            insights = await self.financial_agent.generate_insights_from_ratios(ratios)
            result_data["insights"] = insights
        
        # Prepare chart data if requested
        if parameters.get("generate_charts", True):
            chart_data = await self.financial_agent.prepare_chart_data(
                financial_data=financial_data,
                ratios=ratios,
                parameters=parameters
            )
            result_data["chart_data"] = chart_data
        
        return result_data
    
    async def _run_trend_analysis(
        self,
        document: Document,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run trend analysis.
        
        Args:
            document: Document to analyze
            parameters: Analysis parameters
            
        Returns:
            Dictionary containing the analysis results
        """
        # Extract financial data from the document
        financial_data = document.extracted_data.get("financial_data", {})
        
        if not financial_data:
            raise ValueError("No financial data found in document")
        
        # Get time periods from the document
        periods = document.periods
        if not periods or len(periods) < 2:
            raise ValueError("Trend analysis requires at least two time periods")
        
        # Use the financial agent to analyze trends
        trends = await self.financial_agent.analyze_trends(
            financial_data=financial_data,
            periods=periods,
            parameters=parameters
        )
        
        # Build the result data
        result_data = {
            "trends": trends,
            "document_type": document.document_type.value if document.document_type else "other",
            "periods": periods,
            "insights": []
        }
        
        # Generate insights if requested
        if parameters.get("generate_insights", True):
            insights = await self.financial_agent.generate_insights_from_trends(trends)
            result_data["insights"] = insights
        
        # Prepare chart data if requested
        if parameters.get("generate_charts", True):
            chart_data = await self.financial_agent.prepare_trend_chart_data(
                trends=trends,
                periods=periods,
                parameters=parameters
            )
            result_data["chart_data"] = chart_data
        
        return result_data
    
    async def _run_benchmark_analysis(
        self,
        document: Document,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run benchmark analysis.
        
        Args:
            document: Document to analyze
            parameters: Analysis parameters
            
        Returns:
            Dictionary containing the analysis results
        """
        # Extract financial data from the document
        financial_data = document.extracted_data.get("financial_data", {})
        
        if not financial_data:
            raise ValueError("No financial data found in document")
        
        # Get benchmark data (in a real implementation, this would come from a database or API)
        industry = parameters.get("industry", "general")
        benchmark_data = await self.financial_agent.get_industry_benchmarks(industry)
        
        # Use the financial agent to compare with benchmarks
        comparison = await self.financial_agent.compare_with_benchmarks(
            financial_data=financial_data,
            benchmarks=benchmark_data,
            parameters=parameters
        )
        
        # Build the result data
        result_data = {
            "benchmark_comparison": comparison,
            "industry": industry,
            "document_type": document.document_type.value if document.document_type else "other",
            "periods": document.periods or [],
            "insights": []
        }
        
        # Generate insights if requested
        if parameters.get("generate_insights", True):
            insights = await self.financial_agent.generate_insights_from_benchmark(comparison)
            result_data["insights"] = insights
        
        # Prepare chart data if requested
        if parameters.get("generate_charts", True):
            chart_data = await self.financial_agent.prepare_benchmark_chart_data(
                comparison=comparison,
                parameters=parameters
            )
            result_data["chart_data"] = chart_data
        
        return result_data
    
    async def get_analysis(self, analysis_id: str) -> Dict[str, Any]:
        """
        Get an analysis by ID.

        Args:
            analysis_id: ID of the analysis

        Returns:
            Dictionary containing the analysis
        """
        # Strip any prefix if present
        clean_id = analysis_id
        if analysis_id.startswith('analysis-'):
            clean_id = analysis_id.replace('analysis-', '', 1) # Remove only the first instance

        # Get the analysis from the repository
        analysis = await self.analysis_repository.get_analysis(clean_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        # Format the result data to match the structure expected by the API endpoint
        result_data = analysis.result_data or {}
        visualization_data = result_data.get("visualization_data", {})
        # Ensure visualization_data is a dict
        if visualization_data is None:
             visualization_data = {}

        response_payload = {
            "id": f"analysis-{analysis.id}", # Add prefix
            "documentIds": [analysis.document_id], # Wrap in list
            "analysisType": analysis.analysis_type,
            "timestamp": analysis.created_at.isoformat(),
            "analysisText": result_data.get("analysis_text", ""),
            "visualizationData": {
                 "charts": visualization_data.get("charts", []),
                 "tables": visualization_data.get("tables", []),
                 # Include other potential keys if they exist
                 **{k: v for k, v in visualization_data.items() if k not in ['charts', 'tables']}
            },
            "metrics": result_data.get("metrics", []),
            "ratios": result_data.get("ratios", []),
            "comparativePeriods": result_data.get("comparative_periods", []),
            "insights": result_data.get("insights", []),
            "citationReferences": result_data.get("citation_references", {}),
            # Add other relevant metadata if stored (or retrieve from document)
        }
        # Fetch document details to add metadata if needed
        document = await self.document_repository.get_document(analysis.document_id)
        if document:
            response_payload["document_type"] = document.document_type.value if document.document_type else "other"
            response_payload["periods"] = document.periods or []
            # Add query if stored (assuming it might be in parameters in result_data)
            response_payload["query"] = result_data.get("query", "")


        return response_payload

    async def list_document_analyses(
        self,
        document_id: str,
        analysis_type: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List analyses for a document.

        Args:
            document_id: ID of the document
            analysis_type: Optional analysis type to filter by
            limit: Maximum number of analyses to return
            offset: Starting index

        Returns:
            List of analyses summaries
        """
        analyses = await self.analysis_repository.list_document_analyses(
            document_id=document_id,
            analysis_type=analysis_type,
            limit=limit,
            offset=offset
        )

        # Format the results
        formatted_analyses = []
        for analysis in analyses:
            summary = self._generate_analysis_summary(analysis.result_data or {})
            formatted_analyses.append({
                "id": f"analysis-{analysis.id}", # Add prefix
                "document_id": analysis.document_id,
                "analysis_type": analysis.analysis_type,
                "created_at": analysis.created_at.isoformat(),
                "summary": summary
            })

        return formatted_analyses

    def _generate_analysis_summary(self, result_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of analysis results.
        """
        viz_data = result_data.get("visualization_data", {})
        if viz_data is None:
            viz_data = {}

        summary = {
            "insights_count": len(result_data.get("insights", [])),
            "metrics_count": len(result_data.get("metrics", [])),
            "ratios_count": len(result_data.get("ratios", [])),
            "comparisons_count": len(result_data.get("comparative_periods", [])),
            "charts_count": len(viz_data.get("charts", [])),
            "tables_count": len(viz_data.get("tables", [])),
        }

        # Include a sample insight if available
        if result_data.get("insights") and len(result_data["insights"]) > 0:
            summary["sample_insight"] = result_data["insights"][0][:100] + "..." # Truncate

        return summary

    async def _save_and_return_analysis_result(
        self,
        analysis_id: str,
        document_ids: List[str],
        analysis_type: str,
        result_data: Dict[str, Any], # This is the core output from the analysis (e.g., text, visualizations)
        user_query: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        logger.info(f"Saving analysis result for {analysis_id}, type {analysis_type}, docs {document_ids}")
        
        # Consolidate all information to be stored in the result_data JSONB field
        persisted_result_payload = {
            "analysis_output": result_data,  # The actual results from Claude/strategy
            "input_parameters": parameters if parameters else {},
            "input_query": user_query,
            "processing_status": "completed" # Status of this analysis run
        }
        
        analysis_to_save = AnalysisResult(
            id=analysis_id,
            document_ids=document_ids, 
            analysis_type=analysis_type,
            result_data=persisted_result_payload, # Store the consolidated payload
            created_at=datetime.utcnow()
            # No 'parameters', 'query_text', 'updated_at', or 'status' direct fields in DB model
        )
        try:
            await self.analysis_repository.create_analysis(
                document_ids=analysis_to_save.document_ids,
                analysis_type=analysis_to_save.analysis_type,
                result_data=analysis_to_save.result_data
            )
            logger.info(f"Successfully saved analysis {analysis_id}")

            # Format for return, including metadata
            # This structure should align with what API consumers expect.
            # The 'results' key in the formatted return should ideally contain what was in the original 'result_data' argument.
            
            # Extract core analysis outputs from result_data
            analysis_text_content = result_data.get("analysis_text", "") # Ensure this key matches _process_tool_calls output
            visualizations_content = result_data.get("visualizations", {"charts": [], "tables": []})
            metrics_content = result_data.get("metrics", [])
            # Assuming result_data might also contain other keys like 'ratios', 'insights' etc. from strategies
            # These should also be promoted if the frontend expects them at the top level.
            # For now, focusing on the ones derived from _process_tool_calls and seen in frontend issues.

            formatted_return = {
                "analysis_id": analysis_id, # Or "id": analysis_id if frontend expects "id"
                "document_ids": document_ids,
                "analysis_type": analysis_type,
                "status": persisted_result_payload["processing_status"], # Get status from the payload
                "created_at": analysis_to_save.created_at.isoformat(), # Or "timestamp"
                "query": user_query, 
                "parameters": parameters,
                # Promoted fields:
                "analysis_text": analysis_text_content,
                "visualization_data": visualizations_content,
                "metrics": metrics_content,
                # Spread other potential top-level fields from result_data if necessary,
                # for example, if strategies directly return 'ratios', 'insights' at top of their result_data dict:
                "ratios": result_data.get("ratios", []),
                "insights": result_data.get("insights", []),
                "comparativePeriods": result_data.get("comparative_periods", []), # Example
                "citationReferences": result_data.get("citation_references", {}) # Example
                # Remove the nested "results" key
            }
            return analysis_id, formatted_return
        except Exception as e:
            logger.error(f"Failed to save analysis {analysis_id}: {e}", exc_info=True)
            # Depending on requirements, might raise an error that translates to HTTP 500
            raise Exception(f"Failed to save analysis result for {analysis_id}")