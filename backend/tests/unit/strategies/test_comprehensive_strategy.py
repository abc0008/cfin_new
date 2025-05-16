'''
Unit tests for the ComprehensiveAnalysisStrategy.
'''
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from services.analysis_strategies.comprehensive_strategy import ComprehensiveAnalysisStrategy
from pdf_processing.claude_service import ClaudeService
from models.visualization import ChartData
from models.analysis import FinancialMetric
from models.database_models import Document # Assuming Document model is needed for strategy input
from anthropic.types import Message as AnthropicMessage, TextBlock, ToolUseBlock

# Helper to create a mock AnthropicMessage
def create_mock_anthropic_message(content_blocks: list, stop_reason: str = "stop_sequence") -> AnthropicMessage:
    return AnthropicMessage(
        id="test_msg_id",
        content=content_blocks,
        model="claude-3-opus-20240229", # Example model
        role="assistant",
        stop_reason=stop_reason,
        type="message",
        usage={"input_tokens": 10, "output_tokens": 20} # Example usage
    )

@pytest.mark.asyncio
async def test_comprehensive_strategy_returns_chart_and_text():
    '''
    Test that ComprehensiveAnalysisStrategy.execute returns at least one chart
    and some analysis text when Claude simulates generating a chart.
    '''
    # 1. Mock ClaudeService and its execute_tool_interaction_turn method
    mock_claude_service = AsyncMock(spec=ClaudeService)

    # Simulate a two-turn conversation:
    # Turn 1: Claude provides some text and requests a graph tool.
    # Turn 2: Claude provides more text after tool execution.

    # Response for Turn 1 (text + tool use)
    turn1_text_content = "This is the initial financial analysis."
    turn1_tool_use_block = ToolUseBlock(
        id="tool_use_123",
        name="generate_graph_data",
        input={"chartType": "bar", "config": {"title": "Test Chart"}, "data": [{"x":1, "y":2}], "chartConfig": {}}
    )
    mock_response_turn1 = create_mock_anthropic_message(
        content_blocks=[TextBlock(text=turn1_text_content, type='text'), turn1_tool_use_block],
        stop_reason="tool_use"
    )

    # Response for Turn 2 (final text after tool result is hypothetically processed and fed back)
    turn2_text_content = "Further analysis after chart generation."
    mock_response_turn2 = create_mock_anthropic_message(
        content_blocks=[TextBlock(text=turn2_text_content, type='text')],
        stop_reason="stop_sequence"
    )

    mock_claude_service.execute_tool_interaction_turn.side_effect = [
        mock_response_turn1,
        mock_response_turn2
    ]

    # 2. Mock tool_processing.process_visualization_input
    # This function is called by the strategy to process tool inputs.
    # We need it to return a valid ChartData object when generate_graph_data is called.
    mock_processed_chart_data = {
        "chartType": "bar",
        "config": {"title": "Mocked Processed Test Chart", "description": "Desc"},
        "data": [{"x": 1, "y": 2}],
        "chartConfig": {}
    }

    # Patch the tool_processing module where the strategy will import it from
    with patch('services.analysis_strategies.comprehensive_strategy.tool_processing') as mock_tool_processing_module:
        mock_tool_processing_module.process_visualization_input.return_value = mock_processed_chart_data

        # 3. Instantiate the strategy with the mocked ClaudeService
        strategy = ComprehensiveAnalysisStrategy(mock_claude_service)

        # 4. Prepare dummy inputs for the strategy's execute method
        dummy_aggregated_text = "Some financial document text."
        dummy_documents = [Document(id="doc1", user_id="user1", filename="test.pdf", s3_bucket="bucket", s3_key="key", upload_timestamp=None, content_text="text")] # Minimal Document
        dummy_parameters = {}
        dummy_user_query = "Analyze this document comprehensively."

        # 5. Call the execute method
        result = await strategy.execute(
            aggregated_text=dummy_aggregated_text,
            documents=dummy_documents,
            parameters=dummy_parameters,
            user_query=dummy_user_query
        )

        # 6. Assertions
        assert result is not None, "Strategy returned None"
        
        # Check for analysis text
        assert "analysis_text" in result, "Result missing 'analysis_text'"
        assert isinstance(result["analysis_text"], str), "analysis_text is not a string"
        assert turn1_text_content in result["analysis_text"], "Initial text not in analysis_text"
        assert turn2_text_content in result["analysis_text"], "Follow-up text not in analysis_text"
        assert len(result["analysis_text"].strip()) > 0, "analysis_text is empty"

        # Check for visualizations and charts
        assert "visualizations" in result, "Result missing 'visualizations'"
        assert isinstance(result["visualizations"], dict), "visualizations is not a dict"
        assert "charts" in result["visualizations"], "visualizations missing 'charts'"
        assert isinstance(result["visualizations"]["charts"], list), "charts is not a list"
        assert len(result["visualizations"]["charts"]) >= 1, "No charts returned"
        
        # Check the content of the first chart
        returned_chart = result["visualizations"]["charts"][0]
        assert isinstance(returned_chart, ChartData) or isinstance(returned_chart, dict), "Returned chart is not ChartData or dict"
        
        # If it's a dict (because Pydantic models might be dicts at this point if not fully instantiated to model by strategy)
        if isinstance(returned_chart, dict):
            assert returned_chart["config"]["title"] == "Mocked Processed Test Chart", "Chart title mismatch"
        elif isinstance(returned_chart, ChartData):
            assert returned_chart.config.title == "Mocked Processed Test Chart", "Chart title mismatch"

        # Verify execute_tool_interaction_turn was called twice
        assert mock_claude_service.execute_tool_interaction_turn.call_count == 2
        
        # Verify tool_processing.process_visualization_input was called for the graph tool
        mock_tool_processing_module.process_visualization_input.assert_called_once_with(
            "generate_graph_data", # tool_name
            turn1_tool_use_block.input, # tool_input
            turn1_tool_use_block.id # tool_use_id
        )

        # Check for metrics and tables (should be empty in this specific test if not simulated)
        assert "metrics" in result and isinstance(result["metrics"], list), "Metrics key missing or not a list"
        assert len(result["metrics"]) == 0, "Metrics list should be empty for this test case"
        assert "tables" in result["visualizations"] and isinstance(result["visualizations"]["tables"], list), "Tables key missing or not a list"
        assert len(result["visualizations"]["tables"]) == 0, "Tables list should be empty for this test case" 