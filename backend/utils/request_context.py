#!/usr/bin/env python3
"""
Request context utilities for tracking token usage and model routing decisions.
Provides cost accountability for Finance dashboards.
"""

import logging
import contextvars
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class RequestMetrics:
    """Tracks metrics for a single request."""
    request_id: str
    tokens_estimated: int = 0
    tokens_actual: Optional[int] = None
    model_chosen: Optional[str] = None
    routing_reason: str = ""
    tools_requested: set = field(default_factory=set)
    cache_hit: bool = False
    file_id_used: Optional[str] = None
    processing_time_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "request_id": self.request_id,
            "tokens_estimated": self.tokens_estimated,
            "tokens_actual": self.tokens_actual,
            "model_chosen": self.model_chosen,
            "routing_reason": self.routing_reason,
            "tools_requested": list(self.tools_requested),
            "cache_hit": self.cache_hit,
            "file_id_used": self.file_id_used,
            "processing_time_ms": self.processing_time_ms
        }

# Context variable for request-scoped metrics
_request_metrics: contextvars.ContextVar[Optional[RequestMetrics]] = contextvars.ContextVar(
    'request_metrics', 
    default=None
)

def init_request_metrics(request_id: str) -> RequestMetrics:
    """Initialize request metrics for cost tracking."""
    metrics = RequestMetrics(request_id=request_id)
    _request_metrics.set(metrics)
    logger.debug("Initialized request metrics for %s", request_id)
    return metrics

def get_request_metrics() -> Optional[RequestMetrics]:
    """Get current request metrics."""
    return _request_metrics.get()

def update_token_estimate(tokens: int, text_slice_length: Optional[int] = None) -> None:
    """Update token estimate after text slicing for accurate model routing."""
    metrics = get_request_metrics()
    if metrics:
        metrics.tokens_estimated = tokens
        if text_slice_length:
            logger.debug("Token estimate updated: %d tokens (text slice: %d chars)", 
                        tokens, text_slice_length)
        else:
            logger.debug("Token estimate updated: %d tokens", tokens)

def set_model_choice(model: str, reason: str, tools: set = None) -> None:
    """Record model routing decision for cost analysis."""
    metrics = get_request_metrics()
    if metrics:
        metrics.model_chosen = model
        metrics.routing_reason = reason
        if tools:
            metrics.tools_requested = tools
        logger.info("Model routing: %s (reason: %s, tools: %s)", 
                   model, reason, list(tools) if tools else [])

def set_cache_hit(file_id: str) -> None:
    """Record cache hit for efficiency tracking."""
    metrics = get_request_metrics()
    if metrics:
        metrics.cache_hit = True
        metrics.file_id_used = file_id
        logger.debug("Cache hit recorded: file_id=%s", file_id)

def set_actual_tokens(tokens: int) -> None:
    """Record actual tokens consumed from API response."""
    metrics = get_request_metrics()
    if metrics:
        metrics.tokens_actual = tokens
        logger.debug("Actual tokens recorded: %d", tokens)

def set_processing_time(milliseconds: int) -> None:
    """Record request processing time."""
    metrics = get_request_metrics()
    if metrics:
        metrics.processing_time_ms = milliseconds
        logger.debug("Processing time recorded: %d ms", milliseconds)

def get_cost_summary() -> Dict[str, Any]:
    """Get cost summary for current request."""
    metrics = get_request_metrics()
    if not metrics:
        return {"error": "No request metrics available"}
    
    # Calculate token efficiency
    token_efficiency = None
    if metrics.tokens_actual and metrics.tokens_estimated:
        token_efficiency = metrics.tokens_actual / metrics.tokens_estimated
    
    # Estimate cost reduction based on model choice
    cost_factor = 1.0
    if metrics.model_chosen == "claude-3-haiku-20250315":
        cost_factor = 0.083  # Haiku is ~12x cheaper than Sonnet
    
    return {
        **metrics.to_dict(),
        "token_efficiency": token_efficiency,
        "cost_factor": cost_factor,
        "estimated_savings": (1.0 - cost_factor) * 100 if cost_factor < 1.0 else 0.0
    } 