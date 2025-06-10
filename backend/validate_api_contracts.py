#!/usr/bin/env python3
"""
API Contract Validation Script
Validates that backend Pydantic models properly align with frontend expectations
"""

import inspect
from typing import get_type_hints, get_args, get_origin, Union, List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

# Import all models
from models.api_models import *
from models.document import *
from models.analysis import *
from models.message import *
from models.visualization import *
from models.citation import *

def to_camel(string: str) -> str:
    """Convert snake_case to camelCase"""
    parts = string.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:]) if len(parts) > 1 else string

def get_model_fields_info(model: type[BaseModel]) -> Dict[str, Dict[str, Any]]:
    """Extract field information from a Pydantic model"""
    fields_info = {}
    
    # Get model fields
    for field_name, field_info in model.model_fields.items():
        # Get the field type
        field_type = field_info.annotation
        
        # Check if field has an alias
        alias = None
        if isinstance(field_info, FieldInfo) and field_info.alias:
            alias = field_info.alias
        
        # Check if model has alias_generator
        has_alias_generator = False
        if hasattr(model, 'model_config'):
            config = model.model_config
            if isinstance(config, dict):
                has_alias_generator = 'alias_generator' in config
            elif hasattr(config, 'alias_generator'):
                has_alias_generator = config.alias_generator is not None
        elif hasattr(model, 'Config'):
            has_alias_generator = hasattr(model.Config, 'alias_generator')
        
        # Determine expected alias
        expected_alias = alias if alias else (to_camel(field_name) if has_alias_generator else field_name)
        
        fields_info[field_name] = {
            'type': str(field_type),
            'alias': alias,
            'expected_alias': expected_alias,
            'has_alias_generator': has_alias_generator,
            'is_optional': get_origin(field_type) is Union and type(None) in get_args(field_type),
            'needs_alias': field_name != expected_alias and not alias and not has_alias_generator
        }
    
    return fields_info

def validate_model(model: type[BaseModel], model_name: str) -> List[str]:
    """Validate a single model for API contract compliance"""
    issues = []
    fields_info = get_model_fields_info(model)
    
    # Check if model has alias generator
    has_global_alias_generator = False
    if hasattr(model, 'model_config'):
        config = model.model_config
        if isinstance(config, dict):
            has_global_alias_generator = 'alias_generator' in config
        elif hasattr(config, 'alias_generator'):
            has_global_alias_generator = config.alias_generator is not None
    elif hasattr(model, 'Config'):
        has_global_alias_generator = hasattr(model.Config, 'alias_generator')
    
    # Validate each field
    for field_name, info in fields_info.items():
        # Check if snake_case fields need aliases
        if '_' in field_name and info['needs_alias']:
            issues.append(f"{model_name}.{field_name}: Missing camelCase alias (expected: {info['expected_alias']})")
    
    # Check if model should have alias generator
    snake_case_fields = [f for f in fields_info.keys() if '_' in f]
    if snake_case_fields and not has_global_alias_generator:
        aliased_fields = [f for f, i in fields_info.items() if i['alias']]
        if len(aliased_fields) < len(snake_case_fields):
            issues.append(f"{model_name}: Has snake_case fields but no alias_generator in Config")
    
    return issues

def main():
    """Run validation on all API models"""
    print("=== API Contract Validation Report ===\n")
    
    # Models to validate (API response models)
    models_to_check = [
        # Document models
        (DocumentUploadResponse, "DocumentUploadResponse"),
        (ProcessedDocument, "ProcessedDocument"),
        (DocumentMetadata, "DocumentMetadata"),
        
        # Analysis models
        (AnalysisApiResponse, "AnalysisApiResponse"),
        (AnalysisResult, "AnalysisResult"),
        (AnalysisRequest, "AnalysisRequest"),
        (FinancialMetric, "FinancialMetric"),
        (FinancialRatio, "FinancialRatio"),
        (ComparativePeriod, "ComparativePeriod"),
        
        # Message models
        (Message, "Message"),
        (MessageResponse, "MessageResponse"),
        (MessageRequest, "MessageRequest"),
        (ConversationState, "ConversationState"),
        (ConversationCreateRequest, "ConversationCreateRequest"),
        
        # Visualization models
        (ChartData, "ChartData"),
        (TableData, "TableData"),
        (ChartConfig, "ChartConfig"),
        (TableConfig, "TableConfig"),
        
        # Other models
        (Citation, "Citation"),
        (RetryExtractionRequest, "RetryExtractionRequest"),
    ]
    
    total_issues = 0
    
    for model_class, model_name in models_to_check:
        try:
            issues = validate_model(model_class, model_name)
            if issues:
                print(f"\n❌ {model_name}:")
                for issue in issues:
                    print(f"   - {issue}")
                    total_issues += 1
            else:
                print(f"✅ {model_name}: All fields properly aliased")
        except Exception as e:
            print(f"⚠️  {model_name}: Error during validation - {str(e)}")
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Total issues found: {total_issues}")
    
    if total_issues > 0:
        print("\n📋 Recommended fixes:")
        print("1. Add 'alias_generator = to_camel' to model Config")
        print("2. Add 'allow_population_by_field_name = True' to allow both formats")
        print("3. Or add explicit Field(alias='camelCaseName') for each snake_case field")
        
        print("\nExample fix:")
        print("""
class MyModel(BaseModel):
    snake_case_field: str
    another_field: int
    
    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True
""")

if __name__ == "__main__":
    main()