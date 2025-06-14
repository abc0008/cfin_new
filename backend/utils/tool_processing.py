import json
import logging
from typing import Dict, Optional, Any

from pydantic import ValidationError

from models.visualization import ChartData, TableData
from models.analysis import FinancialMetric
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
    
    # Fix Claude sending JSON strings instead of actual lists/dicts
    if "data" in processed_chart:
        data = processed_chart["data"]
        if isinstance(data, str):
            try:
                # Clean up the JSON string - strip whitespace and handle malformed JSON
                cleaned_data = data.strip()
                
                # Handle common malformed JSON patterns from Claude
                if cleaned_data.endswith(']}') and cleaned_data.count('[') == 1:
                    # Fix extra ]} at the end (should just be ])
                    cleaned_data = cleaned_data[:-2] + ']'
                elif cleaned_data.endswith('}]') and not cleaned_data.endswith('"}]'):
                    # Sometimes Claude sends }] instead of ]
                    pass  # This is actually correct
                
                # Parse JSON string to actual list
                processed_chart["data"] = json.loads(cleaned_data)
                logger.info(f"Successfully parsed chart data from JSON string to list ({len(processed_chart['data'])} items)")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse chart data JSON string: {e}. Original data: {data}")
                # Try to extract JSON array from the string using regex as fallback
                try:
                    import re
                    # Look for array pattern in the string
                    match = re.search(r'\[.*?\]', data, re.DOTALL)
                    if match:
                        clean_json = match.group(0)
                        processed_chart["data"] = json.loads(clean_json)
                        logger.info(f"Successfully parsed chart data using regex fallback ({len(processed_chart['data'])} items)")
                    else:
                        raise ToolSchemaValidationError(f"Could not extract valid JSON array from chart data: {data}")
                except Exception as fallback_error:
                    logger.error(f"Regex fallback also failed: {fallback_error}")
                    raise ToolSchemaValidationError(f"Invalid JSON in chart data: {str(e)}", original_exception=e)
    
    # Similarly handle chartConfig if it's a JSON string
    if "chartConfig" in processed_chart:
        chart_config = processed_chart["chartConfig"]
        if isinstance(chart_config, str):
            try:
                # Clean up the JSON string - strip whitespace and handle malformed JSON
                cleaned_config = chart_config.strip()
                
                # Handle common malformed JSON patterns for objects
                if cleaned_config.endswith('}}') and cleaned_config.count('{') >= 1:
                    # Fix extra } at the end (should just be })
                    cleaned_config = cleaned_config[:-1]
                
                processed_chart["chartConfig"] = json.loads(cleaned_config)
                logger.info("Successfully parsed chart chartConfig from JSON string to dict")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse chart chartConfig JSON string: {e}. Original data: {chart_config}")
                # Try to extract JSON object from the string using regex as fallback
                try:
                    import re
                    # Look for object pattern in the string
                    match = re.search(r'\{.*\}', chart_config, re.DOTALL)
                    if match:
                        clean_json = match.group(0)
                        processed_chart["chartConfig"] = json.loads(clean_json)
                        logger.info("Successfully parsed chart chartConfig using regex fallback")
                    else:
                        raise ToolSchemaValidationError(f"Could not extract valid JSON object from chartConfig: {chart_config}")
                except Exception as fallback_error:
                    logger.error(f"ChartConfig regex fallback also failed: {fallback_error}")
                    raise ToolSchemaValidationError(f"Invalid JSON in chart chartConfig: {str(e)}", original_exception=e)
    
    config = processed_chart.get("config", {})
    if "description" not in config or config["description"] is None:
        config["description"] = config.get("title", "")
    processed_chart["config"] = config

    # Transform data structure to match frontend expectations
    original_data = processed_chart.get("data", [])
    chart_type = processed_chart.get("chartType")
    chart_config_settings = processed_chart.get("chartConfig", {})
    x_axis_key = config.get("xAxisKey")

    transformed_data = []

    # Pie charts don't need xAxisKey - they use 'name' and 'value' fields
    if chart_type == "pie":
        # For pie charts, we'll use 'name' as the category key
        x_axis_key = config.get("xAxisKey", "name")
    else:
        # For other chart types, xAxisKey is required
        if not x_axis_key:
            raise ToolSchemaValidationError(f"xAxisKey is missing in chart config. Input: {tool_input}")

    # Determine if it's a multi-series chart based on data structure
    # Simple charts: data like [{'name': 'A', 'value': 10}] - single metric per item
    # Multi-series charts: data like [{'quarter': 'Q1', 'sales': 100, 'profit': 20}] - multiple metrics per item
    
    series_keys = list(chart_config_settings.keys())
    
    # Check the actual data structure to determine if it's truly multi-series
    is_multi_series = False
    if isinstance(original_data, list) and len(original_data) > 0:
        first_item = original_data[0]
        if isinstance(first_item, dict):
            # Count how many series keys exist in the actual data
            data_series_count = sum(1 for key in series_keys if key in first_item)
            # It's multi-series if multiple series keys exist in the data AND we have multiple series in config
            is_multi_series = data_series_count > 1 and len(series_keys) > 1

    # Transform data to ChartDataItem format (x, y) that the Pydantic model expects
    if isinstance(original_data, list) and len(original_data) > 0:
        first_item = original_data[0]
        
        # Check if data is already in {x, y} format
        if isinstance(first_item, dict) and 'x' in first_item and 'y' in first_item:
            logger.info(f"Chart data already in {{x, y}} format")
            transformed_data = original_data
                
        else:
            # Transform data to {x, y} format required by ChartDataItem model
            logger.info(f"Transforming chart data to {{x, y}} format required by ChartDataItem model")
            
            if chart_type in ["bar", "line", "scatter", "area"] and not is_multi_series:
                # Single series chart - transform to {x, y} format
                # First, check what keys actually exist in the data
                value_key = None
                for item in original_data:
                    possible_y_keys = [k for k, v in item.items() if k != x_axis_key and isinstance(v, (int, float))]
                    if 'value' in possible_y_keys:
                        value_key = 'value'
                        break
                    elif possible_y_keys:
                        value_key = possible_y_keys[0]
                        break
                
                # If no value key found in data, try using series_keys as fallback
                if not value_key and len(series_keys) == 1:
                    # Check if the series key actually exists in the data
                    if original_data and series_keys[0] in original_data[0]:
                        value_key = series_keys[0]
                
                for item in original_data:
                    if x_axis_key in item and value_key and value_key in item:
                        transformed_data.append({
                            "x": item[x_axis_key],  # Always use 'x' for ChartDataItem
                            "y": item[value_key]    # Always use 'y' for ChartDataItem
                        })
                    else:
                        logger.warning(f"Missing x ('{x_axis_key}') or y ('{value_key}') key in item: {item} for single series {chart_type}")
                logger.info(f"Transformed {len(transformed_data)} items for single series {chart_type} chart using value_key='{value_key}'")
                
            elif chart_type == "pie":
                # Pie chart: transform to {x, y} format where x is the category and y is the value
                # First, check what keys actually exist in the data
                y_value_key = None
                for item in original_data:
                    possible_y_keys = [k for k, v in item.items() if k != x_axis_key and isinstance(v, (int, float))]
                    if 'value' in possible_y_keys:
                        y_value_key = 'value'
                        break
                    elif possible_y_keys:
                        y_value_key = possible_y_keys[0]
                        break
                
                # If no value key found in data, try using series_keys as fallback
                if not y_value_key and len(series_keys) == 1:
                    # Check if the series key actually exists in the data
                    if original_data and series_keys[0] in original_data[0]:
                        y_value_key = series_keys[0]

                for item in original_data:
                    if x_axis_key in item and y_value_key and y_value_key in item:
                        transformed_data.append({
                            "x": item[x_axis_key],      # Always use 'x' for ChartDataItem
                            "y": item[y_value_key]    # Always use 'y' for ChartDataItem
                        })
                    else:
                        logger.warning(f"Pie chart: Missing x ('{x_axis_key}') or deduced y key ('{y_value_key}') in item: {item}")
                logger.info(f"Transformed {len(transformed_data)} items for pie chart using y_value_key='{y_value_key}'")

            elif chart_type == "line" and is_multi_series:
                # Multi-series line chart - keep flat format for frontend compatibility
                logger.info(f"Line chart with multiple series ({series_keys}) - keeping flat format")
                # Data is already in the correct format for line charts
                transformed_data = original_data
                
            elif chart_type in ["bar", "multiBar", "stackedArea", "area"] and is_multi_series:
                # Multi-series chart - create PydanticMultiSeriesChartDataItem format
                # If original type was 'bar' but we have multiple series, treat as 'multiBar'
                if chart_type == "bar":
                    logger.info(f"Chart type 'bar' with multiple series_keys ({series_keys}) being treated as 'multiBar'.")
                    processed_chart["chartType"] = "multiBar" # Update chartType
                
                for series_key in series_keys:
                    series_name = chart_config_settings[series_key].get("label", series_key)
                    current_series_data = []
                    for item in original_data:
                        if x_axis_key in item and series_key in item:
                            current_series_data.append({
                                "x": item[x_axis_key],  # Always use 'x' for ChartDataItem
                                "y": item[series_key]   # Always use 'y' for ChartDataItem
                            })
                        else:
                            logger.warning(f"Missing x ('{x_axis_key}') or series key ('{series_key}') in item: {item} for multi-series chart")
                    transformed_data.append({
                        "name": series_name,
                        "data": current_series_data
                    })
                logger.info(f"Transformed {len(transformed_data)} series for multi-series {chart_type} chart")
                
            else:
                # Fallback: try to intelligently transform unknown chart types
                logger.warning(f"Unhandled chart data transformation for chartType '{chart_type}' with is_multi_series={is_multi_series}. Attempting intelligent transformation.")
                if not is_multi_series:
                    # Treat as single series - first check what keys actually exist in the data
                    value_key = None
                    for item in original_data:
                        possible_y_keys = [k for k, v in item.items() if k != x_axis_key and isinstance(v, (int, float))]
                        if 'value' in possible_y_keys:
                            value_key = 'value'
                            break
                        elif possible_y_keys:
                            value_key = possible_y_keys[0]
                            break
                    
                    # If no value key found in data, try using series_keys as fallback
                    if not value_key and len(series_keys) == 1:
                        # Check if the series key actually exists in the data
                        if original_data and series_keys[0] in original_data[0]:
                            value_key = series_keys[0]
                    
                    for item in original_data:
                        if x_axis_key in item and value_key and value_key in item:
                            transformed_data.append({
                                "x": item[x_axis_key],
                                "y": item[value_key]
                            })
                else:
                    # Keep original if no transformation logic applies
                    transformed_data = original_data
    else:
        # No data to transform
        transformed_data = original_data

    processed_chart["data"] = transformed_data

    # Ensure chartConfig has complete MetricConfig objects with default values
    chart_config_settings = processed_chart.get("chartConfig", {})
    for metric_key, metric_config in chart_config_settings.items():
        if isinstance(metric_config, dict):
            # Ensure all required MetricConfig fields have default values
            metric_config.setdefault("unit", "")
            metric_config.setdefault("formatter", "")
            metric_config.setdefault("precision", 2)
            # label and color should already be provided by Claude
    
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
    
    allowed_table_types = ["simple", "matrix", "comparison", "summary", "detailed"]
    current_table_type = processed_table.get("tableType")
    
    if current_table_type not in allowed_table_types:
        logger.warning(f"Invalid tableType '{current_table_type}' received from Claude. Defaulting to 'comparison'. Input: {tool_input}")
        processed_table["tableType"] = "comparison"
    
    # Fix Claude sending JSON strings instead of actual lists
    if "data" in processed_table:
        data = processed_table["data"]
        if isinstance(data, str):
            try:
                # Clean up the JSON string - strip whitespace and handle malformed JSON
                cleaned_data = data.strip()
                
                # Handle common malformed JSON patterns from Claude
                if cleaned_data.endswith(']}') and cleaned_data.count('[') == 1:
                    # Fix extra ]} at the end (should just be ])
                    cleaned_data = cleaned_data[:-2] + ']'
                elif cleaned_data.endswith('}]') and not cleaned_data.endswith('"}]'):
                    # Sometimes Claude sends }] instead of ]
                    pass  # This is actually correct
                
                # Parse JSON string to actual list
                processed_table["data"] = json.loads(cleaned_data)
                logger.info(f"Successfully parsed table data from JSON string to list ({len(processed_table['data'])} items)")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse table data JSON string: {e}. Original data: {data}")
                # Try to extract JSON array from the string using regex as fallback
                try:
                    import re
                    # Look for array pattern in the string
                    match = re.search(r'\[.*?\]', data, re.DOTALL)
                    if match:
                        clean_json = match.group(0)
                        processed_table["data"] = json.loads(clean_json)
                        logger.info(f"Successfully parsed table data using regex fallback ({len(processed_table['data'])} items)")
                    else:
                        raise ToolSchemaValidationError(f"Could not extract valid JSON array from table data: {data}")
                except Exception as fallback_error:
                    logger.error(f"Regex fallback also failed: {fallback_error}")
                    raise ToolSchemaValidationError(f"Invalid JSON in table data: {str(e)}", original_exception=e)
    
    # Similarly handle chartConfig if it's a JSON string
    if "chartConfig" in processed_table:
        chart_config = processed_table["chartConfig"]
        if isinstance(chart_config, str):
            try:
                processed_table["chartConfig"] = json.loads(chart_config)
                logger.info("Successfully parsed chartConfig from JSON string to dict")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse chartConfig JSON string: {e}. Data: {chart_config}")
                raise ToolSchemaValidationError(f"Invalid JSON in chartConfig: {str(e)}", original_exception=e)
    
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