#!/usr/bin/env python3
"""
Test that citations are being saved correctly with searchable_text.
"""

import asyncio
import json
import logging
from sqlalchemy import text
from utils.database import engine
from repositories.document_repository import DocumentRepository
from utils.database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_citation_creation():
    """Test creating a citation with searchable_text."""
    async for db in get_db():
        try:
            doc_repo = DocumentRepository(db)
            
            # Test citation data with searchable_text
            citation_data = {
                "cited_text": "2024Q1 2024Q2 2024Q3 2024Q4\nInterest Income 900.0 910.0 920.0 930.0",
                "display_text": "Interest Income: $900.0M",
                "searchable_text": "900.0",
                "type": "page_location",
                "start_page_number": 2,
                "end_page_number": 2,
                "document_title": "Test Document"
            }
            
            logger.info(f"Creating citation with searchable_text: '{citation_data['searchable_text']}'")
            
            # Create citation
            created = await doc_repo.add_citation(
                document_id="8ab86f50-1e25-42ac-b27f-a5e27496275d",
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
                    logger.info(f"Database check:")
                    logger.info(f"  ID: {row.id}")
                    logger.info(f"  CitedText: {row.cited_text[:50]}...")
                    logger.info(f"  DisplayText: {row.display_text}")
                    logger.info(f"  SearchableText: {row.searchable_text}")
                    
                    if row.searchable_text == "900.0":
                        logger.info("✅ searchable_text saved correctly!")
                    else:
                        logger.error(f"❌ searchable_text not saved correctly: {row.searchable_text}")
                else:
                    logger.error("❌ Citation not found in database")
                    
            # Clean up
            await doc_repo.delete_citation(created.id)
            logger.info("✅ Test citation deleted")
            
        except Exception as e:
            logger.error(f"❌ Error during test: {e}")
            raise
        finally:
            await db.close()

async def check_existing_citations():
    """Check existing citations for searchable_text."""
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(searchable_text) as with_searchable,
                   COUNT(CASE WHEN searchable_text IS NOT NULL AND searchable_text != '' THEN 1 END) as non_empty
            FROM citations
            WHERE document_id = '8ab86f50-1e25-42ac-b27f-a5e27496275d'
        """))
        
        stats = result.fetchone()
        logger.info(f"\n📊 Citation Statistics:")
        logger.info(f"  Total citations: {stats.total}")
        logger.info(f"  With searchable_text field: {stats.with_searchable}")
        logger.info(f"  With non-empty searchable_text: {stats.non_empty}")

async def main():
    """Run tests."""
    logger.info("Testing citation creation with searchable_text...")
    
    try:
        await test_citation_creation()
        await check_existing_citations()
        logger.info("\n✅ All tests completed")
    except Exception as e:
        logger.error(f"❌ Tests failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())