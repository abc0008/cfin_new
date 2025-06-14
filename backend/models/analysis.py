from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, ConfigDict

# Assuming ChartData and TableData will be imported or defined if not already
# For now, let's use Any as a placeholder if they are not in the current context of this file.
# If they are in models.visualization, they should be imported:
from models.visualization import ChartData, TableData

# Utility for camelCase aliasing
def to_camel(string: str) -> str:
    parts = string.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:]) if len(parts) > 1 else string

class FinancialRatio(BaseModel):
    name: str
    value: float
    description: str
    benchmark: Optional[float] = None
    trend: Optional[float] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class FinancialMetric(BaseModel):
    category: str
    name: str
    period: str
    value: float
    unit: str
    is_estimated: bool = Field(default=False, alias="isEstimated")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class ComparativePeriod(BaseModel):
    metric: str
    current_period: str = Field(alias="currentPeriod")
    previous_period: str = Field(alias="previousPeriod")
    current_value: float = Field(alias="currentValue")
    previous_value: float = Field(alias="previousValue")
    change: float
    percent_change: float = Field(alias="percentChange")
    trend: Literal["positive", "negative", "neutral"] = "neutral"

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class AnalysisResult(BaseModel):
    # This model seems to be for internal service an_d repository use,
    # and its fields are already snake_case with camelCase aliases. This is good.
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_ids: List[str] = Field(alias="documentIds")
    analysis_type: str = Field(alias="analysisType")
    timestamp: datetime = Field(default_factory=datetime.now)
    metrics: List[FinancialMetric] = Field(default_factory=list)
    ratios: List[FinancialRatio] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
    visualization_data: Dict[str, Any] = Field(default_factory=dict, alias="visualizationData")
    citation_references: Dict[str, str] = Field(default_factory=dict, alias="citationReferences")
    comparative_periods: List[ComparativePeriod] = Field(default_factory=list, alias="comparativePeriods")
    analysis_text: Optional[str] = Field(default=None, alias="analysisText")
    # Adding fields that might be in result_data from service, to be used by AnalysisApiResponse
    document_type: Optional[str] = Field(default=None, alias="documentType") 
    periods: List[str] = Field(default_factory=list)
    query: Optional[str] = None


    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class AnalysisRequest(BaseModel):
    analysis_type: str = Field(alias="analysisType")
    document_ids: List[str] = Field(alias="documentIds")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    query: Optional[str] = None
    custom_knowledge_base: Optional[str] = Field(default=None, alias="customKnowledgeBase")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# --- Moved and Refactored API Response Models ---

class VisualizationDataResponse(BaseModel):
    charts: List[ChartData] = Field(default_factory=list)
    tables: List[TableData] = Field(default_factory=list)
    # Using snake_case for Python attributes, will be aliased to camelCase
    monetary_values: Optional[List[Dict[str, Any]]] = Field(default=None, alias="monetaryValues")
    percentages: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class AnalysisApiResponse(BaseModel):
    id: str
    document_ids: List[str] = Field(alias="documentIds")
    analysis_type: str = Field(alias="analysisType")
    timestamp: str # Keep as string for ISO format from routes
    analysis_text: Optional[str] = Field(default=None, alias="analysisText")
    visualization_data: VisualizationDataResponse = Field(alias="visualizationData")
    metrics: List[FinancialMetric] = Field(default_factory=list)
    ratios: List[FinancialRatio] = Field(default_factory=list)
    comparative_periods: List[ComparativePeriod] = Field(default_factory=list, alias="comparativePeriods")
    insights: List[str] = Field(default_factory=list)
    citation_references: Dict[str, str] = Field(default_factory=dict, alias="citationReferences")
    document_type: Optional[str] = Field(default=None, alias="documentType")
    periods: List[str] = Field(default_factory=list)
    query: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)