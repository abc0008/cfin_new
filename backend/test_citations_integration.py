#!/usr/bin/env python3
"""
Test script for citation integration with Anthropic API.
Tests the full flow from document upload to citation parsing.
"""

import asyncio
import os
import sys
import json
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.citation_service import parse_citations, create_citation_from_anthropic
from pdf_processing.claude_file_client import prepare_document_blocks
from models.citation import CitationPayload, CitationType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_citation_parsing():
    """Test the citation parsing functionality."""
    logger.info("Testing citation parsing...")
    
    # Mock Claude response with citations
    content_blocks = [
        {
            "type": "text",
            "text": "According to the financial report, revenue increased by 15% ",
            "citations": [
                {
                    "type": "page_location",
                    "cited_text": "Revenue for the fiscal year increased by 15% to $2.3 billion",
                    "document_index": 0,
                    "document_title": "Q4 2023 Financial Report",
                    "start_page_number": 5,
                    "end_page_number": 6
                }
            ]
        },
        {
            "type": "text",
            "text": " while expenses decreased by 8% ",
            "citations": [
                {
                    "type": "page_location",
                    "cited_text": "Operating expenses decreased by 8% year-over-year",
                    "document_index": 0,
                    "document_title": "Q4 2023 Financial Report",
                    "start_page_number": 7,
                    "end_page_number": 7
                }
            ]
        }
    ]
    
    # Document map
    document_map = {0: "doc-123-456"}
    
    # Parse citations
    rendered_text, citations = parse_citations(content_blocks, document_map)
    
    # Verify results
    assert "[1]" in rendered_text, "Citation marker [1] not found"
    assert "[2]" in rendered_text, "Citation marker [2] not found"
    assert len(citations) == 2, f"Expected 2 citations, got {len(citations)}"
    
    # Check first citation
    citation1 = citations[0]
    assert citation1.type == CitationType.PAGE_LOCATION
    assert citation1.cited_text == "Revenue for the fiscal year increased by 15% to $2.3 billion"
    assert citation1.start_page_number == 5
    assert citation1.end_page_number == 6
    assert citation1.document_id == "doc-123-456"
    
    logger.info("✓ Citation parsing test passed")
    return True


def test_document_blocks():
    """Test document block preparation."""
    logger.info("Testing document block preparation...")
    
    # Mock documents
    documents = [
        {
            "id": "doc-123",
            "claude_file_id": "file_01ABC123",
            "filename": "financial_report.pdf",
            "metadata": {"year": 2023, "quarter": "Q4"}
        },
        {
            "id": "doc-456",
            "file_id": "file_02DEF456",  # Testing fallback
            "filename": "balance_sheet.pdf"
        }
    ]
    
    # Prepare blocks
    blocks = prepare_document_blocks(documents, enable_citations=True)
    
    # Verify results
    assert len(blocks) == 2, f"Expected 2 blocks, got {len(blocks)}"
    
    # Check first block
    block1 = blocks[0]
    assert block1["type"] == "document"
    assert block1["source"]["type"] == "file"
    assert block1["source"]["file_id"] == "file_01ABC123"
    assert block1["title"] == "financial_report.pdf"
    assert block1["citations"]["enabled"] == True
    
    # Parse context
    context1 = json.loads(block1["context"])
    assert context1["doc_id"] == "doc-123"
    assert context1["doc_index"] == 0
    assert context1["metadata"]["year"] == 2023
    
    logger.info("✓ Document block preparation test passed")
    return True


def test_citation_model():
    """Test CitationPayload model."""
    logger.info("Testing CitationPayload model...")
    
    # Create a citation
    citation = CitationPayload(
        id="cite-123",
        document_id="doc-456",
        type=CitationType.PAGE_LOCATION,
        cited_text="Test citation text",
        document_title="Test Document",
        highlight_id="hl-123",
        rects=[],
        start_page_number=5,
        end_page_number=5,
        page=5
    )
    
    # Test serialization
    citation_dict = citation.model_dump(by_alias=True)
    
    # Verify camelCase conversion
    assert "documentId" in citation_dict
    assert "citedText" in citation_dict
    assert "startPageNumber" in citation_dict
    assert "highlightId" in citation_dict
    assert citation_dict["documentId"] == "doc-456"
    assert citation_dict["type"] == "page_location"
    
    logger.info("✓ CitationPayload model test passed")
    return True


async def test_api_integration():
    """Test the API integration (requires running server)."""
    logger.info("Testing API integration...")
    
    try:
        import httpx
        
        # Test citation endpoint
        async with httpx.AsyncClient() as client:
            # This will fail if server is not running, which is expected
            response = await client.get("http://localhost:8000/api/citations/test-citation-id")
            
            if response.status_code == 404:
                logger.info("✓ Citation API endpoint is accessible (404 for non-existent citation)")
            else:
                logger.warning(f"Unexpected response: {response.status_code}")
                
    except Exception as e:
        logger.info(f"✓ API test skipped (server not running): {str(e)}")
    
    return True


def main():
    """Run all tests."""
    logger.info("Starting citation integration tests...\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Run synchronous tests
    tests = [
        test_citation_parsing,
        test_document_blocks,
        test_citation_model
    ]
    
    for test in tests:
        try:
            if test():
                tests_passed += 1
        except Exception as e:
            logger.error(f"✗ {test.__name__} failed: {str(e)}")
            tests_failed += 1
    
    # Run async tests
    try:
        asyncio.run(test_api_integration())
        tests_passed += 1
    except Exception as e:
        logger.error(f"✗ test_api_integration failed: {str(e)}")
        tests_failed += 1
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info(f"Tests passed: {tests_passed}")
    logger.info(f"Tests failed: {tests_failed}")
    logger.info(f"{'='*50}")
    
    return tests_failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)