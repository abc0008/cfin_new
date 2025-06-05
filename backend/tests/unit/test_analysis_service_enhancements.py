import pytest
from unittest.mock import AsyncMock, MagicMock

from services.analysis_service import AnalysisService
from models.document import ProcessedDocument, DocumentMetadata, DocumentContentType, ProcessingStatus
from models.visualization import ChartData, TableData, VisualizationData
from cfin.backend.pdf_processing.api_service import ClaudeService


@pytest.fixture
def sample_document():
    """Create a sample document for testing"""
    return ProcessedDocument(
        id="doc123",
        file_hash="abc123",
        metadata=DocumentMetadata(
            filename="financial_report_2023.pdf",
            filetype="application/pdf",
            size=12345,
            document_type=DocumentContentType.BALANCE_SHEET,
            upload_time="2023-11-01T12:00:00Z",
            page_count=10
        ),
        processing_status=ProcessingStatus.COMPLETED,
        extracted_text="Sample financial report text with revenue of $1,500,000.",
        extracted_data={
            "metrics": [
                {"name": "Revenue", "value": 1500000, "unit": "USD"}
            ],
            "visualization_data": {
                "charts": [
                    {
                        "chartType": "bar",
                        "config": {
                            "title": "Revenue by Year",
                            "description": "Annual revenue trends",
                            "xAxisKey": "year"
                        },
                        "data": [
                            {"year": "2021", "value": 1000000},
                            {"year": "2022", "value": 1200000},
                            {"year": "2023", "value": 1500000}
                        ],
                        "chartConfig": {
                            "value": {
                                "label": "Revenue",
                                "color": "#0066CC"
                            }
                        }
                    }
                ],
                "tables": [
                    {
                        "tableType": "simple",
                        "config": {
                            "title": "Financial Metrics",
                            "description": "Key financial metrics",
                            "columns": [
                                {"key": "metric", "label": "Metric"},
                                {"key": "value", "label": "Value", "format": "currency"}
                            ]
                        },
                        "data": [
                            {"metric": "Total Revenue", "value": 1500000},
                            {"metric": "Net Income", "value": 350000}
                        ]
                    }
                ]
            },
            "visualizationData": {
                "monetaryValues": [
                    {"title": "Revenue", "value": 1500000, "change": 0.25},
                    {"title": "Net Income", "value": 350000, "change": 0.15}
                ],
                "keywordFrequency": [
                    {"keyword": "revenue", "frequency": 15},
                    {"keyword": "profit", "frequency": 10}
                ]
            }
        }
    )


@pytest.fixture
def mock_claude_service():
    """Create a mock Claude service"""
    service = AsyncMock(spec=ClaudeService)
    
    # Mock the tool-based extraction method
    service.extract_financial_data_with_tools.return_value = {
        "metrics": [{"name": "Revenue", "value": 1500000}],
        "visualization_data": {
            "charts": [
                {
                    "chartType": "bar",
                    "config": {"title": "Revenue", "description": "Revenue by year"},
                    "data": [{"year": "2023", "value": 1500000}],
                    "chartConfig": {"value": {"label": "Revenue"}}
                }
            ],
            "tables": []
        }
    }
    
    # Return the mocked service
    return service


class TestAnalysisServiceEnhancements:
    """Test suite for enhanced AnalysisService functionality"""
    
    def setup_method(self):
        """Set up for each test"""
        self.analysis_repository = MagicMock()
        self.document_repository = MagicMock()
        self.claude_service = MagicMock()
        
        # Create the service with the correct constructor parameters
        self.service = AnalysisService(
            analysis_repository=self.analysis_repository,
            document_repository=self.document_repository
        )
        
        # Replace the claude_service property after initialization
        self.service.claude_service = self.claude_service
    
    @pytest.mark.asyncio
    async def test_get_visualization_data(self, sample_document):
        """Test retrieving visualization data from a document"""
        # Setup
        self.document_repository.get_document.return_value = sample_document
        
        # Execute
        result = await self.service.get_visualization_data("doc123")
        
        # Verify
        assert result is not None
        assert "charts" in result
        assert "tables" in result
        assert len(result["charts"]) == 1
        assert len(result["tables"]) == 1
        assert result["charts"][0]["chartType"] == "bar"
        
    @pytest.mark.asyncio
    async def test_get_visualization_data_missing(self):
        """Test handling missing visualization data"""
        # Setup - document without visualization data
        doc_without_viz = ProcessedDocument(
            id="doc456",
            file_hash="def456",
            metadata=DocumentMetadata(
                filename="simple_doc.pdf",
                filetype="application/pdf",
                size=5000,
                document_type=DocumentContentType.BALANCE_SHEET,
                upload_time="2023-11-02T12:00:00Z",
                page_count=5
            ),
            processing_status=ProcessingStatus.COMPLETED,
            extracted_text="Simple document without visualization data",
            extracted_data={"metrics": []}
        )
        self.document_repository.get_document.return_value = doc_without_viz
        
        # Execute
        result = await self.service.get_visualization_data("doc456")
        
        # Verify - should get an empty visualization data structure
        assert result is not None
        assert "charts" in result
        assert "tables" in result
        assert len(result["charts"]) == 0
        assert len(result["tables"]) == 0
        
    @pytest.mark.asyncio
    async def test_get_document_not_found(self):
        """Test handling document not found"""
        # Setup
        self.document_repository.get_document.return_value = None
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Document not found"):
            await self.service.get_visualization_data("nonexistent")
    
    @pytest.mark.asyncio
    async def test_run_analysis_with_tools(self, sample_document, mock_claude_service):
        """Test running analysis with tool-based approach"""
        # Setup
        self.document_repository.get_document.return_value = sample_document
        self.service.claude_service = mock_claude_service
        
        # Mock PDF content
        pdf_content = b"%PDF-1.5\nSample PDF content"
        self.document_repository.get_pdf_content.return_value = pdf_content
        
        # Execute - Update to match the actual implementation
        result = await self.service.run_analysis(
            document_ids=["doc123"],
            analysis_type="financial",
            parameters={"use_tools": True}
        )
        
        # Verify - Adjust for the actual return value format (a tuple)
        analysis_id, result_data = result
        assert result_data is not None
        assert "result_data" in result_data
        assert "visualization_data" in result_data["result_data"]
        assert "charts" in result_data["result_data"]["visualization_data"]
        assert mock_claude_service.extract_financial_data_with_tools.called
        assert mock_claude_service.extract_financial_data_with_tools.call_args[1]["document_type"] == DocumentContentType.BALANCE_SHEET
    
    @pytest.mark.asyncio
    async def test_run_analysis_without_tools(self, sample_document):
        """Test running analysis with classic approach (without tools)"""
        # Setup
        self.document_repository.get_document.return_value = sample_document
        
        # Mock the comprehensive analysis method
        classic_analysis_result = {
            "metrics": [{"name": "Revenue", "value": 1500000}],
            "visualizationData": {
                "monetaryValues": [
                    {"title": "Revenue", "value": 1500000, "change": 0.25}
                ]
            }
        }
        
        self.service._run_comprehensive_analysis = AsyncMock(return_value=classic_analysis_result)
        
        # Execute - Update to match the actual implementation
        result = await self.service.run_analysis(
            document_ids=["doc123"],
            analysis_type="financial",
            parameters={"use_tools": False}
        )
        
        # Verify - Adjust for the actual return value format (a tuple)
        analysis_id, result_data = result
        assert result_data is not None
        assert "result_data" in result_data
        assert self.service._run_comprehensive_analysis.called
    
    @pytest.mark.asyncio
    async def test_transform_visualization_data(self):
        """Test transformation between visualization data formats"""
        # Setup
        tool_style_data = VisualizationData(
            charts=[
                ChartData(
                    chartType="bar",
                    config={
                        "title": "Revenue by Year",
                        "description": "Annual revenue trends",
                        "xAxisKey": "year"
                    },
                    data=[
                        {"year": "2021", "value": 1000000},
                        {"year": "2022", "value": 1200000}
                    ],
                    chartConfig={
                        "value": {
                            "label": "Revenue",
                            "color": "#0066CC"
                        }
                    }
                )
            ],
            tables=[
                TableData(
                    tableType="simple",
                    config={
                        "title": "Financial Metrics",
                        "description": "Key metrics",
                        "columns": [
                            {"key": "metric", "label": "Metric"},
                            {"key": "value", "label": "Value", "format": "currency"}
                        ]
                    },
                    data=[
                        {"metric": "Revenue", "value": 1200000}
                    ]
                )
            ]
        )
        
        # Execute
        legacy_data = self.service._transform_to_legacy_format(tool_style_data)
        
        # Verify
        assert legacy_data is not None
        assert "monetaryValues" in legacy_data
        assert "keywordFrequency" in legacy_data
        assert legacy_data["monetaryValues"][0]["title"] == "Revenue"
        assert legacy_data["monetaryValues"][0]["value"] == 1200000
        
    @pytest.mark.asyncio
    async def test_format_analysis_response(self, sample_document):
        """Test response formatting from different data sources"""
        # Setup
        tool_data = {
            "visualization_data": {
                "charts": [
                    {
                        "chartType": "bar",
                        "config": {"title": "Revenue", "description": ""},
                        "data": [{"year": "2023", "value": 1500000}],
                        "chartConfig": {"value": {"label": "Revenue"}}
                    }
                ],
                "tables": []
            }
        }
        
        # Execute
        result = await self.service._format_analysis_response(
            document=sample_document, 
            analysis_data=tool_data,
            analysis_type="financial"
        )
        
        # Verify
        assert result is not None
        assert "visualization_data" in result
        assert "visualizationData" in result
        assert result["visualization_data"]["charts"][0]["chartType"] == "bar"

    @pytest.mark.asyncio
    async def test_run_analysis_comprehensive_no_tools(self, mock_claude_service, mock_document_repo):
        # Mock ClaudeService methods
        mock_claude_service.get_document_content.return_value = {"text": "Sample document text", "raw_text": "Sample raw text for comprehensive"}
        # Mock _extract_financial_data_with_citations for non-tool comprehensive
        mock_claude_service._extract_financial_data_with_citations = AsyncMock(return_value=(
            {"raw_text": "Extracted financial data without tools", "some_metric": 123},
            [{"page": 1, "text": "citation1"}]
        ))
        
        analysis_service = AnalysisService(mock_claude_service, mock_document_repo)
        
        # Execute
        result = await analysis_service.run_analysis(
            document_id="doc_comp",
            analysis_type="comprehensive", # This type should trigger non-tool comprehensive analysis
            user_query="Summarize this document.",
            report_template_path=None 
        )
        
        # Verify
        mock_claude_service.get_document_content.assert_called_once_with("doc_comp")
        mock_claude_service._extract_financial_data_with_citations.assert_called_once()
        # Check arguments of _extract_financial_data_with_citations if necessary
        
        assert result is not None
        assert result.analysis_type == "comprehensive"
        assert "Extracted financial data without tools" in result.results_summary
        assert result.visualization_data is None # No visualizations for this path
        assert result.metrics is None # No separate metrics for this path currently
        assert result.comparative_periods is None # No comparative periods for this path
        assert result.status == ProcessingStatus.COMPLETED
        assert len(result.citations) == 1

    @pytest.mark.asyncio
    async def test_run_analysis_comprehensive_tools(self, mock_claude_service, mock_document_repo):
        # Mock ClaudeService methods
        mock_claude_service.get_document_content.return_value = {"text": "Sample document text", "raw_text": "Sample raw text"}
        mock_claude_service.analyze_with_visualization_tools = AsyncMock(return_value={
            "analysis_text": "Tool-based analysis complete.",
            "visualizations": {
                "charts": [{"type": "bar", "data": "chart_data"}],
                "tables": [{"type": "simple", "data": "table_data"}]
            },
            "metrics": [{"name": "ROI", "value": "15%"}],
            "comparative_periods": [{"metric": "Revenue", "change": "5%"}]
        })
        
        analysis_service = AnalysisService(mock_claude_service, mock_document_repo)
        
        # Execute
        result = await analysis_service.run_analysis(
            document_id="doc1",
            analysis_type="comprehensive_tools", # This type should trigger tool-based analysis
            user_query="Analyze financial health.",
            report_template_path=None 
        )
        
        # Verify
        mock_claude_service.get_document_content.assert_called_once_with("doc1")
        mock_claude_service.analyze_with_visualization_tools.assert_called_once_with(
            document_text="Sample raw text", # Ensure it uses raw_text
            user_query="Analyze financial health.",
            knowledge_base="" # Assuming knowledge base is empty for this test
        )
        
        assert result is not None
        assert result.analysis_type == "comprehensive_tools"
        assert "Tool-based analysis complete." in result.results_summary
        assert len(result.visualization_data["charts"]) == 1
        assert len(result.visualization_data["tables"]) == 1
        assert len(result.metrics) == 1
        assert len(result.comparative_periods) == 1
        assert result.status == ProcessingStatus.COMPLETED 