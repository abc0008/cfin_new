#!/usr/bin/env python3
"""
Check current citations in the database after cleanup.
"""

import asyncio
import logging
from sqlalchemy import text
from utils.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_citations():
    """Check what citations exist in the database."""
    async with engine.begin() as conn:
        # Get citation summary
        result = await conn.execute(text("""
            SELECT 
                c.document_id,
                d.filename,
                COUNT(*) as citation_count,
                COUNT(CASE WHEN c.searchable_text IS NOT NULL AND c.searchable_text != '' THEN 1 END) as with_searchable,
                MIN(c.created_at) as oldest,
                MAX(c.created_at) as newest
            FROM citations c
            LEFT JOIN documents d ON c.document_id = d.id
            GROUP BY c.document_id, d.filename
            ORDER BY newest DESC
        """))
        
        rows = result.fetchall()
        
        if not rows:
            logger.info("📭 No citations found in database")
            return
        
        logger.info(f"\n📊 Citation Summary by Document:")
        logger.info("=" * 80)
        
        for row in rows:
            logger.info(f"\nDocument: {row.filename}")
            logger.info(f"  ID: {row.document_id}")
            logger.info(f"  Total Citations: {row.citation_count}")
            logger.info(f"  With SearchableText: {row.with_searchable}")
            logger.info(f"  Date Range: {row.oldest} to {row.newest}")
            
        # Get sample citations from the most recent document
        if rows:
            latest_doc_id = rows[0].document_id
            logger.info(f"\n📋 Sample citations from latest document ({rows[0].filename}):")
            
            sample_result = await conn.execute(text("""
                SELECT 
                    id,
                    cited_text,
                    display_text,
                    searchable_text,
                    start_page_number,
                    created_at
                FROM citations 
                WHERE document_id = :doc_id
                ORDER BY created_at DESC
                LIMIT 3
            """), {"doc_id": latest_doc_id})
            
            samples = sample_result.fetchall()
            for s in samples:
                logger.info(f"\n  Citation: {s.id[:8]}...")
                logger.info(f"    CitedText: {s.cited_text[:50] if s.cited_text else 'None'}...")
                logger.info(f"    DisplayText: {s.display_text}")
                logger.info(f"    SearchableText: {s.searchable_text}")
                logger.info(f"    Page: {s.start_page_number}")

async def main():
    """Run check."""
    logger.info("🔍 Checking current citations in database...")
    await check_citations()

if __name__ == "__main__":
    asyncio.run(main())