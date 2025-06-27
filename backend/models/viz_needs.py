"""
Visualization needs classification models for determining what types of 
visualizations and analysis should be generated for a given user query.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class ChartType(str, Enum):
    """Supported chart types for financial visualizations."""
    LINE = "line"
    BAR = "bar" 
    AREA = "area"
    STACKED_AREA = "stackedArea"
    PIE = "pie"
    SCATTER = "scatter"

class TableType(str, Enum):
    """Supported table types for financial data."""
    DETAILED = "detailed"
    COMPARISON = "comparison"
    SUMMARY = "summary"

class MetricCategory(str, Enum):
    """Categories of financial metrics."""
    PROFITABILITY = "profitability"
    LIQUIDITY = "liquidity" 
    CREDIT_QUALITY = "credit_quality"
    GROWTH = "growth"
    EFFICIENCY = "efficiency"

class AnalysisFocus(str, Enum):
    """Focus areas for analysis and explanation."""
    TRENDS = "trends"
    COMPARISONS = "comparisons"
    SUMMARY = "summary"
    DEEP_DIVE = "deep_dive"
    PERFORMANCE = "performance"

class VizNeeds(BaseModel):
    """
    Classification of visualization and analysis needs for a user query.
    Determines what should be generated alongside the streaming text response.
    """
    
    # Chart requirements
    needs_charts: bool = Field(
        default=False,
        description="Whether any charts should be generated"
    )
    
    chart_types: List[ChartType] = Field(
        default_factory=list,
        description="Specific chart types to generate (line, bar, area, etc.)"
    )
    
    # Table requirements  
    needs_tables: bool = Field(
        default=False,
        description="Whether any tables should be generated"
    )
    
    table_types: List[TableType] = Field(
        default_factory=list,
        description="Specific table types to generate (detailed, comparison, summary)"
    )
    
    # Metrics requirements
    needs_metrics: bool = Field(
        default=False, 
        description="Whether key financial metrics should be calculated and displayed"
    )
    
    metric_categories: List[MetricCategory] = Field(
        default_factory=list,
        description="Categories of metrics to focus on (profitability, liquidity, etc.)"
    )
    
    # Analysis focus
    analysis_focus: AnalysisFocus = Field(
        default=AnalysisFocus.SUMMARY,
        description="Primary focus of the analysis and explanation"
    )
    
    # Context
    reasoning: Optional[str] = Field(
        default=None,
        description="Brief explanation of why these visualizations were chosen"
    )
    
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence level in the classification (0.0 to 1.0)"
    )

    @property
    def needs_any_visualization(self) -> bool:
        """Returns True if any visualization is needed."""
        return self.needs_charts or self.needs_tables or self.needs_metrics
    
    @property
    def is_simple_text_only(self) -> bool:
        """Returns True if only text response is needed."""
        return not self.needs_any_visualization

class DocumentContext(BaseModel):
    """Context about the documents available for analysis."""
    
    has_financial_data: bool = Field(
        default=False,
        description="Whether documents contain financial data"
    )
    
    document_types: List[str] = Field(
        default_factory=list,
        description="Types of documents available (balance_sheet, income_statement, etc.)"
    )
    
    time_periods: List[str] = Field(
        default_factory=list,
        description="Time periods covered in the documents"
    )
    
    data_categories: List[str] = Field(
        default_factory=list,
        description="Categories of data available (loans, deposits, revenue, etc.)"
    )

class ClassificationRequest(BaseModel):
    """Request for classifying visualization needs."""
    
    user_query: str = Field(
        description="The user's query/message"
    )
    
    document_context: DocumentContext = Field(
        description="Context about available documents"
    )
    
    conversation_history: Optional[List[str]] = Field(
        default=None,
        description="Recent conversation history for context"
    )