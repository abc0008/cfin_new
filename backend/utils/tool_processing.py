import json
import logging
from typing import Dict, List, Optional, Any

from pydantic import ValidationError

from ..models.visualization import ChartData, TableData
from ..models.analysis import FinancialMetric
from .exceptions import ToolSchemaValidationError

logger = logging.getLogger(__name__)

def process_financial_metric_input(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    required_keys = ["category", "name", "period", "value", "unit"]
    if not isinstance(tool_input, dict):
        raise ToolSchemaValidationError(f"Financial metric input is not a dictionary: {type(tool_input)}")
    expected_input_keys = {
        "category": "category", "name": "name", "period": "period",
        "value": "value", "unit": "unit", "isEstimated": "isEstimated"
    }
    processed_metric = {}
    missing_required_keys = []
    for pydantic_key, tool_key in expected_input_keys.items():
        if tool_key in tool_input:
            processed_metric[pydantic_key] = tool_input[tool_key]
        elif pydantic_key in required_keys:
            missing_required_keys.append(tool_key)
    if missing_required_keys:
        raise ToolSchemaValidationError(f"Financial metric input missing required keys: {missing_required_keys}. Input: {tool_input}")
    if "value" in processed_metric and not isinstance(processed_metric["value"], (int, float)):
        if isinstance(processed_metric["value"], str):
            try:
                processed_metric["value"] = float(processed_metric["value"].replace(',', ''))
            except ValueError as e:
                raise ToolSchemaValidationError(f"Could not convert metric value '{processed_metric['value']}' to float. Input: {tool_input}", original_exception=e)
        else:
            raise ToolSchemaValidationError(f"Financial metric 'value' is not a number: {processed_metric['value']}. Input: {tool_input}")
    if "isEstimated" not in processed_metric or not isinstance(processed_metric.get("isEstimated"), bool):
        processed_metric["isEstimated"] = False
    try:
        validated_metric = FinancialMetric(**processed_metric)
        logger.info(f"Successfully processed financial metric: {validated_metric.name}")
        return validated_metric.model_dump(by_alias=True)
    except ValidationError as e:
        logger.error(f"FinancialMetric Pydantic validation failed for {processed_metric.get('name', 'Unknown Metric')}: {e}. Input: {tool_input}")
        raise ToolSchemaValidationError(f"Schema validation failed for financial metric '{processed_metric.get('name', 'Unknown Metric')}': {str(e)}", original_exception=e)

def process_chart_input(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_input, dict):
        raise ToolSchemaValidationError(f"Chart input is not a dictionary: {type(tool_input)}")
    if not all(key in tool_input for key in ["chartType", "config", "data", "chartConfig"]):
        raise ToolSchemaValidationError(f"Chart input missing required keys (chartType, config, data, chartConfig). Input: {tool_input}")
    processed_chart = tool_input.copy()
    config = processed_chart.get("config", {})
    if "description" not in config or config["description"] is None:
        config["description"] = config.get("title", "")
    processed_chart["config"] = config
    try:
        validated_chart = ChartData(**processed_chart)
        logger.info(f"Successfully processed chart: {validated_chart.config.title if validated_chart.config else 'Untitled Chart'}")
        return validated_chart.model_dump(by_alias=True)
    except ValidationError as e:
        chart_title = tool_input.get('config', {}).get('title', 'Unknown Chart')
        logger.error(f"ChartData Pydantic validation failed for '{chart_title}': {e}. Input: {json.dumps(tool_input, indent=2)}")
        raise ToolSchemaValidationError(f"Schema validation failed for chart '{chart_title}': {str(e)}", original_exception=e)

def process_table_input(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    processed_table = tool_input.copy()
    if "tableType" not in processed_table or processed_table.get("tableType") is None:
        logger.warning(f"Missing 'tableType' in tool_input from Claude. Defaulting to 'comparison'. Input: {tool_input}")
        processed_table["tableType"] = "comparison"
    allowed_table_types = ["simple", "matrix", "comparison"]
    current_table_type = processed_table.get("tableType")
    if current_table_type not in allowed_table_types:
        logger.warning(f"Invalid tableType '{current_table_type}' received from Claude. Defaulting to 'comparison'. Input: {tool_input}")
        processed_table["tableType"] = "comparison"
    try:
        config = processed_table.get("config", {})
        if "description" not in config or config["description"] is None:
            config["description"] = config.get("title", "")
        processed_table["config"] = config
        if "columns" in config and isinstance(config["columns"], list):
            for column_config_item in config["columns"]:
                if isinstance(column_config_item, dict):
                    if column_config_item.get("header") is None:
                        column_config_item["header"] = column_config_item.get("label", "")
                    if column_config_item.get("format") is None:
                        column_config_item["format"] = "text"
                    if column_config_item.get("width") is None:
                        if column_config_item.get("key") == "metric":
                            column_config_item["width"] = 200
                        else:
                            column_config_item["width"] = 150
                    if column_config_item.get("formatter") is None:
                        column_config_item["formatter"] = ""
        validated_table = TableData(**processed_table)
        logger.info(f"Successfully processed table: {validated_table.config.title if validated_table.config else 'Untitled Table'}")
        return validated_table.model_dump(by_alias=True)
    except ValidationError as e:
        table_title = tool_input.get('config', {}).get('title', 'Unknown Table')
        logger.error(f"TableData Pydantic validation failed for '{table_title}': {e}. Input: {json.dumps(tool_input, indent=2)}")
        raise ToolSchemaValidationError(f"Schema validation failed for table '{table_title}': {str(e)}", original_exception=e)

def process_visualization_input(tool_name: str, tool_input: Dict[str, Any], block_id: str) -> Optional[Dict[str, Any]]:
    try:
        if tool_name == "generate_graph_data":
            return process_chart_input(tool_input)
        elif tool_name == "generate_table_data":
            return process_table_input(tool_input)
        elif tool_name == "generate_financial_metric":
            return process_financial_metric_input(tool_input)
        else:
            logger.warning(f"Unsupported tool: {tool_name} (ID: {block_id})")
            return None
    except Exception as e:
        logger.error(f"Error processing {tool_name} input (ID: {block_id}): {e}")
        return None 