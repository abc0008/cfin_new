from typing import Dict, List, Optional, Any, Literal, Union
from pydantic import BaseModel, Field, ConfigDict
import uuid
from datetime import datetime

# Utility for camelCase aliasing
def to_camel(string: str) -> str:
    parts = string.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:]) if len(parts) > 1 else string

class MetricConfig(BaseModel):
    """Configuration for a metric in a chart."""
    label: str
    unit: Optional[str] = None  # Added for frontend consistency
    color: Optional[str] = None
    formatter: Optional[str] = None  # Added for frontend formatting
    precision: Optional[int] = None  # Added for frontend number formatting

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class ChartConfig(BaseModel):
    """Configuration for a chart."""
    title: str
    description: str
    subtitle: Optional[str] = None  # Added for frontend consistency
    x_axis_label: Optional[str] = Field(None, alias="xAxisLabel")
    y_axis_label: Optional[str] = Field(None, alias="yAxisLabel")
    x_axis_key: Optional[str] = Field(None, alias="xAxisKey")
    trend: Optional[Dict[str, Any]] = None
    footer: Optional[str] = None
    total_label: Optional[str] = Field(None, alias="totalLabel")
    show_legend: bool = Field(True, alias="showLegend")
    legend_position: Optional[Literal["top", "bottom", "left", "right"]] = Field("bottom", alias="legendPosition")
    show_grid: Optional[bool] = Field(True, alias="showGrid")
    height: Optional[int] = None  # Added for frontend sizing
    width: Optional[int] = None  # Added for frontend sizing
    stack: Optional[bool] = False  # Added for frontend stacked charts

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class ChartData(BaseModel):
    """Base model for chart data."""
    chart_type: Literal["bar", "multiBar", "line", "pie", "area", "stackedArea"] = Field(..., alias="chartType")
    config: ChartConfig
    data: List[Dict[str, Any]]
    chart_config: Dict[str, MetricConfig] = Field(..., alias="chartConfig")
    
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        validate_assignment=True,
        protected_namespaces=()
    )

class TableColumn(BaseModel):
    """Definition of a table column."""
    key: str
    label: str  # Backend uses 'label'
    header: Optional[str] = None  # Added for frontend (uses 'header' instead of 'label')
    format: Optional[Literal["number", "currency", "percentage", "text"]] = None
    width: Optional[int] = None  # Added for frontend column sizing
    align: Optional[Literal["left", "center", "right"]] = "left"  # Added for frontend text alignment
    formatter: Optional[str] = None  # Added for frontend custom formatting

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class TableConfig(BaseModel):
    """Configuration for a table."""
    title: str
    description: str
    subtitle: Optional[str] = None  # Added for frontend consistency
    footer: Optional[str] = None
    columns: List[TableColumn]
    show_row_numbers: Optional[bool] = Field(False, alias="showRowNumbers")
    sortable: Optional[bool] = True  # Added for frontend sorting functionality
    pagination: Optional[bool] = True  # Added for frontend pagination
    page_size: Optional[int] = Field(10, alias="pageSize")
    height: Optional[int] = None  # Added for frontend sizing
    width: Optional[int] = None  # Added for frontend sizing

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class TableData(BaseModel):
    """Model for table data."""
    table_type: Literal["simple", "matrix", "comparison"] = Field(..., alias="tableType")
    config: TableConfig
    data: List[Dict[str, Any]]
    
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        validate_assignment=True,
        protected_namespaces=()
    )

class VisualizationData(BaseModel):
    """Container for different visualization types."""
    charts: Optional[List[ChartData]] = Field(default_factory=list)
    tables: Optional[List[TableData]] = Field(default_factory=list)
    
    # Common chart types expected by frontend
    monetary_values: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="monetaryValues")
    percentages: Optional[Dict[str, Any]] = Field(default_factory=dict)
    keyword_frequency: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="keywordFrequency")
    
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        validate_assignment=True,
        protected_namespaces=()
    ) 