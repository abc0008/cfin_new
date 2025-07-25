#!/usr/bin/env python3
"""
Test direct citation creation with searchable_text.
"""

import asyncio
import logging
from sqlalchemy import text
from utils.database import engine
from repositories.document_repository import DocumentRepository
from utils.database import get_db
from models.database_models import Citation
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_direct_citation():
    """Test creating a citation directly with searchable_text."""
    async for db in get_db():
        try:
            # Create a test citation with searchable_text
            citation_data = {
                "id": "test-citation-001",
                "document_id": "8ab86f50-1e25-42ac-b27f-a5e27496275d",
                "cited_text": "2024Q1 2024Q2 2024Q3 2024Q4\nInterest Income 900.0 910.0 920.0 930.0",
                "display_text": "Interest Income: $920.0M",
                "searchable_text": "920.0",
                "type": "page_location",
                "start_page_number": 2,
                "end_page_number": 2,
                "document_title": "Bank 5Q Trend Report",
                "rects": json.dumps([]),  # Empty for now
                "message_id": None
            }
            
            doc_repo = DocumentRepository(db)
            
            # Remove message_id from citation_data before creating
            message_id = citation_data.pop("message_id", None)
            
            logger.info(f"Creating citation with searchable_text: '{citation_data.get('searchable_text')}'")
            
            # Create citation using the same method as conversation_service
            created = await doc_repo.create_citation_from_dict(
                document_id=citation_data["document_id"],
                citation_data=citation_data
            )
            
            logger.info(f"Created citation: {created.id}")
            
            # Query database directly to verify
            async with engine.begin() as conn:
                result = await conn.execute(text("""
                    SELECT id, cited_text, display_text, searchable_text 
                    FROM citations 
                    WHERE id = :id
                """), {"id": created.id})
                
                row = result.fetchone()
                if row:
                    logger.info(f"\n✅ Database verification:")
                    logger.info(f"  ID: {row.id}")
                    logger.info(f"  CitedText: {row.cited_text[:50]}...")
                    logger.info(f"  DisplayText: {row.display_text}")
                    logger.info(f"  SearchableText: {row.searchable_text}")
                    
                    # Now test the rect finding
                    citations = await doc_repo.get_citations_for_document(citation_data["document_id"])
                    test_citation = next((c for c in citations if c.id == created.id), None)
                    
                    if test_citation:
                        logger.info(f"\n🔍 Testing rect finding:")
                        logger.info(f"  Citation has searchableText in API response: {hasattr(test_citation, 'searchable_text')}")
                        if hasattr(test_citation, 'searchable_text'):
                            logger.info(f"  searchable_text value: '{test_citation.searchable_text}'")
                else:
                    logger.error("❌ Citation not found in database")
                    
            # Clean up
            await conn.execute(text("DELETE FROM citations WHERE id = :id"), {"id": created.id})
            logger.info("\n✅ Test citation cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Error during test: {e}")
            raise
        finally:
            await db.close()

async def main():
    """Run tests."""
    logger.info("Testing direct citation creation with searchable_text...")
    
    try:
        await test_direct_citation()
        logger.info("\n✅ Test completed successfully")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())