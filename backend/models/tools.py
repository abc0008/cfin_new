from typing import Dict, List, Optional, Any, Literal, Union, Callable
from pydantic import BaseModel, Field, RootModel
import logging
from utils import tool_processing

logger = logging.getLogger(__name__)

# Utility for camelCase aliasing
def to_camel(string: str) -> str:
    parts = string.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:]) if len(parts) > 1 else string

# Base Tool Schema
class ToolSchema(BaseModel):
    """Base model for tool definitions to be used with Claude API."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    cache_control: Optional[Dict[str, str]] = Field(default=None, alias="cacheControl", description="Optional cache control settings")
    processor: Optional[Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]] = Field(default=None, exclude=True)

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

# --- New Tool Registration Logic (PlanPlanPlan.md item 2) ---
ALL_TOOLS_SCHEMAS: list[ToolSchema] = []
CLAUDE_API_TOOLS_LIST: list[dict[str, Any]] = []

def register_tool(tool: ToolSchema) -> None:
    ALL_TOOLS_SCHEMAS.append(tool)
    # Construct the schema for Claude API, ensuring only relevant fields are included
    api_schema_dict = tool.model_dump(
        by_alias=True, 
        exclude_none=True, 
        include={'name', 'description', 'input_schema', 'cache_control'}
    )

    # Ensure the key is 'input_schema' as expected by Anthropic,
    # overriding Pydantic's camelCase aliasing for this specific field.
    if 'inputSchema' in api_schema_dict and 'input_schema' not in api_schema_dict:
        api_schema_dict['input_schema'] = api_schema_dict.pop('inputSchema')
    
    CLAUDE_API_TOOLS_LIST.append(api_schema_dict)

# --- Chart Generation Tool ---

class ChartMetricConfig(BaseModel):
    """Configuration for a single metric/series in a chart."""
    label: str
    color: Optional[str] = None
    unit: Optional[str] = None
    formatter: Optional[str] = None
    precision: Optional[int] = None

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class ChartConfig(BaseModel):
    title: str
    description: Optional[str] = None
    x_axis_key: Optional[str] = Field(default="name", alias="xAxisKey")
    y_axis_key: Optional[str] = Field(default=None, alias="yAxisKey")
    x_axis_label: Optional[str] = Field(default=None, alias="xAxisLabel")
    y_axis_label: Optional[str] = Field(default=None, alias="yAxisLabel")
    show_legend: bool = Field(default=True, alias="showLegend")
    legend_position: Optional[Literal["top", "bottom", "left", "right"]] = Field(default="bottom", alias="legendPosition")
    show_grid: Optional[bool] = Field(default=True, alias="showGrid")
    stack: Optional[bool] = Field(default=False)
    colors: Optional[List[str]] = None
    footer: Optional[str] = None
    total_label: Optional[str] = Field(default=None, alias="totalLabel")

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class ChartDataItem(RootModel):
    root: Dict[str, Union[str, float, int, None]]

class ChartGenerationInputSchema(BaseModel):
    chart_type: Literal["bar", "multiBar", "line", "pie", "area", "stackedArea", "scatter"] = Field(..., alias="chartType")
    config: ChartConfig
    data: List[Dict[str, Any]]
    chart_config: Dict[str, ChartMetricConfig] = Field(..., alias="chartConfig")

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class ChartGenerationTool(ToolSchema):
    name: str = "generate_graph_data"
    description: str = """Use this tool to generate structured JSON data for financial charts and graphs (bar, line, pie, area, scatter).\nSpecify the chartType, provide general config (title, axis labels), the data array, and chartConfig for each series/metric.\nThe 'data' array objects must contain a key matching 'config.xAxisKey' and keys matching the keys used in 'chartConfig'.\nFor pie charts, 'data' objects typically have 'name' and 'value' keys."""
    input_schema: Dict[str, Any] = ChartGenerationInputSchema.model_json_schema()

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

register_tool(ChartGenerationTool()) # Register after definition

# --- Table Generation Tool ---

class TableColumnConfig(BaseModel):
    key: str
    label: str
    header: Optional[str] = None
    format: Optional[Literal["number", "currency", "percentage", "text", "date"]] = "text"
    width: Optional[int] = None
    align: Optional[Literal["left", "center", "right"]] = "left"

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class TableConfig(BaseModel):
    title: str
    description: Optional[str] = None
    footer: Optional[str] = None
    columns: List[TableColumnConfig]
    show_row_numbers: Optional[bool] = Field(default=False, alias="showRowNumbers")
    sortable: Optional[bool] = True
    pagination: Optional[bool] = True
    page_size: Optional[int] = Field(default=10, alias="pageSize")

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class TableGenerationInputSchema(BaseModel):
    table_type: Literal["simple", "matrix", "comparison", "detailed"] = Field(default="simple", alias="tableType")
    config: TableConfig
    data: List[Dict[str, Any]]

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

class TableGenerationTool(ToolSchema):
    name: str = "generate_table_data"
    description: str = """Use this tool to generate structured JSON data for creating financial data tables.\nSpecify the tableType (e.g., 'comparison', 'detailed'), provide config (title, column definitions), and the data array.\nThe 'data' objects' keys must match the 'key' values defined in 'config.columns'.\nUse appropriate 'format' values in column definitions (number, currency, percentage, text, date)."""
    input_schema: Dict[str, Any] = TableGenerationInputSchema.model_json_schema()

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True

register_tool(TableGenerationTool()) # Register after definition

# Keep the existing FinancialMetricGenerationTool and ComparativePeriodGenerationTool
class FinancialMetricGenerationTool(ToolSchema):
    """Tool for generating financial metrics."""
    name: str = "generate_financial_metric"
    description: str = """Generate structured financial metrics with period information.
    
Metrics should include:
- Category: The metric category (Revenue, Expenses, Assets, etc.)
- Name: The specific metric name
- Period: The time period the metric applies to
- Value: The numeric value
- Unit: The unit of measurement (%, $, etc.)
- IsEstimated: Whether the value is estimated or directly from the document
"""
    
    input_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "The category of the financial metric"
            },
            "name": {
                "type": "string",
                "description": "The name of the financial metric"
            },
            "period": {
                "type": "string",
                "description": "The time period the metric applies to"
            },
            "value": {
                "type": "number",
                "description": "The value of the metric"
            },
            "unit": {
                "type": "string",
                "description": "The unit of measurement (%, $, etc.)"
            },
            "isEstimated": {
                "type": "boolean",
                "description": "Whether the value is estimated"
            }
        },
        "required": ["category", "name", "period", "value"]
    }

register_tool(FinancialMetricGenerationTool()) # Register after definition

class ComparativePeriodGenerationTool(ToolSchema):
    """Tool for generating comparative period data."""
    name: str = "generate_comparative_period"
    description: str = """Generate structured data for period-over-period comparisons.
    
Comparative periods should include:
- Metric: The metric being compared
- CurrentPeriod: The current time period
- PreviousPeriod: The previous time period
- CurrentValue: The value in the current period
- PreviousValue: The value in the previous period
- Change: The absolute change
- PercentChange: The percentage change
- Trend: Whether the change is positive, negative, or neutral
"""
    
    input_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "metric": {
                "type": "string",
                "description": "The metric being compared"
            },
            "currentPeriod": {
                "type": "string",
                "description": "The current time period"
            },
            "previousPeriod": {
                "type": "string",
                "description": "The previous time period"
            },
            "currentValue": {
                "type": "number",
                "description": "The value in the current period"
            },
            "previousValue": {
                "type": "number",
                "description": "The value in the previous period"
            },
            "change": {
                "type": "number",
                "description": "The absolute change"
            },
            "percentChange": {
                "type": "number",
                "description": "The percentage change"
            },
            "trend": {
                "type": "string",
                "enum": ["positive", "negative", "neutral"],
                "description": "The trend direction"
            }
        },
        "required": ["metric", "currentPeriod", "previousPeriod", "currentValue", "previousValue"]
    }

register_tool(ComparativePeriodGenerationTool()) # Register after definition

# List of all available tools for Claude - NO LONGER POPULATED DIRECTLY
# ALL_TOOLS_SCHEMAS: List[ToolSchema] = [
#     ChartGenerationTool(),
#     TableGenerationTool(),
#     FinancialMetricGenerationTool(),
#     ComparativePeriodGenerationTool()
# ]

# Create dictionary for easier lookup by name, mapping to ToolSchema instances
# This remains, but now iterates over the registered ALL_TOOLS_SCHEMAS
ALL_TOOLS_DICT: Dict[str, ToolSchema] = {}
for tool_schema_instance in ALL_TOOLS_SCHEMAS: # Iterates over dynamically populated list
    if tool_schema_instance.name == "generate_graph_data":
        tool_schema_instance.processor = tool_processing.process_chart_input
    elif tool_schema_instance.name == "generate_table_data":
        tool_schema_instance.processor = tool_processing.process_table_input
    elif tool_schema_instance.name == "generate_financial_metric":
        tool_schema_instance.processor = tool_processing.process_financial_metric_input
    ALL_TOOLS_DICT[tool_schema_instance.name] = tool_schema_instance

# Legacy name for backward compatibility, now points to the new dict structure if appropriate,
# or the list of dicts if that's what downstream code expects from 'DEFAULT_TOOLS'.
# Given ClaudeService.execute_tool_interaction_turn takes Optional[List[ToolSchema]],
# DEFAULT_TOOLS should probably be List[ToolSchema] or the list of dicts.
# The variable ClaudeService.ALL_TOOLS_DICT used in init should be CLAUDE_API_TOOLS_LIST.
DEFAULT_TOOLS = ALL_TOOLS_SCHEMAS

logger.info(f"Loaded {len(ALL_TOOLS_SCHEMAS)} tools for Claude API.")
logger.info(f"Tool names: {[tool.name for tool in ALL_TOOLS_SCHEMAS]}")

# Example Usage (for testing schema generation)
if __name__ == "__main__":
    chart_schema = ChartGenerationTool().model_dump_json(indent=2)
    print("Chart Generation Tool Schema:")
    print(chart_schema)

    table_schema = TableGenerationTool().model_dump_json(indent=2)
    print("\nTable Generation Tool Schema:")
    print(table_schema) 