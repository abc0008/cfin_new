# backend/pdf_processing/model_router.py

import settings
import logging

log = logging.getLogger(__name__)

# Light tools that can be handled efficiently by Haiku
_LIGHT_TOOLS = {"generate_table_data", "generate_financial_metric"}

# Token threshold for using Haiku vs Sonnet
_HAIKU_LIMIT = 6_000

# Cost tracking for Finance validation (12x cost claim)
_model_call_counts = {"haiku": 0, "sonnet": 0}

def choose_model(requested_tools: set[str], token_estimate: int) -> str:
    """
    Choose between Haiku and Sonnet based on tool requirements and token count.
    Records routing decision in request context for cost tracking.
    
    Args:
        requested_tools: Set of tool names being requested
        token_estimate: Estimated token count for the request
        
    Returns:
        Model ID string (either MODEL_HAIKU or MODEL_SONNET)
    """
    # Use Haiku for light tools and small token counts
    if requested_tools.issubset(_LIGHT_TOOLS) and token_estimate < _HAIKU_LIMIT:
        chosen_model = settings.MODEL_HAIKU
        routing_reason = f"light_tools_under_{_HAIKU_LIMIT}_tokens"
        _model_call_counts["haiku"] += 1
        
        # Record routing decision for cost tracking
        try:
            from utils.request_context import set_model_choice
            set_model_choice(chosen_model, routing_reason, requested_tools)
        except ImportError:
            pass  # Request context not available
        
        log.info(f"Using Haiku for light tools {requested_tools} with {token_estimate} tokens " +
                f"(haiku_calls={_model_call_counts['haiku']}, sonnet_calls={_model_call_counts['sonnet']})")
        return chosen_model
    
    # Use Sonnet for heavy analysis or large token counts
    chosen_model = settings.MODEL_SONNET
    routing_reason = f"heavy_tools_or_over_{_HAIKU_LIMIT}_tokens"
    _model_call_counts["sonnet"] += 1
    
    # Record routing decision for cost tracking
    try:
        from utils.request_context import set_model_choice
        set_model_choice(chosen_model, routing_reason, requested_tools)
    except ImportError:
        pass  # Request context not available
    
    log.info(f"Using Sonnet for tools {requested_tools} with {token_estimate} tokens " +
            f"(haiku_calls={_model_call_counts['haiku']}, sonnet_calls={_model_call_counts['sonnet']})")
    return chosen_model

def get_model_stats() -> dict:
    """Get model usage statistics for Finance cost validation."""
    total_calls = sum(_model_call_counts.values())
    if total_calls == 0:
        return {"haiku_ratio": 0.0, "sonnet_ratio": 0.0, "total_calls": 0}
    
    return {
        "haiku_ratio": _model_call_counts["haiku"] / total_calls,
        "sonnet_ratio": _model_call_counts["sonnet"] / total_calls,
        "total_calls": total_calls,
        "haiku_calls": _model_call_counts["haiku"],
        "sonnet_calls": _model_call_counts["sonnet"],
        "cost_reduction_factor": (_model_call_counts["haiku"] * 12 + _model_call_counts["sonnet"]) / max(total_calls, 1)  # 12x cheaper for Haiku
    } 