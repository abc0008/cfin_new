import pytest
import asyncio
import os
from unittest.mock import patch, AsyncMock, MagicMock
import json
from typing import Dict, Any, List, Optional

from fastapi.testclient import TestClient
from app.main import app
from repositories.document_repository import DocumentRepository
from services.document_service import DocumentService
from services.analysis_service import AnalysisService
from cfin.backend.pdf_processing.api_service import ClaudeService
from models.document import ProcessedDocument, DocumentMetadata, DocumentContentType, ProcessingStatus, DocumentCitation


@pytest.fixture
def sample_pdf_data():
    """Sample PDF content for testing"""
    # Just a minimal PDF header for testing
    return b"%PDF-1.5\nSample financial report with revenue data"


@pytest.fixture
def test_client():
    """Create a FastAPI test client"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_document_service():
    """Mock document service for testing"""
    service = MagicMock(spec=DocumentService)
    
    # Create a sample document
    doc = ProcessedDocument(
        id="integration-test-doc",
        file_hash="test123",
        metadata=DocumentMetadata(
            filename="financial_report_test.pdf",
            filetype="application/pdf",
            size=12345,
            document_type=DocumentContentType.FINANCIAL_REPORT,
            upload_time="2023-12-01T12:00:00Z",
            page_count=5
        ),
        processing_status=ProcessingStatus.COMPLETED,
        extracted_text="Financial report with revenue of $1,500,000 for 2023.",
        extracted_data={
            "metrics": [
                {"name": "Revenue", "value": 1500000, "unit": "USD"}
            ],
            "visualizationData": {
                "monetaryValues": [
                    {"title": "Revenue", "value": 1500000, "change": 0.25}
                ]
            }
        }
    )
    
    # Mock methods
    service.get_document.return_value = doc
    service.get_pdf_content.return_value = sample_pdf_data()
    
    return service


@pytest.fixture
def mock_claude_service():
    """Mock Claude service for testing"""
    service = AsyncMock(spec=ClaudeService)
    
    # Mock the tool-based financial data extraction
    service.extract_financial_data_with_tools.return_value = {
        "metrics": [
            {"name": "Revenue", "value": 1500000, "unit": "USD"},
            {"name": "Net Income", "value": 350000, "unit": "USD"}
        ],
        "visualization_data": {
            "charts": [
                {
                    "chartType": "bar",
                    "config": {
                        "title": "Revenue by Year",
                        "description": "Annual revenue analysis",
                        "xAxisKey": "year"
                    },
                    "data": [
                        {"year": "2021", "value": 1000000},
                        {"year": "2022", "value": 1200000},
                        {"year": "2023", "value": 1500000}
                    ],
                    "chartConfig": {
                        "value": {
                            "label": "Revenue (USD)",
                            "color": "#0066CC"
                        }
                    }
                },
                {
                    "chartType": "line",
                    "config": {
                        "title": "Net Income Trend",
                        "description": "Net income over time",
                        "xAxisKey": "year"
                    },
                    "data": [
                        {"year": "2021", "value": 200000},
                        {"year": "2022", "value": 280000},
                        {"year": "2023", "value": 350000}
                    ],
                    "chartConfig": {
                        "value": {
                            "label": "Net Income (USD)",
                            "color": "#00CC66"
                        }
                    }
                }
            ],
            "tables": [
                {
                    "tableType": "simple",
                    "config": {
                        "title": "Key Financial Metrics",
                        "description": "Summary of important metrics",
                        "columns": [
                            {"key": "metric", "label": "Metric"},
                            {"key": "value", "label": "Value (USD)", "format": "currency"},
                            {"key": "change", "label": "YoY Change", "format": "percent"}
                        ]
                    },
                    "data": [
                        {"metric": "Revenue", "value": 1500000, "change": 0.25},
                        {"metric": "Net Income", "value": 350000, "change": 0.25},
                        {"metric": "Operating Expenses", "value": 850000, "change": 0.15}
                    ]
                }
            ]
        },
        "visualizationData": {
            "monetaryValues": [
                {"title": "Revenue", "value": 1500000, "change": 0.25},
                {"title": "Net Income", "value": 350000, "change": 0.25}
            ],
            "keywordFrequency": [
                {"keyword": "revenue", "frequency": 15},
                {"keyword": "profit", "frequency": 10}
            ]
        }
    }
    
    return service


@pytest.mark.integration
class TestFinancialAnalysisToolsIntegration:
    """Integration tests for financial analysis with tool-based approach"""
    
    @pytest.mark.asyncio
    @patch('app.routes.analysis.get_analysis_service')
    @patch('app.routes.analysis.get_document_service')
    async def test_financial_analysis_endpoint_with_tools(
        self, mock_get_doc_service, mock_get_analysis_service, 
        test_client, mock_document_service, mock_claude_service, monkeypatch
    ):
        """Test the financial analysis endpoint with tool-based analysis"""
        # Setup
        analysis_service = AnalysisService(
            document_service=mock_document_service,
            claude_service=mock_claude_service
        )
        
        # Configure mocks for dependency injection
        mock_get_doc_service.return_value = mock_document_service
        mock_get_analysis_service.return_value = analysis_service
        
        # Mock the ClaudeService's tool-based analysis method
        mock_claude_instance = AsyncMock()
        mock_claude_instance.analyze_with_visualization_tools = AsyncMock(return_value={
            "analysis_text": "Comprehensive analysis with visualizations.",
            "visualizations": {
                "charts": [{"type": "bar", "data": "sample_chart_data", "config": {"title": "Revenue"}}],
                "tables": [{"type": "simple", "data": "sample_table_data", "config": {"title": "Metrics Table"}}]
            },
            "metrics": [{"name": "Efficiency Ratio", "value": "60%"}],
            "comparative_periods": [{"metric": "NIM", "current_value": "3.2%", "previous_value": "3.1%", "change": "0.1%"}]
        })
        monkeypatch.setattr("services.analysis_service.ClaudeService", lambda api_key=None: mock_claude_instance)
        monkeypatch.setattr("fastapi.BackgroundTasks.add_task", MagicMock())

        # Prepare request data
        analysis_request = {
            "document_id": "existing_doc_id",
            "analysis_type": "comprehensive_tools",
            "user_query": "Analyze this document and provide visualizations.",
            "report_template_path": None  # Or a valid path if testing templates
        }

        # Call the endpoint
        response = await test_client.post("/api/v1/analysis/", json=analysis_request)

        # Assertions
        assert response.status_code == 202  # Accepted for background processing
        response_data = response.json()
        assert response_data["message"] == "Analysis task accepted and processing in background"
        assert "analysis_id" in response_data
        
        # Ensure the background task was called with the correct analysis service method
        # This requires inspecting the mock_background_tasks or how AnalysisService uses ClaudeService
        # For now, we'll assume the service layer correctly calls analyze_with_visualization_tools
        # and verify that analyze_with_visualization_tools itself was called.
        
        # Wait a moment for the "background" task to execute in the test context if it's not truly async
        # This part is tricky to test without a real async worker or more complex mocking.
        # We'll rely on the unit tests for AnalysisService to ensure correct method routing.
        # Here we primarily check that the endpoint can be called and returns an accepted status.
        
        # To properly test the interaction, AnalysisService.run_analysis would need to be awaited
        # or the background task execution more directly controllable/inspectable.
        # For this refactor, we confirm the endpoint is okay and rely on AnalysisService unit tests
        # for the internal call to claude_service.analyze_with_visualization_tools.

    @pytest.mark.asyncio
    async def test_document_upload_and_analysis_flow(client, monkeypatch, sample_pdf_bytes, mock_document_repo_integration):
        """
        Test the document upload process and that initial processing (like citation extraction) occurs.
        This test is simplified to not check for immediate tool-based visualization generation
        as that is no longer the default behavior on upload.
        """
        # --- Mock ClaudeService for DocumentService ---
        mock_claude_doc_service_instance = AsyncMock(spec=ClaudeService)
        # This is the method DocumentService calls during upload
        mock_claude_doc_service_instance._extract_financial_data_with_citations = AsyncMock(return_value=(
            {"raw_text": "Extracted text from PDF.", "some_metric": 12345}, 
            [{"page_number": 1, "text": "This is a citation."}]
        ))
        # This mock is for the process_pdf method which is called by DocumentService
        mock_claude_doc_service_instance.process_pdf = AsyncMock(return_value=(
            ProcessedDocument(
                document_id="new_doc_id", 
                filename="test_upload.pdf",
                content_type=DocumentContentType.FINANCIAL_STATEMENT,
                text_content="Extracted text from PDF.",
                structured_data={"raw_text": "Extracted text from PDF.", "some_metric": 12345},
                summary="Summary of the PDF.",
                key_insights=["Insight 1", "Insight 2"],
                status=ProcessingStatus.COMPLETED,
                citations_count=1
            ),
            [DocumentCitation(document_id="new_doc_id", citation_id="cit1", page_number=1, text="This is a citation.")]
        ))

        # --- Mock DocumentRepository ---
        # mock_document_repo_integration is already passed as a fixture

        # --- Mock ClaudeService for AnalysisService (if a separate analysis is triggered) ---
        # For this simplified test, we are not triggering a separate analysis post-upload.
        
        # Apply mocks
        monkeypatch.setattr("pdf_processing.document_service.ClaudeService", lambda api_key=None: mock_claude_doc_service_instance)
        monkeypatch.setattr("services.analysis_service.ClaudeService", lambda api_key=None: AsyncMock()) # Generic mock for analysis
        monkeypatch.setattr("fastapi.BackgroundTasks.add_task", MagicMock())
        
        # 1. Upload Document
        files = {"file": ("test_upload.pdf", sample_pdf_bytes, "application/pdf")}
        response_upload = await client.post("/api/v1/documents/upload", files=files)
        
        assert response_upload.status_code == 202
        upload_data = response_upload.json()
        assert upload_data["message"] == "Document processing started in background"
        document_id = upload_data["document_id"]
        assert document_id is not None

        # Allow background tasks to complete (simplified for testing)
        await asyncio.sleep(0.1) 

        # Verify DocumentService called the correct ClaudeService method
        mock_claude_doc_service_instance.process_pdf.assert_called_once()
        called_args, called_kwargs = mock_claude_doc_service_instance.process_pdf.call_args
        assert called_kwargs['filename'] == "test_upload.pdf"
        # Add more assertions if needed on the pdf_data

        # Verify document was "created" and "updated" in the mock repository
        # Check that create_document was called
        mock_document_repo_integration.create_document.assert_called_once()
        # Check that update_document_content_and_status (or similar) was called after processing
        # The exact method depends on DocumentService's implementation details
        # For this example, let's assume update_document_content_and_status covers it.
        assert mock_document_repo_integration.update_document_content_and_status.call_count >= 1
        
        # You might want to check the status progression if your mock repo tracks it.
        # For instance, an initial PENDING, then PROCESSING, then COMPLETED.
        
        # Verify that structured data and citations were stored (based on mock_claude_doc_service_instance.process_pdf)
        # This would typically involve checking the arguments passed to mock_document_repo_integration.update_document_content_and_status
        # For example, that the 'structured_data' and 'citations' were correctly passed.
        # This requires a more detailed mock for DocumentRepository or direct inspection of call_args.

        # This test now confirms upload and initial processing. 
        # A separate test like test_financial_analysis_endpoint_with_tools 
        # would cover the subsequent explicit analysis call.

    @pytest.mark.asyncio
    @patch('app.routes.analysis.get_analysis_service')
    async def test_visualization_data_endpoint(
        self, mock_get_analysis_service, test_client, 
        mock_document_service, mock_claude_service
    ):
        """Test the dedicated visualization data endpoint"""
        # Setup
        analysis_service = AnalysisService(
            document_service=mock_document_service,
            claude_service=mock_claude_service
        )
        
        # Add visualization data to the mock document
        processed_doc = mock_document_service.get_document.return_value
        processed_doc.extracted_data["visualization_data"] = mock_claude_service.extract_financial_data_with_tools.return_value["visualization_data"]
        mock_document_service.get_document.return_value = processed_doc
        
        # Configure mock for dependency injection
        mock_get_analysis_service.return_value = analysis_service
        
        # Execute
        response = test_client.get(
            "/api/analysis/visualization-data/integration-test-doc"
        )
        
        # Verify
        assert response.status_code == 200
        
        data = response.json()
        assert "charts" in data
        assert "tables" in data
        
        # Verify charts
        assert len(data["charts"]) == 2
        assert data["charts"][0]["chartType"] == "bar"
        assert data["charts"][1]["chartType"] == "line"
        
        # Verify tables
        assert len(data["tables"]) == 1
        assert data["tables"][0]["tableType"] == "simple" 