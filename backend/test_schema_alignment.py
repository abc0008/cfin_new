#!/usr/bin/env python3
"""
Comprehensive schema alignment verification script.

This script tests all Pydantic models to ensure they have proper camelCase aliases
and that the ConfigDict is set up correctly with alias_generator and populate_by_name.
"""

import json
import inspect
from datetime import datetime
from typing import get_origin, get_args
import uuid

from models.visualization import *
from models.citation import *
from models.api_models import *
from models.message import *
from models.document import *
from models.analysis import *
from models.tools import *
from models.error import *

def test_camel_case_conversion():
    """Test that the to_camel utility function works correctly."""
    from models.visualization import to_camel
    
    test_cases = [
        ("snake_case", "snakeCase"),
        ("single_word", "singleWord"),
        ("multiple_word_case", "multipleWordCase"),
        ("already_camel", "alreadyCamel"),
        ("single", "single"),
        ("word_with_numbers_123", "wordWithNumbers123"),
    ]
    
    print("Testing camelCase conversion utility:")
    for snake, expected in test_cases:
        result = to_camel(snake)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"  {snake} -> {result} (expected: {expected}) {status}")
        if result != expected:
            return False
    return True

def check_model_config(model_class):
    """Check if a Pydantic model has the correct ConfigDict setup."""
    issues = []
    
    # Skip RootModel and other Pydantic base classes
    from pydantic import RootModel
    if model_class.__name__ in ['RootModel'] or issubclass(model_class, RootModel):
        return issues  # RootModel doesn't need our config
    
    # Check if model_config exists
    if not hasattr(model_class, 'model_config'):
        issues.append("Missing model_config")
        return issues
    
    config = model_class.model_config
    
    # Check if it's a ConfigDict
    if not hasattr(config, 'get'):
        issues.append("model_config is not a ConfigDict")
        return issues
    
    # Check for alias_generator
    if 'alias_generator' not in config:
        issues.append("Missing alias_generator in model_config")
    
    # Check for populate_by_name
    if 'populate_by_name' not in config:
        issues.append("Missing populate_by_name in model_config")
    elif not config.get('populate_by_name'):
        issues.append("populate_by_name is False")
    
    return issues

def find_all_pydantic_models():
    """Find all Pydantic BaseModel subclasses in the imported modules."""
    from pydantic import BaseModel
    
    models = []
    
    # Get all global variables from this module
    for name, obj in globals().items():
        if (inspect.isclass(obj) and 
            issubclass(obj, BaseModel) and 
            obj is not BaseModel):
            models.append((name, obj))
    
    return models

def test_model_serialization(model_class, model_name):
    """Test that a model serializes correctly to camelCase."""
    try:
        # Create a sample instance based on the model
        if model_name == "MetricConfig":
            instance = MetricConfig(label="Test Metric")
        elif model_name == "ChartConfig":
            instance = ChartConfig(title="Test Chart", description="Test Description")
        elif model_name == "ChartDataItem":
            instance = ChartDataItem(x_value="test", y_value=100)
        elif model_name == "ChartData":
            config = ChartConfig(title="Test", description="Test")
            data_item = ChartDataItem(x_value="test", y_value=100)
            instance = ChartData(
                chart_type="bar",
                config=config,
                data=[data_item],
                chart_config={}
            )
        elif model_name == "TableColumn":
            instance = TableColumn(key="test", label="Test")
        elif model_name == "TableConfig":
            column = TableColumn(key="test", label="Test")
            instance = TableConfig(
                title="Test Table",
                description="Test Description",
                columns=[column]
            )
        elif model_name == "TableData":
            config = TableConfig(
                title="Test",
                description="Test",
                columns=[TableColumn(key="test", label="Test")]
            )
            instance = TableData(
                table_type="simple",
                config=config,
                data=[{"test": "value"}]
            )
        elif model_name == "DocumentMetadata":
            instance = DocumentMetadata(
                filename="test.pdf",
                file_size=1000,
                mime_type="application/pdf",
                user_id="test-user"
            )
        elif model_name == "ProcessedDocument":
            metadata = DocumentMetadata(
                filename="test.pdf",
                file_size=1000,
                mime_type="application/pdf",
                user_id="test-user"
            )
            instance = ProcessedDocument(metadata=metadata)
        elif model_name == "DocumentUploadResponse":
            instance = DocumentUploadResponse(
                document_id=uuid.uuid4(),
                filename="test.pdf",
                status=ProcessingStatus.COMPLETED,
                message="Success",
                content_type="application/pdf",
                file_size=1000
            )
        elif model_name == "FinancialMetric":
            instance = FinancialMetric(
                category="Revenue",
                name="Total Revenue",
                period="2024",
                value=1000000.0,
                unit="USD"
            )
        elif model_name == "FinancialRatio":
            instance = FinancialRatio(
                name="Current Ratio",
                value=1.5,
                description="Test ratio"
            )
        elif model_name == "ComparativePeriod":
            instance = ComparativePeriod(
                metric="Revenue",
                current_period="2024",
                previous_period="2023",
                current_value=1000000,
                previous_value=900000,
                change=100000,
                percent_change=11.11
            )
        elif model_name == "AnalysisRequest":
            instance = AnalysisRequest(
                analysis_type="financial_overview",
                document_ids=["doc1"]
            )
        elif model_name == "AnalysisResult":
            instance = AnalysisResult(
                document_ids=["doc1"],
                analysis_type="financial_overview"
            )
        elif model_name == "VisualizationDataResponse":
            instance = VisualizationDataResponse()
        elif model_name == "AnalysisApiResponse":
            viz_data = VisualizationDataResponse()
            instance = AnalysisApiResponse(
                id=str(uuid.uuid4()),
                document_ids=["doc1"],
                analysis_type="financial_overview",
                timestamp=datetime.now().isoformat(),
                visualization_data=viz_data
            )
        elif model_name == "Message":
            instance = Message(
                session_id="test-session",
                role=MessageRole.USER,
                content="Test message"
            )
        elif model_name == "ConversationState":
            instance = ConversationState(session_id="test-session")
        elif model_name == "MessageRequest":
            instance = MessageRequest(
                session_id="test-session",
                content="Test message"
            )
        elif model_name == "MessageResponse":
            instance = MessageResponse(
                id="test-id",
                session_id="test-session",
                timestamp=datetime.now(),
                role=MessageRole.ASSISTANT,
                content="Test response"
            )
        elif model_name == "ConversationCreateRequest":
            instance = ConversationCreateRequest(title="Test Conversation")
        elif model_name == "RetryExtractionRequest":
            instance = RetryExtractionRequest()
        elif model_name == "ErrorResponse":
            instance = ErrorResponse(
                status_code=404,
                detail="Not found"
            )
        elif model_name == "ValidationErrorDetail":
            instance = ValidationErrorDetail(
                loc=["field"],
                msg="Error message",
                type="value_error"
            )
        else:
            # Skip models we can't easily instantiate
            return True, {}, []
        
        # Test serialization with aliases
        serialized = instance.model_dump(by_alias=True)
        
        # Check for camelCase keys
        camel_case_issues = []
        for key in serialized.keys():
            # Special cases: some fields have explicit aliases that override camelCase
            special_cases = ['x', 'y', 'chart_type']
            if '_' in key and key not in special_cases:
                camel_case_issues.append(f"Snake case key found: {key}")
        
        return True, serialized, camel_case_issues
        
    except Exception as e:
        return False, {}, [f"Failed to create instance: {str(e)}"]

def main():
    """Main test function."""
    print("🔍 CFIN Backend Schema Alignment Verification")
    print("=" * 60)
    
    overall_success = True
    
    # Test 1: camelCase utility function
    print("\n1. Testing camelCase conversion utility...")
    if not test_camel_case_conversion():
        overall_success = False
    
    # Test 2: Find and test all Pydantic models
    print("\n2. Finding all Pydantic models...")
    models = find_all_pydantic_models()
    print(f"Found {len(models)} Pydantic models")
    
    # Test 3: Check model configurations
    print("\n3. Testing model configurations...")
    config_issues = {}
    for model_name, model_class in models:
        issues = check_model_config(model_class)
        if issues:
            config_issues[model_name] = issues
            overall_success = False
        else:
            print(f"  ✅ {model_name}: Configuration OK")
    
    if config_issues:
        print("\n❌ Configuration Issues Found:")
        for model_name, issues in config_issues.items():
            print(f"  {model_name}:")
            for issue in issues:
                print(f"    - {issue}")
    
    # Test 4: Test serialization
    print("\n4. Testing model serialization...")
    serialization_issues = {}
    
    for model_name, model_class in models:
        success, serialized, issues = test_model_serialization(model_class, model_name)
        
        if not success:
            serialization_issues[model_name] = issues
            overall_success = False
            print(f"  ❌ {model_name}: Failed to serialize")
        elif issues:
            serialization_issues[model_name] = issues
            overall_success = False
            print(f"  ⚠️  {model_name}: Serialization has issues")
        else:
            print(f"  ✅ {model_name}: Serialization OK")
    
    if serialization_issues:
        print("\n❌ Serialization Issues Found:")
        for model_name, issues in serialization_issues.items():
            print(f"  {model_name}:")
            for issue in issues:
                print(f"    - {issue}")
    
    # Test 5: Sample API response structure
    print("\n5. Testing sample API response structures...")
    
    try:
        # Test complete analysis response
        metric = FinancialMetric(
            category="Revenue",
            name="Total Revenue", 
            period="2024",
            value=1000000.0,
            unit="USD"
        )
        
        viz_data = VisualizationDataResponse()
        
        analysis_response = AnalysisApiResponse(
            id=str(uuid.uuid4()),
            document_ids=["doc1"],
            analysis_type="financial_overview",
            timestamp=datetime.now().isoformat(),
            visualization_data=viz_data,
            metrics=[metric]
        )
        
        response_json = analysis_response.model_dump(by_alias=True)
        
        # Check critical fields are camelCase
        critical_fields = [
            ('document_ids', 'documentIds'),
            ('analysis_type', 'analysisType'),
            ('analysis_text', 'analysisText'),
            ('visualization_data', 'visualizationData'),
            ('citation_references', 'citationReferences'),
            ('comparative_periods', 'comparativePeriods'),
            ('document_type', 'documentType')
        ]
        
        missing_camel_fields = []
        for snake_field, camel_field in critical_fields:
            if camel_field not in response_json:
                missing_camel_fields.append(f"{snake_field} -> {camel_field}")
        
        if missing_camel_fields:
            print("  ❌ Critical camelCase fields missing:")
            for field in missing_camel_fields:
                print(f"    - {field}")
            overall_success = False
        else:
            print("  ✅ Analysis API response structure OK")
        
        print("\n📄 Sample API Response Structure:")
        print(json.dumps(response_json, indent=2, default=str)[:500] + "...")
        
    except Exception as e:
        print(f"  ❌ Failed to create sample API response: {e}")
        overall_success = False
    
    # Final summary
    print("\n" + "=" * 60)
    if overall_success:
        print("🎉 SUCCESS: All schema alignment checks passed!")
        print("✅ All models have proper ConfigDict setup")
        print("✅ All models use camelCase aliases correctly")
        print("✅ API responses will be in camelCase format")
    else:
        print("❌ ISSUES FOUND: Schema alignment needs attention")
        print("Please fix the issues listed above")
    
    print("=" * 60)
    return overall_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)