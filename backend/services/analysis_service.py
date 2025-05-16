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

from repositories.analysis_repository import AnalysisRepository
from repositories.document_repository import DocumentRepository
from pdf_processing.claude_service import ClaudeService, ALL_TOOLS_DICT
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
from ..utils import tool_processing # Added for Story #9
from ..utils.exceptions import ToolSchemaValidationError # Added for Story #17

logger = logging.getLogger(__name__)

# System prompts for Story #2
BASIC_FINANCIAL_SYSTEM_PROMPT = """You are an AI financial analyst. Your task is to provide a concise textual summary of key financial highlights from the provided document excerpts.
You MUST perform the following actions in this exact order:
1. Call the `generate_financial_metric` tool exactly twice to extract two different key financial metrics.
2. Call the `generate_table_data` tool exactly once to present a summary table of important figures.
3. Provide a brief overall textual summary based on the document and the tool results.
Adhere strictly to the Pydantic models provided in the tool descriptions for tool inputs.
Ensure your final textual summary is concise and directly answers the user's query if provided, incorporating the extracted metrics and table.
"""

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
            docs_data = await asyncio.gather(*[self.document_repository.get_document_by_id(doc_id) for doc_id in document_ids])
            
            loaded_docs_count = 0
            for doc_data in docs_data:
                if doc_data is None:
                    # Log and continue for now, or decide if this should be a hard error
                    logger.warning(f"Document not found for one of the provided IDs. Analysis {analysis_id} may be incomplete.")
                    continue 

                doc = Document(**doc_data) if isinstance(doc_data, dict) else doc_data
                documents.append(doc)
                loaded_docs_count += 1
                
                if doc.content_text:
                    aggregated_text += doc.content_text + "\n\n"
                
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
                except ToolSchemaValidationError as e:
                    logger.error(f"Tool schema validation error during \'{analysis_type}\' for analysis {analysis_id}: {e}", exc_info=True)
                    error_detail = f"Tool input/output validation failed: {str(e)}."
                    if e.original_exception and hasattr(e.original_exception, 'errors'):
                        try:
                            pydantic_errors = json.dumps(e.original_exception.errors(), indent=2) # type: ignore
                            error_detail += f" Details: {pydantic_errors}"
                        except Exception:
                            pass
                    raise HTTPException(status_code=422, detail=error_detail)
                except Exception as e: # Added general exception for strategy execution
                    logger.error(f"Error executing strategy {strategy_cls.__name__} for analysis {analysis_id}: {e}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"An unexpected error occurred while running the \'{analysis_type}\' strategy: {str(e)}")

            elif analysis_type == "basic_financial":
                logger.info(f"Executing basic_financial analysis for analysis {analysis_id}")
                turn_results = []
                current_messages = [
                    {"role": "user", "content": aggregated_text if aggregated_text else "No document text available."}
                ]
                if query:
                    current_messages.append({"role": "user", "content": f"User query: {query}"})

                max_turns = 4 
                for turn in range(max_turns):
                    logger.info(f"Basic financial analysis - Turn {turn + 1}")
                    try:
                        api_response = await self.claude_service.execute_tool_interaction_turn(
                            system_prompt=BASIC_FINANCIAL_SYSTEM_PROMPT,
                            messages=current_messages, # type: ignore
                            tools=ALL_TOOLS_DICT 
                        )
                        processed_turn_data = self.claude_service._process_tool_calls(api_response)
                        turn_results.append(processed_turn_data)
                        current_messages.append({"role": "assistant", "content": api_response.content})

                        has_tool_use = any(block.type == 'tool_use' for block in api_response.content)
                        if has_tool_use:
                            for tool_name, tool_results_list in processed_turn_data.get("processed_tool_outputs", {}).items():
                                for res in tool_results_list: 
                                    current_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": res.get("tool_use_id", "missing_tool_use_id"), "content": json.dumps(res.get("output_data")) if res.get("output_data") is not None else "null"}]})
                        if api_response.stop_reason == "stop_sequence" or not has_tool_use:
                            logger.info(f"Basic financial analysis completed in turn {turn + 1}.")
                            break 
                        if turn == max_turns -1:
                             logger.info(f"Basic financial analysis reached max turns.")
                    except ToolSchemaValidationError as e:
                        logger.error(f"Tool schema validation error during basic_financial analysis {analysis_id}, turn {turn+1}: {e}", exc_info=True)
                        raise HTTPException(status_code=422, detail=f"Tool input/output validation failed during basic financial analysis: {str(e)}.")
                    except Exception as e:
                        logger.error(f"Error during basic_financial analysis turn {turn + 1} for analysis {analysis_id}: {e}", exc_info=True)
                        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during turn {turn + 1} of basic financial analysis: {str(e)}")
                
                # Consolidate results from turns for basic_financial
                final_text = "\n".join([res.get("analysis_text", "") for res in turn_results])
                final_charts = [chart for res in turn_results for chart in res.get("visualizations", {}).get("charts", [])]
                final_tables = [table for res in turn_results for table in res.get("visualizations", {}).get("tables", [])]
                final_metrics = [metric for res in turn_results for metric in res.get("metrics", [])]
                result_data = {
                    "analysis_text": final_text,
                    "visualizations": {"charts": final_charts, "tables": final_tables},
                    "metrics": final_metrics
                }

            elif analysis_type == "sentiment_analysis":
                logger.info(f"Executing sentiment_analysis for analysis {analysis_id}")
                turn_results = []
                current_messages = [
                    {"role": "user", "content": aggregated_text if aggregated_text else "No document text available."}
                ]
                if query:
                    current_messages.append({"role": "user", "content": f"User query: {query}"})

                max_turns = 4 # Or a different max_turns suitable for sentiment analysis
                for turn in range(max_turns):
                    logger.info(f"Sentiment analysis - Turn {turn + 1}")
                    try:
                        api_response = await self.claude_service.execute_tool_interaction_turn(
                            system_prompt=SENTIMENT_ANALYSIS_SYSTEM_PROMPT,
                            messages=current_messages, # type: ignore
                            tools=ALL_TOOLS_DICT 
                        )
                        processed_turn_data = self.claude_service._process_tool_calls(api_response)
                        turn_results.append(processed_turn_data)
                        current_messages.append({"role": "assistant", "content": api_response.content})

                        has_tool_use = any(block.type == 'tool_use' for block in api_response.content)
                        if has_tool_use:
                            for tool_name, tool_results_list in processed_turn_data.get("processed_tool_outputs", {}).items():
                                for res in tool_results_list: 
                                    current_messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": res.get("tool_use_id", "missing_tool_use_id"), "content": json.dumps(res.get("output_data")) if res.get("output_data") is not None else "null"}]})
                        if api_response.stop_reason == "stop_sequence" or not has_tool_use:
                            logger.info(f"Sentiment analysis completed in turn {turn + 1}.")
                            break
                        if turn == max_turns -1:
                             logger.info(f"Sentiment analysis reached max turns.")
                    except ToolSchemaValidationError as e:
                        logger.error(f"Tool schema validation error during sentiment_analysis {analysis_id}, turn {turn+1}: {e}", exc_info=True)
                        raise HTTPException(status_code=422, detail=f"Tool input/output validation failed during sentiment analysis: {str(e)}.")
                    except Exception as e:
                        logger.error(f"Error during sentiment_analysis turn {turn + 1} for analysis {analysis_id}: {e}", exc_info=True)
                        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during turn {turn + 1} of sentiment analysis: {str(e)}")
                
                # Consolidate results from turns for sentiment_analysis
                final_text = "\n".join([res.get("analysis_text", "") for res in turn_results])
                final_charts = [chart for res in turn_results for chart in res.get("visualizations", {}).get("charts", [])]
                final_tables = [table for res in turn_results for table in res.get("visualizations", {}).get("tables", [])]
                final_metrics = [metric for res in turn_results for metric in res.get("metrics", [])]
                result_data = {
                    "analysis_text": final_text,
                    "visualizations": {"charts": final_charts, "tables": final_tables},
                    "metrics": final_metrics
                }
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
        result_data: Dict[str, Any],
        user_query: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        logger.info(f"Saving analysis result for {analysis_id}, type {analysis_type}, docs {document_ids}")
        analysis_to_save = AnalysisResult(
            id=analysis_id,
            document_ids=document_ids, # Store list of document IDs
            analysis_type=analysis_type,
            parameters=parameters if parameters else {},
            query_text=user_query,
            result_data=result_data, # This is the direct output from strategy or other methods
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            status="completed" # Or derive status
        )
        try:
            await self.analysis_repository.create_analysis(analysis_to_save.dict())
            logger.info(f"Successfully saved analysis {analysis_id}")

            # Format for return, including metadata
            # This is just an example structure, adapt as needed
            formatted_return = {
                "analysis_id": analysis_id,
                "document_ids": document_ids,
                "analysis_type": analysis_type,
                "status": "completed", # analysis_to_save.status,
                "created_at": analysis_to_save.created_at.isoformat(),
                "query": user_query,
                "parameters": parameters,
                "results": result_data # The core analysis output
            }
            return analysis_id, formatted_return
        except Exception as e:
            logger.error(f"Failed to save analysis {analysis_id}: {e}", exc_info=True)
            # Depending on requirements, might raise an error that translates to HTTP 500
            raise Exception(f"Failed to save analysis result for {analysis_id}")