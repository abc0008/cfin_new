#!/usr/bin/env python3
"""
Comprehensive integration test for the citation backend changes.
Tests the full flow without database complexities.
"""

import sys
import json
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Test all major components
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_all_components():
    """Test all backend components work together."""
    logger.info("Testing backend citation integration...\n")
    
    # Test 1: Citation models
    logger.info("1. Testing Citation Models...")
    from models.citation import CitationPayload, CitationType, CitationRect
    
    citation = CitationPayload(
        id="test-123",
        document_id="doc-456",
        type=CitationType.PAGE_LOCATION,
        cited_text="Test citation text",
        document_title="Test Document",
        highlight_id="hl-123",
        rects=[
            CitationRect(
                x1=100, y1=200, x2=300, y2=220,
                width=200, height=20, page_number=5
            )
        ],
        start_page_number=5,
        end_page_number=5
    )
    
    # Verify serialization
    citation_dict = citation.model_dump(by_alias=True)
    assert citation_dict["documentId"] == "doc-456"
    assert citation_dict["citedText"] == "Test citation text"
    assert len(citation_dict["rects"]) == 1
    assert citation_dict["rects"][0]["pageNumber"] == 5
    logger.info("✓ Citation models working correctly")
    
    # Test 2: Citation Service
    logger.info("\n2. Testing Citation Service...")
    from services.citation_service import parse_citations, get_citation_signature
    
    # Mock Claude response
    content_blocks = [
        {
            "type": "text",
            "text": "The report shows revenue of ",
            "citations": []
        },
        {
            "type": "text",
            "text": "$2.3 billion",
            "citations": [{
                "type": "page_location",
                "cited_text": "Total revenue: $2.3 billion",
                "document_index": 0,
                "document_title": "Financial Report",
                "start_page_number": 3,
                "end_page_number": 3
            }]
        }
    ]
    
    document_map = {0: "doc-789"}
    rendered_text, citations = parse_citations(content_blocks, document_map)
    
    assert "[1]" in rendered_text
    assert len(citations) == 1
    assert citations[0].document_id == "doc-789"
    assert citations[0].start_page_number == 3
    logger.info("✓ Citation service parsing correctly")
    
    # Test 3: Files API Integration
    logger.info("\n3. Testing Files API Integration...")
    from pdf_processing.claude_file_client import prepare_document_blocks
    
    documents = [{
        "id": "doc-123",
        "claude_file_id": "file_ABC123",
        "filename": "report.pdf",
        "metadata": {"year": 2023}
    }]
    
    blocks = prepare_document_blocks(documents, enable_citations=True)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "document"
    assert blocks[0]["source"]["file_id"] == "file_ABC123"
    assert blocks[0]["citations"]["enabled"] == True
    
    context = json.loads(blocks[0]["context"])
    assert context["doc_id"] == "doc-123"
    assert context["doc_index"] == 0
    logger.info("✓ Files API document blocks formatted correctly")
    
    # Test 4: API Response Format
    logger.info("\n4. Testing API Response Format...")
    
    # Test citation deduplication
    from services.citation_service import deduplicate_citations
    
    citations_list = [
        CitationPayload(
            id="cite-1",
            document_id="doc-1",
            type=CitationType.PAGE_LOCATION,
            cited_text="Same text",
            document_title="Doc",
            highlight_id="hl-1",
            start_page_number=5,
            end_page_number=5,
            rects=[]
        ),
        CitationPayload(
            id="cite-2",
            document_id="doc-1",
            type=CitationType.PAGE_LOCATION,
            cited_text="Same text",
            document_title="Doc",
            highlight_id="hl-2",
            start_page_number=5,
            end_page_number=5,
            rects=[]
        ),
        CitationPayload(
            id="cite-3",
            document_id="doc-1",
            type=CitationType.PAGE_LOCATION,
            cited_text="Different text",
            document_title="Doc",
            highlight_id="hl-3",
            start_page_number=6,
            end_page_number=6,
            rects=[]
        )
    ]
    
    unique_citations = deduplicate_citations(citations_list)
    assert len(unique_citations) == 2  # Should dedupe the first two
    logger.info("✓ Citation deduplication working")
    
    # Test 5: Full Integration
    logger.info("\n5. Testing Full Integration Flow...")
    
    # Simulate the full flow
    # 1. Documents prepared with citations enabled
    # 2. Claude response parsed for citations
    # 3. Citations formatted for API response
    
    final_api_response = {
        "text": rendered_text,
        "citations": [c.model_dump(by_alias=True) for c in citations]
    }
    
    assert "text" in final_api_response
    assert "citations" in final_api_response
    assert len(final_api_response["citations"]) == 1
    assert final_api_response["citations"][0]["highlightId"] is not None
    logger.info("✓ Full integration flow working")
    
    return True


def main():
    """Run all tests."""
    try:
        success = test_all_components()
        
        if success:
            logger.info("\n" + "="*50)
            logger.info("✅ ALL BACKEND TESTS PASSED!")
            logger.info("="*50)
            logger.info("\nBackend is ready for:")
            logger.info("- Citation parsing from Claude responses")
            logger.info("- Document blocks with Files API")
            logger.info("- Citation deduplication")
            logger.info("- API response formatting")
            logger.info("\nNext step: Frontend implementation")
            return 0
        else:
            return 1
    except Exception as e:
        logger.error(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())