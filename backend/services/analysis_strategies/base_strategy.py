#!/usr/bin/env python3
"""
Base class for analysis strategies.

This module defines the abstract base class AnalysisStrategy that all concrete analysis 
strategies must inherit from. It establishes a common interface for executing different 
types of financial document analysis.

Upstream Dependencies:
- models.database_models.Document: Database model for document entities
- pdf_processing.api_service.ClaudeService: Core AI service for Claude API interactions

Downstream Dependencies:
- Used by all concrete strategy implementations (basic_financial_strategy.py, 
  comprehensive_strategy.py, financial_template_strategy.py, sentiment_analysis_strategy.py)
- Instantiated by services.analysis_service.AnalysisService which routes analysis requests
  to the appropriate strategy based on analysis type

Key Responsibilities:
- Define the execute() method signature that all strategies must implement
- Provide common initialization pattern with ClaudeService dependency injection
- Establish standard return format for analysis results (analysis_text, visualizations, metrics)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from models.database_models import Document
from pdf_processing.api_service import ClaudeService
import logging

logger = logging.getLogger(__name__)


class AnalysisStrategy(ABC):
    """
    Abstract base class for all analysis strategies.
    Defines a common interface for executing an analysis type.
    """

    def __init__(self, claude_service: ClaudeService):
        """
        Initializes the strategy with a ClaudeService instance.

        Args:
            claude_service: An instance of the ClaudeService for AI interactions.
        """
        self.claude_service = claude_service

    @abstractmethod
    async def execute(
        self,
        aggregated_text: str,
        documents: List[Document], 
        parameters: Dict[str, Any],
        user_query: Optional[str],
        pdf_base64_contents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Executes the analysis strategy.

        This method must be implemented by concrete strategy classes.
        It should orchestrate the interaction with ClaudeService and other
        necessary logic to perform the specific analysis.

        Args:
            aggregated_text: Aggregated text content from the input documents.
            documents: A list of Document objects.
            parameters: Analysis parameters, including any knowledge base or user settings.
            user_query: The user's query for the analysis, if provided.
            pdf_base64_contents: Optional list of base64 encoded PDF contents.

        Returns:
            A dictionary containing the analysis results, adhering to the standard structure:
            {
                "analysis_text": str,
                "visualizations": {
                    "charts": List[ChartData],
                    "tables": List[TableData]
                },
                "metrics": List[FinancialMetric]
            }
        """
        pass 