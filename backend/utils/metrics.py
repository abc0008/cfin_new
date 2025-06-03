#!/usr/bin/env python3
"""
Prometheus metrics for Claude API optimization monitoring.
Tracks upload performance, model routing decisions, and cost efficiency.
"""

import logging
import time
from contextlib import contextmanager
from typing import Dict, Any

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Histogram, Gauge, Info
    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning("prometheus_client not available. Metrics will be logged only.")
    PROMETHEUS_AVAILABLE = False

# Prometheus metrics (if available)
if PROMETHEUS_AVAILABLE:
    # File upload performance
    claude_files_upload_seconds = Histogram(
        'claude_files_upload_seconds',
        'Time spent uploading files to Claude Files API',
        ['filename_size_bucket']  # small/medium/large based on file size
    )
    
    # Model routing decisions
    claude_tool_calls_total = Counter(
        'claude_tool_calls_total',
        'Total Claude API tool calls by model',
        ['model', 'routing_reason']
    )
    
    # Cache performance
    claude_cache_operations_total = Counter(
        'claude_cache_operations_total',
        'Claude file cache operations',
        ['operation', 'result']  # operation: get/set, result: hit/miss/expired
    )
    
    # Token efficiency
    claude_token_efficiency = Histogram(
        'claude_token_efficiency_ratio',
        'Ratio of actual tokens to estimated tokens',
        ['model']
    )
    
    # Cost optimization
    claude_cost_reduction_percent = Gauge(
        'claude_cost_reduction_percent',
        'Percentage cost reduction vs all-Sonnet baseline'
    )
    
    # Haiku usage ratio (target: >50% for cost optimization)
    claude_haiku_usage_ratio = Gauge(
        'claude_haiku_usage_ratio',
        'Percentage of requests routed to Haiku model'
    )

else:
    # Mock metrics for when Prometheus is not available
    class MockMetric:
        def labels(self, **kwargs):
            return self
        def inc(self, value=1):
            pass
        def observe(self, value):
            pass
        def set(self, value):
            pass
        def time(self):
            return contextmanager(lambda: iter([None]))()
    
    claude_files_upload_seconds = MockMetric()
    claude_tool_calls_total = MockMetric()
    claude_cache_operations_total = MockMetric()
    claude_token_efficiency = MockMetric()
    claude_cost_reduction_percent = MockMetric()
    claude_haiku_usage_ratio = MockMetric()

def get_file_size_bucket(file_size_bytes: int) -> str:
    """Categorize file size for metrics."""
    if file_size_bytes < 1024 * 1024:  # < 1MB
        return "small"
    elif file_size_bytes < 10 * 1024 * 1024:  # < 10MB
        return "medium"
    else:
        return "large"

@contextmanager
def track_file_upload(filename: str, file_size: int):
    """Track file upload performance."""
    size_bucket = get_file_size_bucket(file_size)
    start_time = time.time()
    
    try:
        yield
        # Success case
        duration = time.time() - start_time
        claude_files_upload_seconds.labels(filename_size_bucket=size_bucket).observe(duration)
        logger.debug("File upload metrics: %s (%s bucket) took %.2fs", 
                    filename, size_bucket, duration)
    except Exception as e:
        # Error case - still record the attempt time
        duration = time.time() - start_time
        claude_files_upload_seconds.labels(filename_size_bucket=f"{size_bucket}_error").observe(duration)
        logger.debug("File upload error metrics: %s (%s bucket) failed after %.2fs", 
                    filename, size_bucket, duration)
        raise

def record_model_choice(model: str, routing_reason: str) -> None:
    """Record model routing decision."""
    claude_tool_calls_total.labels(model=model, routing_reason=routing_reason).inc()
    logger.debug("Model choice recorded: %s (reason: %s)", model, routing_reason)

def record_cache_operation(operation: str, result: str) -> None:
    """Record cache operation (get/set with hit/miss/expired result)."""
    claude_cache_operations_total.labels(operation=operation, result=result).inc()
    logger.debug("Cache operation recorded: %s -> %s", operation, result)

def record_token_efficiency(model: str, estimated_tokens: int, actual_tokens: int) -> None:
    """Record token estimation accuracy."""
    if estimated_tokens > 0:
        efficiency_ratio = actual_tokens / estimated_tokens
        claude_token_efficiency.labels(model=model).observe(efficiency_ratio)
        logger.debug("Token efficiency recorded: %s model, %.2f ratio (%d actual / %d estimated)", 
                    model, efficiency_ratio, actual_tokens, estimated_tokens)

def update_cost_metrics(haiku_calls: int, sonnet_calls: int) -> None:
    """Update cost optimization metrics."""
    total_calls = haiku_calls + sonnet_calls
    
    if total_calls > 0:
        # Calculate Haiku usage ratio
        haiku_ratio = haiku_calls / total_calls
        claude_haiku_usage_ratio.set(haiku_ratio * 100)  # Percentage
        
        # Calculate cost reduction vs all-Sonnet baseline
        # Assuming Haiku is 12x cheaper than Sonnet
        actual_cost_units = haiku_calls * 1 + sonnet_calls * 12  # Relative cost
        baseline_cost_units = total_calls * 12  # All Sonnet cost
        cost_reduction = ((baseline_cost_units - actual_cost_units) / baseline_cost_units) * 100
        
        claude_cost_reduction_percent.set(cost_reduction)
        
        logger.debug("Cost metrics updated: %.1f%% Haiku usage, %.1f%% cost reduction", 
                    haiku_ratio * 100, cost_reduction)

def get_metrics_summary() -> Dict[str, Any]:
    """Get current metrics summary for debugging."""
    try:
        from pdf_processing.model_router import get_model_stats
        from utils.file_cache import get_file_cache_stats
        
        model_stats = get_model_stats()
        cache_stats = get_file_cache_stats()  # This is async, but we'll call it sync for summary
        
        return {
            "prometheus_available": PROMETHEUS_AVAILABLE,
            "model_routing": model_stats,
            "cache_performance": {
                "note": "Cache stats require async call",
                "prometheus_tracking": "Enabled" if PROMETHEUS_AVAILABLE else "Disabled"
            },
            "metrics_endpoints": [
                "claude_files_upload_seconds",
                "claude_tool_calls_total", 
                "claude_cache_operations_total",
                "claude_token_efficiency_ratio",
                "claude_cost_reduction_percent",
                "claude_haiku_usage_ratio"
            ]
        }
    except Exception as e:
        return {"error": str(e), "prometheus_available": PROMETHEUS_AVAILABLE} 