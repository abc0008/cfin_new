#!/usr/bin/env python3
"""
Clear old citations that don't have searchable_text field populated.
These citations cause full table/page highlights instead of specific values.
"""

import asyncio
import logging
from sqlalchemy import text
from utils.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def clear_old_citations():
    """Clear citations without searchable_text."""
    async with engine.begin() as conn:
        # First, count how many citations we'll delete
        count_result = await conn.execute(text("""
            SELECT COUNT(*) as count
            FROM citations 
            WHERE searchable_text IS NULL OR searchable_text = ''
        """))
        count = count_result.scalar()
        
        logger.info(f"🗑️  Found {count} citations without searchable_text to delete")
        
        if count > 0:
            # Delete old citations
            await conn.execute(text("""
                DELETE FROM citations 
                WHERE searchable_text IS NULL OR searchable_text = ''
            """))
            
            logger.info(f"✅ Deleted {count} old citations")
            
            # Verify remaining citations
            verify_result = await conn.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN searchable_text IS NOT NULL AND searchable_text != '' THEN 1 END) as with_searchable
                FROM citations
            """))
            row = verify_result.fetchone()
            
            logger.info(f"📊 Remaining citations: {row.total} total, {row.with_searchable} with searchable_text")
        else:
            logger.info("✨ No old citations to delete")

async def main():
    """Run cleanup."""
    logger.info("🧹 Cleaning up old citations without searchable_text...")
    await clear_old_citations()
    logger.info("\n✅ Cleanup complete! New citations will highlight specific values correctly.")

if __name__ == "__main__":
    asyncio.run(main())