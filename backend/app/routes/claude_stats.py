#!/usr/bin/env python3
"""
Claude API optimization statistics endpoint for Finance validation.
Provides model usage, cost reduction metrics, and cache performance data.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claude-stats", tags=["claude-optimization"])

@router.get("/model-usage")
async def get_model_usage_stats() -> Dict[str, Any]:
    """
    Get model usage statistics for cost validation.
    
    Returns:
        Dictionary with model usage ratios and cost reduction metrics
    """
    try:
        from pdf_processing.model_router import get_model_stats
        
        stats = get_model_stats()
        
        # Calculate cost reduction factor (assuming Haiku is 12x cheaper)
        haiku_cost_factor = 1.0  # Baseline
        sonnet_cost_factor = 12.0  # 12x more expensive
        
        if stats["total_calls"] > 0:
            # Cost reduction vs all-Sonnet baseline
            actual_cost = (stats["haiku_calls"] * haiku_cost_factor + 
                          stats["sonnet_calls"] * sonnet_cost_factor)
            baseline_cost = stats["total_calls"] * sonnet_cost_factor
            cost_reduction_percent = ((baseline_cost - actual_cost) / baseline_cost) * 100
        else:
            cost_reduction_percent = 0.0
        
        return {
            "model_usage": stats,
            "cost_analysis": {
                "haiku_cost_factor": haiku_cost_factor,
                "sonnet_cost_factor": sonnet_cost_factor,
                "cost_reduction_percent": round(cost_reduction_percent, 2),
                "estimated_savings_factor": round(baseline_cost / max(actual_cost, 1), 2) if stats["total_calls"] > 0 else 1.0
            },
            "status": "active" if stats["total_calls"] > 0 else "no_usage"
        }
        
    except Exception as e:
        logger.error(f"Error getting model usage stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve model stats: {str(e)}")

@router.get("/file-cache")
async def get_file_cache_stats() -> Dict[str, Any]:
    """
    Get file cache statistics showing duplicate upload prevention.
    
    Returns:
        Dictionary with cache performance metrics
    """
    try:
        from utils.file_cache import get_file_cache_stats
        
        cache_stats = await get_file_cache_stats()
        
        return {
            "cache_stats": cache_stats,
            "optimization_impact": {
                "description": "Each cached file prevents a duplicate upload, saving ~1-2 seconds UX time",
                "cache_hit_benefit": "Instant file ID retrieval vs API upload time"
            },
            "status": "active" if cache_stats["cached_files"] > 0 else "empty"
        }
        
    except Exception as e:
        logger.error(f"Error getting file cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cache stats: {str(e)}")

@router.get("/optimization-summary")
async def get_optimization_summary() -> Dict[str, Any]:
    """
    Get comprehensive Claude API optimization summary.
    
    Returns:
        Combined metrics for all optimization features
    """
    try:
        from pdf_processing.model_router import get_model_stats
        from utils.file_cache import get_file_cache_stats
        
        model_stats = get_model_stats()
        cache_stats = await get_file_cache_stats()
        
        return {
            "optimization_features": {
                "files_api": {
                    "status": "active",
                    "benefit": "50-90% token reduction on follow-up requests",
                    "cached_files": cache_stats["cached_files"]
                },
                "token_efficient_tools": {
                    "status": "active",
                    "benefit": "~14% token reduction on tool calls",
                    "header_enabled": True
                },
                "model_routing": {
                    "status": "active",
                    "benefit": "12x cost reduction for light analysis",
                    "haiku_ratio": model_stats.get("haiku_ratio", 0.0),
                    "total_calls": model_stats.get("total_calls", 0)
                },
                "rate_limiting": {
                    "status": "active", 
                    "benefit": "Prevents 429 errors with token bucket",
                    "throttling_enabled": True
                }
            },
            "performance_metrics": {
                "model_usage": model_stats,
                "file_cache": cache_stats,
                "estimated_token_savings": "50-90% on subsequent requests",
                "estimated_cost_reduction": f"{model_stats.get('cost_reduction_factor', 1.0):.1f}x vs all-Sonnet baseline"
            },
            "deployment_status": "production_ready",
            "last_updated": "2025-01-26"
        }
        
    except Exception as e:
        logger.error(f"Error getting optimization summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve optimization summary: {str(e)}") 