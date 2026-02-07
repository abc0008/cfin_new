#!/usr/bin/env python3
"""
Test script for citation repository functionality.
Tests database operations with the new citation schema.
"""

import asyncio
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.database import get_db, engine
from repositories.document_repository import DocumentRepository
from models.database_models import Citation, Document, User
from models.citation import CitationPayload, CitationType, CitationRect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_citation_crud():
    """Test citation CRUD operations with new schema."""
    logger.info("Testing citation CRUD operations...")
    
    async with AsyncSession(engine) as session:
        doc_repo = DocumentRepository(session)
        
        # Create a test user and document first
        test_user = User(
            id="test-user-123",
            email="test@example.com",
            username="testuser",
            hashed_password="dummy_hash"
        )
        session.add(test_user)
        
        test_doc = Document(
            id="test-doc-456",
            filename="test_report.pdf",
            file_path="/tmp/test_report.pdf",
            user_id="test-user-123",
            file_size=1024,
            mime_type="application/pdf",
            upload_timestamp=datetime.utcnow(),
            processing_status="completed"
        )
        session.add(test_doc)
        
        # Create a new citation with the enhanced schema
        test_citation = Citation(
            id="test-cite-789",
            document_id="test-doc-456",
            type="page_location",
            page=5,  # Legacy field
            text="Legacy text field",
            cited_text="Revenue increased by 15% year-over-year",
            document_title="Q4 2023 Financial Report",
            start_page_number=5,
            end_page_number=5,
            rects=json.dumps([{
                "x1": 100, "y1": 200, "x2": 300, "y2": 220,
                "width": 200, "height": 20, "pageNumber": 5
            }]),
            highlight_id="hl-test-789"
        )
        session.add(test_citation)
        
        await session.commit()
        logger.info("✓ Created test citation with new schema")
        
        # Test retrieval
        retrieved = await doc_repo.get_citation("test-cite-789")
        assert retrieved is not None
        assert retrieved.type == "page_location"
        assert retrieved.start_page_number == 5
        assert retrieved.highlight_id == "hl-test-789"
        logger.info("✓ Retrieved citation successfully")
        
        # Test API schema conversion
        api_citation = doc_repo.citation_to_api_schema(retrieved)
        assert api_citation["documentId"] == "test-doc-456"
        assert api_citation["type"] == "page_location"
        assert api_citation["citedText"] == "Revenue increased by 15% year-over-year"
        assert api_citation["startPageNumber"] == 5
        assert len(api_citation["rects"]) == 1
        assert api_citation["rects"][0]["pageNumber"] == 5
        logger.info("✓ API schema conversion working")
        
        # Clean up
        await session.delete(test_citation)
        await session.delete(test_doc)
        await session.delete(test_user)
        await session.commit()
        logger.info("✓ Cleanup completed")
        
    return True


async def test_citation_types():
    """Test different citation types."""
    logger.info("\nTesting different citation types...")
    
    async with AsyncSession(engine) as session:
        doc_repo = DocumentRepository(session)
        
        # Create test data
        test_user = User(id="test-user-2", email="test2@example.com", username="testuser2", hashed_password="dummy_hash")
        test_doc = Document(
            id="test-doc-2",
            filename="test2.pdf",
            file_path="/tmp/test2.pdf",
            user_id="test-user-2",
            file_size=2048,
            mime_type="application/pdf",
            upload_timestamp=datetime.utcnow(),
            processing_status="completed"
        )
        session.add(test_user)
        session.add(test_doc)
        
        # Test different citation types
        citation_types = [
            {
                "type": "page_location",
                "start_page_number": 10,
                "end_page_number": 11,
                "cited_text": "Page-based citation"
            },
            {
                "type": "char_location",
                "start_char_index": 1000,
                "end_char_index": 1050,
                "cited_text": "Character-based citation"
            },
            {
                "type": "content_block_location",
                "start_block_index": 5,
                "end_block_index": 6,
                "cited_text": "Block-based citation"
            }
        ]
        
        created_citations = []
        for i, cite_data in enumerate(citation_types):
            citation = Citation(
                id=f"test-cite-type-{i}",
                document_id="test-doc-2",
                type=cite_data["type"],
                text=f"Test citation {i}",
                cited_text=cite_data["cited_text"],
                document_title="Test Document",
                highlight_id=f"hl-type-{i}",
                **{k: v for k, v in cite_data.items() if k not in ["type", "cited_text"]}
            )
            session.add(citation)
            created_citations.append(citation)
        
        await session.commit()
        logger.info(f"✓ Created {len(citation_types)} citations of different types")
        
        # Verify each type
        for i, citation in enumerate(created_citations):
            api_citation = doc_repo.citation_to_api_schema(citation)
            logger.info(f"  Citation type: {api_citation['type']}")
            
            if api_citation["type"] == "page_location":
                assert api_citation["startPageNumber"] is not None
            elif api_citation["type"] == "char_location":
                assert api_citation["startCharIndex"] is not None
            elif api_citation["type"] == "content_block_location":
                assert api_citation["startBlockIndex"] is not None
        
        logger.info("✓ All citation types verified")
        
        # Clean up
        for citation in created_citations:
            await session.delete(citation)
        await session.delete(test_doc)
        await session.delete(test_user)
        await session.commit()
        
    return True


async def main():
    """Run all async repository tests."""
    logger.info("Starting citation repository tests...\n")
    
    tests_passed = 0
    tests_failed = 0
    
    tests = [
        test_citation_crud,
        test_citation_types
    ]
    
    for test in tests:
        try:
            if await test():
                tests_passed += 1
        except Exception as e:
            logger.error(f"✗ {test.__name__} failed: {str(e)}")
            import traceback
            traceback.print_exc()
            tests_failed += 1
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info(f"Tests passed: {tests_passed}")
    logger.info(f"Tests failed: {tests_failed}")
    logger.info(f"{'='*50}")
    
    return tests_failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)