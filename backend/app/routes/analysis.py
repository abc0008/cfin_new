from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from typing import Dict, List, Optional, Any
import uuid
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
import json
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from models.analysis import AnalysisRequest, AnalysisResult
from models.analysis import AnalysisApiResponse, VisualizationDataResponse
from models.analysis import FinancialMetric, FinancialRatio, ComparativePeriod
from models.visualization import VisualizationData, ChartData, TableData
from models.document import ProcessedDocument
from models.database_models import ProcessingStatusEnum
from repositories.document_repository import DocumentRepository
from repositories.analysis_repository import AnalysisRepository
from services.analysis_service import AnalysisService
from pdf_processing.document_service import DocumentService
from pdf_processing.claude_service import ClaudeService
from pdf_processing.langchain_service import LangChainService
from utils.database import get_db
from utils.response import handle_exception, create_error_response, get_error_type_from_status, add_cors_headers

# Configure more verbose logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# Dependencies
async def get_document_repository(db: AsyncSession = Depends(get_db)):
    return DocumentRepository(db)

async def get_document_service(db: AsyncSession = Depends(get_db)):
    document_repository = DocumentRepository(db)
    return DocumentService(document_repository)

async def get_analysis_repository(db: AsyncSession = Depends(get_db)):
    return AnalysisRepository(db)

async def get_analysis_service(
    db: AsyncSession = Depends(get_db),
    analysis_repository: AnalysisRepository = Depends(get_analysis_repository),
    document_repository: DocumentRepository = Depends(get_document_repository)
):
    return AnalysisService(analysis_repository, document_repository)

async def get_claude_service():
    return ClaudeService()

async def get_langchain_service():
    return LangChainService()

# --- Pydantic models for API response ---
# Definitions are now in models/analysis.py and imported above

@router.post("/run", response_model=AnalysisApiResponse)
async def run_analysis_endpoint(
    analysis_request: AnalysisRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Run an analysis on document(s). This endpoint now routes to the
    appropriate analysis logic, primarily the tool-based comprehensive analysis.
    """
    try:
        # Log the incoming request details correctly
        logger.info(
            f"API Request - Run Analysis: Type='{analysis_request.analysis_type}', "
            f"Docs='{analysis_request.document_ids}', "
            f"Query='{analysis_request.query}', "
            f"Params='{analysis_request.parameters}'"
        )

        # Instantiate the AnalysisService
        # analysis_service = get_analysis_service() # This will be injected by Depends

        # Prepare parameters for the service call
        parameters = analysis_request.parameters.copy()
        custom_knowledge_base = analysis_request.custom_knowledge_base
        query = analysis_request.query

        analysis_id, analysis_result_dict = await analysis_service.run_analysis(
            document_ids=[str(doc_id) for doc_id in analysis_request.document_ids],
            analysis_type=analysis_request.analysis_type,
            parameters=parameters,
            custom_knowledge_base=custom_knowledge_base,
            query=query
        )

        # Log the dictionary received from the service
        logger.info(f"--- analysis_result_dict from AnalysisService for analysis {analysis_id} ---")
        logger.info(json.dumps(analysis_result_dict, indent=2, default=str)) # Use default=str for any non-serializable items
        logger.info(f"--- End analysis_result_dict from AnalysisService ---")

        # Ensure visualization_data is properly structured for VisualizationDataResponse
        viz_data_input = analysis_result_dict.get("visualization_data") or {}
        
        # Ensure charts and tables are lists even if missing from viz_data_input
        charts_list = viz_data_input.get("charts", [])
        tables_list = viz_data_input.get("tables", [])

        viz_response_data = VisualizationDataResponse(
            charts=[ChartData(**c) if isinstance(c, dict) else c for c in charts_list],
            tables=[TableData(**t) if isinstance(t, dict) else t for t in tables_list],
            monetary_values=viz_data_input.get("monetary_values"), # Use snake_case key here
            percentages=viz_data_input.get("percentages"),
            keyword_frequency=viz_data_input.get("keyword_frequency") # Use snake_case key here
        )

        api_response = AnalysisApiResponse(
            id=analysis_id,  # Use the unpacked analysis_id
            document_ids=analysis_result_dict.get("document_ids", []),
            analysis_type=analysis_result_dict.get("analysis_type", analysis_request.analysis_type),
            timestamp=analysis_result_dict.get("timestamp", datetime.now().isoformat()),
            analysis_text=analysis_result_dict.get("analysis_text"),
            visualization_data=viz_response_data,
            metrics=analysis_result_dict.get("metrics", []),
            ratios=analysis_result_dict.get("ratios", []),
            comparative_periods=analysis_result_dict.get("comparative_periods", []),
            insights=analysis_result_dict.get("insights", []),
            citation_references=analysis_result_dict.get("citation_references", {}),
            document_type=analysis_result_dict.get("document_type"), 
            periods=analysis_result_dict.get("periods", []),
            query=analysis_result_dict.get("query")
        )

        logger.info(f"API Response - Analysis successful: ID='{api_response.id}'")
        # Log counts for verification
        logger.info(f"Charts: {len(api_response.visualization_data.charts)}, Tables: {len(api_response.visualization_data.tables)}")
        logger.info(f"Metrics: {len(api_response.metrics)}, Ratios: {len(api_response.ratios)}, Comparisons: {len(api_response.comparative_periods)}")

        # Temporarily log the exact response being sent to the frontend
        response_to_send = api_response.model_dump(by_alias=True)
        logger.info(f"--- JSON Response to Frontend ---")
        logger.info(json.dumps(response_to_send, indent=2))
        logger.info(f"--- End JSON Response to Frontend ---")

        return response_to_send

    except ValueError as ve:
        logger.warning(f"Value error during analysis run: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Unhandled error during analysis run: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run analysis: {str(e)}")

@router.post("/run-with-tools", response_model=AnalysisApiResponse, deprecated=True)
async def run_analysis_with_tools(
    analysis_request: AnalysisRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    DEPRECATED: Use the primary /run endpoint instead, which now supports tool-based analysis.
    This endpoint is maintained for backwards compatibility but routes to the same implementation.
    """
    return await run_analysis_endpoint(analysis_request, analysis_service)

# Get endpoint for retrieving results
@router.get("/{analysis_id}", response_model=AnalysisApiResponse)
async def get_analysis_result(
    analysis_id: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Retrieve analysis results along with linked citation references.
    """
    try:
        # Assuming analysis_service.get_analysis returns an AnalysisResult model instance
        # or a dict that largely conforms to AnalysisResult structure (snake_case keys)
        analysis_result_obj: AnalysisResult = await analysis_service.get_analysis(analysis_id)

        if not analysis_result_obj:
            raise ValueError(f"Analysis {analysis_id} not found") # Or handle as per service contract

        viz_data_dict = analysis_result_obj.visualization_data or {}
        charts_list = viz_data_dict.get("charts", [])
        tables_list = viz_data_dict.get("tables", [])

        viz_response_data = VisualizationDataResponse(
            charts=[ChartData(**c) if isinstance(c, dict) else c for c in charts_list],
            tables=[TableData(**t) if isinstance(t, dict) else t for t in tables_list],
            monetary_values=viz_data_dict.get("monetary_values"),
            percentages=viz_data_dict.get("percentages"),
            keyword_frequency=viz_data_dict.get("keyword_frequency")
        )

        api_response = AnalysisApiResponse(
            id=analysis_result_obj.id,
            document_ids=analysis_result_obj.document_ids,
            analysis_type=analysis_result_obj.analysis_type,
            timestamp=analysis_result_obj.timestamp.isoformat() if isinstance(analysis_result_obj.timestamp, datetime) else datetime.now().isoformat(),
            analysis_text=analysis_result_obj.analysis_text,
            visualization_data=viz_response_data,
            metrics=analysis_result_obj.metrics,
            ratios=analysis_result_obj.ratios,
            comparative_periods=analysis_result_obj.comparative_periods,
            insights=analysis_result_obj.insights,
            citation_references=analysis_result_obj.citation_references,
            document_type=analysis_result_obj.document_type,
            periods=analysis_result_obj.periods,
            query=analysis_result_obj.query
        )
        return api_response.model_dump(by_alias=True) # Use model_dump for Pydantic V2

    except ValueError as ve:
        logger.warning(f"Analysis not found: {ve}")
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.exception(f"Error retrieving analysis {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analysis: {str(e)}")

@router.get("/document/{document_id}", response_model=List[Dict[str, Any]])
async def list_document_analyses(
    document_id: str,
    analysis_type: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    List analyses for a document.
    """
    try:
        # Get the analyses from the database
        analyses = await analysis_service.list_document_analyses(
            document_id=document_id,
            analysis_type=analysis_type,
            limit=limit,
            offset=offset
        )
        
        return analyses
    except Exception as e:
        # Ensure JSONResponse is imported in case we need it
        from fastapi.responses import JSONResponse
        
        logger.error(f"Error listing analyses: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing analyses: {str(e)}")

@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    analysis_repository: AnalysisRepository = Depends(get_analysis_repository)
):
    """
    Delete an analysis.
    """
    try:
        # Check if analysis exists
        analysis = await analysis_repository.get_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
        
        # Delete the analysis
        success = await analysis_repository.delete_analysis(analysis_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete analysis")
        
        return {"message": f"Analysis {analysis_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        # Ensure JSONResponse is imported in case we need it
        from fastapi.responses import JSONResponse
        
        logger.error(f"Error deleting analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting analysis: {str(e)}")

# Helper functions to generate mock data for demonstration/testing
def generate_mock_metrics(period: str) -> List[FinancialMetric]:
    """Generate mock financial metrics for demo purposes."""
    return [
        FinancialMetric(
            category="Revenue",
            name="Total Revenue",
            period=period,
            value=24.5,
            unit="million USD"
        ),
        FinancialMetric(
            category="Revenue",
            name="YoY Growth",
            period=period,
            value=12.0,
            unit="percent"
        ),
        FinancialMetric(
            category="Expenses",
            name="Operating Expenses",
            period=period,
            value=18.3,
            unit="million USD"
        ),
        FinancialMetric(
            category="Profitability",
            name="Net Income",
            period=period,
            value=4.2,
            unit="million USD"
        ),
        FinancialMetric(
            category="Liquidity",
            name="Cash Position",
            period=period,
            value=15.6,
            unit="million USD"
        )
    ]

def generate_mock_ratios() -> List[FinancialRatio]:
    """Generate mock financial ratios for demo purposes."""
    return [
        FinancialRatio(
            name="Current Ratio",
            value=1.8,
            description="Measures the company's ability to pay short-term obligations",
            benchmark=2.1,
            trend=-0.1
        ),
        FinancialRatio(
            name="Quick Ratio",
            value=1.2,
            description="Measures the company's ability to pay short-term obligations using liquid assets",
            benchmark=1.5,
            trend=-0.05
        ),
        FinancialRatio(
            name="Debt-to-Equity",
            value=0.85,
            description="Measures the company's financial leverage",
            benchmark=0.7,
            trend=0.03
        ),
        FinancialRatio(
            name="Profit Margin",
            value=12.4,
            description="Measures the company's profitability as a percentage of revenue",
            benchmark=10.2,
            trend=0.5
        ),
        FinancialRatio(
            name="Return on Assets",
            value=8.2,
            description="Measures how efficiently the company is using its assets to generate profit",
            benchmark=7.5,
            trend=0.3
        )
    ]

@router.get("/{analysis_id}/enhanced", response_model=Dict[str, Any])
async def get_enhanced_analysis(
    analysis_id: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Retrieve enhanced analysis with trends and extra insights
    """
    try:
        # Get the base analysis
        analysis = await analysis_service.get_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
        
        # Generate enhanced data based on the basic analysis
        trends = []
        insights = []
        
        # Extract metrics for trend generation
        metrics = analysis.get("result_data", {}).get("metrics", [])
        chart_data = analysis.get("result_data", {}).get("chart_data", {})
        base_insights = analysis.get("result_data", {}).get("insights", [])
        
        # Generate trends if we have metrics
        if metrics:
            for metric in metrics:
                # Create trend data for each metric
                trend = {
                    "id": f"trend-{uuid.uuid4()}",
                    "name": f"{metric.get('name', 'Unknown')} Trend",
                    "description": f"Trend analysis for {metric.get('name', 'Unknown')}",
                    "value": metric.get("value", 0.0),
                    "change": 0.05,  # Mock value: 5% change
                    "direction": "increasing" if 0.05 > 0 else "decreasing",
                    "significance": "high" if metric.get("name", "").lower() in ["revenue", "net income"] else "medium",
                    "category": metric.get("category", "Unknown")
                }
                trends.append(trend)
        
        # Generate enhanced insights
        if base_insights:
            for i, insight_text in enumerate(base_insights):
                # Categorize insights
                category = "critical" if i == 0 else "important" if i == 1 else "informational"
                
                # Link to metrics where possible
                related_metrics = []
                for metric in metrics[:2]:  # Just link to first two metrics for demo
                    related_metrics.append(metric.get("name", "Unknown"))
                
                insight = {
                    "id": f"insight-{uuid.uuid4()}",
                    "text": insight_text,
                    "category": category,
                    "relatedMetrics": related_metrics,
                    "confidence": 0.9 - (i * 0.05)  # Decreasing confidence for later insights
                }
                insights.append(insight)
        
        # Return the enhanced analysis
        return {
            "trends": trends,
            "insights": insights
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Ensure JSONResponse is imported in case we need it
        from fastapi.responses import JSONResponse
        
        logger.error(f"Error getting enhanced analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving enhanced analysis: {str(e)}")

@router.get("/{analysis_id}/chart/{chart_type}", response_model=Dict[str, Any])
async def get_chart_data(
    analysis_id: str,
    chart_type: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Retrieve chart data for a specific analysis and chart type
    """
    try:
        # Get the base analysis
        analysis = await analysis_service.get_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
        
        # Extract chart data from the analysis
        chart_data = analysis.get("result_data", {}).get("chart_data", {})
        
        # If time series data is available, return it with the requested chart type
        if "timeSeriesData" in chart_data:
            return {
                "chartData": chart_data["timeSeriesData"],
                "chartType": chart_type,
                "title": f"Financial {chart_type.capitalize()} Chart",
                "description": f"Generated from analysis {analysis_id}"
            }
        
        # If no chart data available, return empty result
        return {
            "chartData": [],
            "chartType": chart_type,
            "title": f"No data available",
            "description": "No chart data found for this analysis"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Ensure JSONResponse is imported in case we need it
        from fastapi.responses import JSONResponse
        
        logger.error(f"Error getting chart data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving chart data: {str(e)}")

@router.get("/types")
async def get_analysis_types():
    """
    List all supported analysis types with display names and descriptions.
    """
    return AnalysisService.get_supported_analysis_types()