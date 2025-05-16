'''
Unit tests for the AnalysisService routing logic.
'''
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from services.analysis_service import AnalysisService
from services.analysis_strategies.comprehensive_strategy import ComprehensiveAnalysisStrategy
from services.analysis_strategies.financial_template_strategy import FinancialTemplateStrategy
# Assuming a base strategy for type hinting if necessary, though not strictly needed for this mock
from services.analysis_strategies.base_strategy import AnalysisStrategy 

from pdf_processing.claude_service import ClaudeService
from repositories.analysis_repository import AnalysisRepository
from repositories.document_repository import DocumentRepository
from models.database_models import Document, AnalysisResult, User

@pytest.mark.asyncio
async def test_run_analysis_routes_to_comprehensive_strategy():
    '''
    Test that AnalysisService.run_analysis correctly routes to ComprehensiveAnalysisStrategy
    when analysis_type is "comprehensive_tools", instantiates it, and calls its execute method.
    '''
    # 1. Mock dependencies for AnalysisService initialization
    mock_claude_service = MagicMock(spec=ClaudeService)
    mock_analysis_repo = MagicMock(spec=AnalysisRepository)
    mock_document_repo = MagicMock(spec=DocumentRepository)

    # 2. Mock the ComprehensiveAnalysisStrategy and its execute method
    # We want to check if it's instantiated and its execute method is called.
    mock_comprehensive_strategy_instance = AsyncMock(spec=ComprehensiveAnalysisStrategy)
    mock_comprehensive_strategy_instance.execute.return_value = {
        "analysis_text": "mocked comprehensive analysis",
        "visualizations": {"charts": [], "tables": []},
        "metrics": []
    }
    
    # Mock the class itself to control its instantiation
    MockComprehensiveStrategyClass = MagicMock(return_value=mock_comprehensive_strategy_instance)

    # 3. Patch the strategy_map in the context of where AnalysisService uses it.
    # AnalysisService imports strategy_map from services.analysis_strategies
    # The path to patch should be where it's looked up.
    with patch('services.analysis_service.strategy_map', new={
        "comprehensive_tools": MockComprehensiveStrategyClass,
        # Add other strategies if testing them, e.g.:
        # "financial_template": MockFinancialTemplateStrategyClass 
    }) as mock_map:

        # 4. Instantiate AnalysisService with mocked dependencies
        analysis_service = AnalysisService(
            claude_service=mock_claude_service,
            analysis_repository=mock_analysis_repo,
            document_repository=mock_document_repo
        )

        # 5. Prepare dummy inputs for run_analysis
        dummy_user = User(id="user1", email="test@example.com") # Minimal User
        dummy_document_ids = ["doc1"]
        dummy_analysis_type = "comprehensive_tools"
        dummy_user_query = "Analyze this."
        dummy_analysis_name = "Test Comprehensive Analysis"
        dummy_parameters = {}

        # Mock document_repository.get_documents_by_ids_for_user to return some docs
        mock_document_repo.get_documents_by_ids_for_user.return_value = [
            Document(id="doc1", user_id="user1", filename="test.pdf", s3_bucket="b", s3_key="k", upload_timestamp=None, content_text="doc content")
        ]
        # Mock analysis_repository.create_analysis_result for the initial creation
        mock_analysis_repo.create_analysis_result.return_value = AnalysisResult(id="analysis1", user_id="user1", document_ids=["doc1"], analysis_type=dummy_analysis_type, status="PENDING")

        # 6. Call run_analysis
        result = await analysis_service.run_analysis(
            user=dummy_user,
            document_ids=dummy_document_ids,
            analysis_type=dummy_analysis_type,
            user_query=dummy_user_query,
            analysis_name=dummy_analysis_name,
            parameters=dummy_parameters
        )

        # 7. Assertions
        # Assert that the ComprehensiveAnalysisStrategy class was instantiated with ClaudeService
        MockComprehensiveStrategyClass.assert_called_once_with(mock_claude_service)

        # Assert that the execute method of the instance was called (and awaited)
        mock_comprehensive_strategy_instance.execute.assert_awaited_once()
        
        # Check the arguments passed to execute (optional, but good for thoroughness)
        execute_args = mock_comprehensive_strategy_instance.execute.call_args
        assert execute_args is not None, "Execute was not called with arguments"
        # Example: check one of the arguments, like user_query
        # Note: .args for positional, .kwargs for keyword arguments
        assert execute_args.kwargs.get('user_query') == dummy_user_query
        assert execute_args.kwargs.get('aggregated_text') is not None # Check it got some text
        assert len(execute_args.kwargs.get('documents')) == 1 # Check it got documents

        # Assert that the result from execute was returned (and potentially processed)
        assert result is not None
        # Depending on whether run_analysis modifies the strategy's result, 
        # you might assert specific parts of 'result' match what the mock execute returned.
        # For this test, the main focus is on instantiation and call, so we'll assume 
        # the result processing is minimal or tested elsewhere if complex.
        assert result.analysis_text == "mocked comprehensive analysis"
        
        # Assert that analysis_repository.update_analysis_result was called to save the final result
        mock_analysis_repo.update_analysis_result.assert_called_once()

@pytest.mark.asyncio
async def test_run_analysis_routes_to_financial_template_strategy():
    '''
    Test that AnalysisService.run_analysis correctly routes to FinancialTemplateStrategy
    when analysis_type is "financial_template".
    '''
    mock_claude_service = MagicMock(spec=ClaudeService)
    mock_analysis_repo = MagicMock(spec=AnalysisRepository)
    mock_document_repo = MagicMock(spec=DocumentRepository)

    mock_financial_strategy_instance = AsyncMock(spec=FinancialTemplateStrategy)
    mock_financial_strategy_instance.execute.return_value = {
        "analysis_text": "mocked financial template analysis",
        "visualizations": {"charts": [], "tables": []},
        "metrics": []
    }
    MockFinancialStrategyClass = MagicMock(return_value=mock_financial_strategy_instance)

    with patch('services.analysis_service.strategy_map', new={
        "financial_template": MockFinancialStrategyClass,
    }):
        analysis_service = AnalysisService(mock_claude_service, mock_analysis_repo, mock_document_repo)
        
        dummy_user = User(id="user1", email="test@example.com")
        dummy_document_ids = ["doc1"]
        dummy_analysis_type = "financial_template"
        dummy_user_query = "Analyze with template."
        dummy_analysis_name = "Test Template Analysis"

        mock_document_repo.get_documents_by_ids_for_user.return_value = [
            Document(id="doc1", user_id="user1", filename="test.pdf", s3_bucket="b", s3_key="k", upload_timestamp=None, content_text="doc content")
        ]
        mock_analysis_repo.create_analysis_result.return_value = AnalysisResult(id="analysis2", user_id="user1", document_ids=["doc1"], analysis_type=dummy_analysis_type, status="PENDING")

        await analysis_service.run_analysis(
            user=dummy_user,
            document_ids=dummy_document_ids,
            analysis_type=dummy_analysis_type,
            user_query=dummy_user_query,
            analysis_name=dummy_analysis_name,
        )

        MockFinancialStrategyClass.assert_called_once_with(mock_claude_service)
        mock_financial_strategy_instance.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_run_analysis_handles_unknown_strategy():
    '''
    Test that AnalysisService.run_analysis raises a ValueError or logs an error
    for an unknown analysis_type.
    '''
    mock_claude_service = MagicMock(spec=ClaudeService)
    mock_analysis_repo = MagicMock(spec=AnalysisRepository)
    mock_document_repo = MagicMock(spec=DocumentRepository)

    # Patch with an empty strategy_map or one not containing the test type
    with patch('services.analysis_service.strategy_map', new={}):
        analysis_service = AnalysisService(mock_claude_service, mock_analysis_repo, mock_document_repo)

        dummy_user = User(id="user1", email="test@example.com")
        dummy_document_ids = ["doc1"]
        dummy_analysis_type = "unknown_strategy_type"
        dummy_user_query = "Analyze this somehow."
        dummy_analysis_name = "Test Unknown Analysis"
        
        mock_document_repo.get_documents_by_ids_for_user.return_value = [
             Document(id="doc1", user_id="user1", filename="test.pdf", s3_bucket="b", s3_key="k", upload_timestamp=None, content_text="doc content")
        ]
        # Mock create_analysis_result for initial PENDING state creation
        initial_result_mock = AnalysisResult(id="analysis3", user_id="user1", document_ids=["doc1"], analysis_type=dummy_analysis_type, status="PENDING")
        mock_analysis_repo.create_analysis_result.return_value = initial_result_mock

        # Expecting a ValueError or for the status to be updated to FAILED with an error message
        # Current implementation in AnalysisService updates status to FAILED.
        # We will check that update_analysis_result is called appropriately.
        
        updated_result = await analysis_service.run_analysis(
            user=dummy_user,
            document_ids=dummy_document_ids,
            analysis_type=dummy_analysis_type,
            user_query=dummy_user_query,
            analysis_name=dummy_analysis_name
        )
        
        assert updated_result.status == "FAILED"
        assert "Unknown analysis type" in updated_result.error_message
        
        # Ensure create was called, and then update was called to mark as FAILED
        mock_analysis_repo.create_analysis_result.assert_called_once()
        mock_analysis_repo.update_analysis_result.assert_called_once()
        updated_args = mock_analysis_repo.update_analysis_result.call_args[0]
        assert updated_args[0] == initial_result_mock.id # analysis_result_id
        assert updated_args[1]["status"] == "FAILED"
        assert "Unknown analysis type" in updated_args[1]["error_message"] 