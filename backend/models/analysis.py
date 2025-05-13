from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, UUID4, ConfigDict

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

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class FinancialMetric(BaseModel):
    category: str
    name: str
    period: str
    value: float
    unit: str
    is_estimated: bool = Field(default=False, alias="isEstimated")

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class ComparativePeriod(BaseModel):
    metric: str
    current_period: str = Field(alias="currentPeriod")
    previous_period: str = Field(alias="previousPeriod")
    current_value: float = Field(alias="currentValue")
    previous_value: float = Field(alias="previousValue")
    change: float
    percent_change: float = Field(alias="percentChange")
    trend: Literal["positive", "negative", "neutral"] = "neutral"

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class AnalysisResult(BaseModel):
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

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class AnalysisRequest(BaseModel):
    analysis_type: str = Field(alias="analysisType")
    document_ids: List[str] = Field(alias="documentIds")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    query: Optional[str] = None

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True