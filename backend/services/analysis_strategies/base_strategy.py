from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from models.database_models import Document
from models.visualization import ChartData, TableData
from models.analysis import FinancialMetric
from cfin.backend.pdf_processing.api_service import ClaudeService


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