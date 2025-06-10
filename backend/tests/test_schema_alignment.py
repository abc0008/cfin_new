#!/usr/bin/env python3
"""
Test script to verify Pydantic/Zod schema alignment
Tests that API responses have proper camelCase fields
"""

import asyncio
import json
from typing import Dict, Any
from datetime import datetime
import uuid

# Import all models to test
from models.document import (
    DocumentMetadata, ProcessedDocument, DocumentUploadResponse,
    Citation, DocumentContentType, ProcessingStatus
)
from models.message import (
    Message, MessageResponse, MessageRequest,
    ConversationState, ConversationHistoryResponse,
    MessageRole
)
from models.analysis import (
    FinancialMetric, FinancialRatio, ComparativePeriod,
    AnalysisResult, VisualizationDataResponse, AnalysisApiResponse
)
from models.visualization import ChartData, TableData, ChartConfig, TableConfig


def check_camel_case(data: Dict[str, Any], model_name: str) -> bool:
    """Check if dictionary keys are in camelCase"""
    issues = []
    for key in data.keys():
        if '_' in key:
            issues.append(f"  - {key} (should be {to_camel_case(key)})")
    
    if issues:
        print(f"\n❌ {model_name} has snake_case fields:")
        for issue in issues:
            print(issue)
        return False
    else:
        print(f"✅ {model_name} - all fields in camelCase")
        return True


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase"""
    parts = snake_str.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])


def test_document_models():
    """Test document-related models"""
    print("\n=== Testing Document Models ===")
    
    # Test DocumentMetadata
    metadata = DocumentMetadata(
        filename="test.pdf",
        file_size=1000,
        mime_type="application/pdf",
        user_id="test-user"
    )
    check_camel_case(metadata.model_dump(by_alias=True), "DocumentMetadata")
    
    # Test Citation
    citation = Citation(
        page=1,
        text="Test citation",
        bounding_box={"x": 0, "y": 0, "width": 100, "height": 50}
    )
    check_camel_case(citation.model_dump(by_alias=True), "Citation")
    
    # Test ProcessedDocument
    doc = ProcessedDocument(
        metadata=metadata,
        content_type=DocumentContentType.INCOME_STATEMENT,
        periods=["Q1 2024"],
        extracted_data={"revenue": 1000000},
        confidence_score=0.95,
        processing_status=ProcessingStatus.COMPLETED
    )
    check_camel_case(doc.model_dump(by_alias=True), "ProcessedDocument")
    
    # Test DocumentUploadResponse
    upload_resp = DocumentUploadResponse(
        document_id=uuid.uuid4(),
        filename="test.pdf",
        status=ProcessingStatus.PROCESSING,
        message="Processing",
        content_type="application/pdf",
        file_size=1000
    )
    check_camel_case(upload_resp.model_dump(by_alias=True), "DocumentUploadResponse")


def test_message_models():
    """Test message-related models"""
    print("\n=== Testing Message Models ===")
    
    # Test Message
    msg = Message(
        session_id="test-session",
        role=MessageRole.USER,
        content="Test message",
        referenced_documents=["doc1", "doc2"]
    )
    check_camel_case(msg.model_dump(by_alias=True), "Message")
    
    # Test MessageRequest
    msg_req = MessageRequest(
        session_id="test-session",
        content="Test request",
        user_id="test-user",
        referenced_documents=["doc1"]
    )
    check_camel_case(msg_req.model_dump(by_alias=True), "MessageRequest")
    
    # Test MessageResponse
    msg_resp = MessageResponse(
        id="test-id",
        session_id="test-session",
        timestamp=datetime.now(),
        role=MessageRole.ASSISTANT,
        content="Test response",
        referenced_documents=["doc1"],
        referenced_analyses=["analysis1"]
    )
    check_camel_case(msg_resp.model_dump(by_alias=True), "MessageResponse")
    
    # Test ConversationState
    conv_state = ConversationState(
        session_id="test-session",
        active_documents=["doc1"],
        active_analyses=["analysis1"],
        user_preferences={"theme": "dark"}
    )
    check_camel_case(conv_state.model_dump(by_alias=True), "ConversationState")


def test_analysis_models():
    """Test analysis-related models"""
    print("\n=== Testing Analysis Models ===")
    
    # Test FinancialMetric
    metric = FinancialMetric(
        category="Revenue",
        name="Net Sales",
        period="Q1 2024",
        value=1000000,
        unit="USD",
        is_estimated=False
    )
    check_camel_case(metric.model_dump(by_alias=True), "FinancialMetric")
    
    # Test FinancialRatio
    ratio = FinancialRatio(
        name="Current Ratio",
        value=1.5,
        description="Current assets to current liabilities"
    )
    check_camel_case(ratio.model_dump(by_alias=True), "FinancialRatio")
    
    # Test ComparativePeriod
    comp = ComparativePeriod(
        metric="Revenue",
        current_period="Q1 2024",
        previous_period="Q1 2023",
        current_value=1000000,
        previous_value=900000,
        change=100000,
        percent_change=11.1
    )
    check_camel_case(comp.model_dump(by_alias=True), "ComparativePeriod")
    
    # Test VisualizationDataResponse
    viz = VisualizationDataResponse(
        charts=[],
        tables=[],
        monetary_values=[{"name": "Revenue", "value": 1000000}],
        percentages=[{"name": "Growth", "value": 10.5}]
    )
    check_camel_case(viz.model_dump(by_alias=True), "VisualizationDataResponse")


def test_visualization_models():
    """Test visualization models"""
    print("\n=== Testing Visualization Models ===")
    
    # Test ChartConfig
    chart_config = ChartConfig(
        title="Revenue Chart",
        x_axis_label="Quarter",
        y_axis_label="Revenue",
        x_axis_key="quarter"
    )
    check_camel_case(chart_config.model_dump(by_alias=True), "ChartConfig")
    
    # Test ChartData
    chart = ChartData(
        chart_type="bar",
        config=chart_config,
        data=[{"x": "Q1", "y": 1000000}]
    )
    check_camel_case(chart.model_dump(by_alias=True), "ChartData")
    
    # Test TableConfig
    table_config = TableConfig(
        title="Financial Summary",
        columns=[{
            "key": "metric",
            "label": "Metric",
            "format": "text"
        }]
    )
    check_camel_case(table_config.model_dump(by_alias=True), "TableConfig")
    
    # Test TableData
    table = TableData(
        table_type="summary",
        config=table_config,
        data=[{"metric": "Revenue", "value": 1000000}]
    )
    check_camel_case(table.model_dump(by_alias=True), "TableData")


def main():
    """Run all tests"""
    print("Testing Pydantic Model Schema Alignment")
    print("=" * 50)
    
    test_document_models()
    test_message_models()
    test_analysis_models()
    test_visualization_models()
    
    print("\n" + "=" * 50)
    print("Schema alignment test complete!")


if __name__ == "__main__":
    main()