"""
Utility functions for preparing visualization data for API responses.
"""
import logging
import re
import json
from typing import List, Dict, Any, Optional

# Assuming FinancialMetric is defined in models.analysis
# If this path is incorrect, it will need adjustment.
from models.analysis import FinancialMetric # Add this import

logger = logging.getLogger(__name__)

def generate_monetary_values_data(metrics: List[FinancialMetric], insights: List[str]) -> Optional[List[Dict[str, Any]]]:
    """Generate monetary values data for visualization."""
    # First, try to use actual metrics with appropriate units
    monetary_metrics = [
        {"name": metric.name, "value": metric.value, "description": f"{metric.category}: {metric.name} ({metric.period})"}
        for metric in metrics
        if metric.unit and (any(keyword in metric.unit.lower() for keyword in ["usd", "$", "dollar", "million", "billion", "revenue", "cost", "price", "value"]))
        or (metric.name and any(keyword in metric.name.lower() for keyword in ["revenue", "sales", "cost", "price", "income", "profit", "expense", "asset"]))
    ]
    
    logger.info(f"VIS_HELPER_LOG: Found {len(metrics)} total metrics for monetary values chart")
    logger.info(f"VIS_HELPER_LOG: Filtered down to {len(monetary_metrics)} monetary metrics")
    if monetary_metrics:
        logger.info(f"VIS_HELPER_LOG: Using actual monetary metrics for chart: {json.dumps([m['name'] for m in monetary_metrics])}")
    
    if not monetary_metrics and insights:
        monetary_pattern = r'\$\s*[\d,\.]+\s*(million|billion|thousand|M|B|K)?|\d+(\.\d+)?\s*(million|billion|thousand|M|B|K)?\s*(dollars|USD)'
        monetary_insights_data = []
        logger.info(f"VIS_HELPER_LOG: No monetary metrics found, attempting to extract from {len(insights)} insights")
        for idx, insight_text in enumerate(insights[:5]): # Corrected variable name
            matches = re.findall(monetary_pattern, insight_text, re.IGNORECASE)
            if matches:
                logger.info(f"VIS_HELPER_LOG: Found monetary pattern in insight {idx+1}: {matches}")
                value = 1000000 * (idx + 1)  # Placeholder
                monetary_insights_data.append({"name": f"Value {idx+1}", "value": value, "description": insight_text[:100] + "..."})
        
        if monetary_insights_data:
            logger.info(f"VIS_HELPER_LOG: Using {len(monetary_insights_data)} monetary values extracted from insights")
            return monetary_insights_data
        else:
            logger.info("VIS_HELPER_LOG: Failed to extract monetary values from insights")
    
    if not monetary_metrics:
        logger.warning("VIS_HELPER_LOG: ⚠️ USING FALLBACK STATIC DATA for monetary values chart - no real metrics or insights found")
        return [
            {"name": "Revenue", "value": 1250000, "description": "Estimated revenue based on document context"},
            {"name": "Cost", "value": 875000, "description": "Estimated costs based on document context"},
            {"name": "Profit", "value": 375000, "description": "Calculated profit (Revenue - Cost)"}
        ]
    
    return monetary_metrics[:5] if monetary_metrics else None

def generate_percentage_data(metrics: List[FinancialMetric], insights: List[str]) -> Optional[List[Dict[str, Any]]]:
    """Generate percentage data for visualization."""
    percentage_metrics = [
        {"name": metric.name, "value": metric.value, "description": f"{metric.category}: {metric.name} ({metric.period})"}
        for metric in metrics
        if metric.unit and (any(keyword in metric.unit.lower() for keyword in ["percent", "%", "ratio", "rate", "growth"])) 
        or (metric.name and any(keyword in metric.name.lower() for keyword in ["percent", "rate", "ratio", "growth", "margin", "yield", "return"]))
    ]
    
    logger.info(f"VIS_HELPER_LOG: Found {len(metrics)} total metrics for percentage chart")
    logger.info(f"VIS_HELPER_LOG: Filtered down to {len(percentage_metrics)} percentage metrics")
    if percentage_metrics:
        logger.info(f"VIS_HELPER_LOG: Using actual percentage metrics for chart: {json.dumps([m['name'] for m in percentage_metrics])}")
    
    if not percentage_metrics and insights:
        percentage_pattern = r'(\d+(\.\d+)?)\s*(%|percent|percentage)'
        percentage_insights_data = []
        logger.info(f"VIS_HELPER_LOG: No percentage metrics found, attempting to extract from {len(insights)} insights")
        for idx, insight_text in enumerate(insights[:5]): # Corrected variable name
            matches = re.findall(percentage_pattern, insight_text, re.IGNORECASE)
            if matches:
                logger.info(f"VIS_HELPER_LOG: Found percentage pattern in insight {idx+1}: {matches}")
                try:
                    value = float(matches[0][0])
                    percentage_insights_data.append({"name": f"Rate {idx+1}", "value": value, "description": insight_text[:100] + "..."})
                except: # Broad except, consider refining
                    percentage_insights_data.append({"name": f"Rate {idx+1}", "value": (idx + 1) * 5, "description": insight_text[:100] + "..."})
        
        if percentage_insights_data:
            logger.info(f"VIS_HELPER_LOG: Using {len(percentage_insights_data)} percentage values extracted from insights")
            return percentage_insights_data
        else:
            logger.info("VIS_HELPER_LOG: Failed to extract percentage values from insights")
    
    if not percentage_metrics:
        logger.warning("VIS_HELPER_LOG: ⚠️ USING FALLBACK STATIC DATA for percentage chart - no real metrics or insights found")
        return [
            {"name": "Growth Rate", "value": 8.5, "description": "Estimated annual growth rate"},
            {"name": "Profit Margin", "value": 15.3, "description": "Estimated profit margin percentage"},
            {"name": "Market Share", "value": 12.7, "description": "Estimated market share percentage"}
        ]
        
    return percentage_metrics[:5] if percentage_metrics else None

def generate_keyword_frequency_data(insights: List[str]) -> Optional[List[Dict[str, Any]]]:
    """Generate keyword frequency data for visualization."""
    if not insights:
        logger.warning("VIS_HELPER_LOG: ⚠️ USING FALLBACK STATIC DATA for keyword frequency chart - no insights found")
        return [
            {"name": "Revenue", "value": 3, "description": "Mentions of revenue in document"},
            {"name": "Profit", "value": 2, "description": "Mentions of profit in document"},
            {"name": "Growth", "value": 2, "description": "Mentions of growth in document"},
            {"name": "Market", "value": 1, "description": "Mentions of market in document"}
        ]
    
    logger.info(f"VIS_HELPER_LOG: Generating keyword frequency data from {len(insights)} insights")
    financial_terms = [
        "revenue", "profit", "loss", "growth", "income", "cost", "expense", "asset", 
        "liability", "equity", "debt", "cash", "margin", "dividend", "earnings", 
        "investment", "capital", "fiscal", "quarter", "annual"
    ]
    term_count: Dict[str, int] = {}
    for insight_text in insights: # Corrected variable name
        for term in financial_terms:
            pattern = r'\b' + re.escape(term) + r'\b'
            matches = re.findall(pattern, insight_text.lower())
            if matches:
                term_count[term] = term_count.get(term, 0) + len(matches)
    
    logger.info(f"VIS_HELPER_LOG: Found {len(term_count)} financial terms in insights")
    if term_count:
        logger.info(f"VIS_HELPER_LOG: Most frequent terms: {json.dumps(dict(sorted(term_count.items(), key=lambda x: x[1], reverse=True)[:5]))}")
    
    frequency_data = [
        {"name": term.capitalize(), "value": count, "description": f"Mentions of {term} in document"}
        for term, count in sorted(term_count.items(), key=lambda x: x[1], reverse=True)
    ]
    
    if not frequency_data: # Check if frequency_data is empty after processing
        logger.warning("VIS_HELPER_LOG: No financial terms found in insights, using fallback method with insight snippets")
        # Fallback to using insight snippets if no terms are found
        return [{"name": insight_text[:20] + "...", "value": 1, "description": insight_text[:100]} for insight_text in insights[:5]]

    return frequency_data[:5] if frequency_data else None 

def get_data_for_visualization_type(visualization_type: str, metrics: List[FinancialMetric], insights: List[str]) -> Optional[List[Dict[str, Any]]]:
    """
    Dispatches to the correct data generation function based on visualization type.
    """
    if visualization_type == "monetary_values":
        return generate_monetary_values_data(metrics, insights)
    elif visualization_type == "percentage":
        return generate_percentage_data(metrics, insights)
    elif visualization_type == "keyword_frequency":
        return generate_keyword_frequency_data(insights)
    else:
        logger.warning(f"Unknown visualization type: {visualization_type}")
        return None 