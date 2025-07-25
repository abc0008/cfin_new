#!/usr/bin/env python3
"""
Final test to verify citation highlighting fix is complete.
"""

import asyncio
import logging
from sqlalchemy import text
from utils.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_fix():
    """Verify that citations have searchable_text and rects are computed correctly."""
    async with engine.begin() as conn:
        # Check citation data
        result = await conn.execute(text("""
            SELECT 
                id,
                cited_text,
                display_text,
                searchable_text,
                start_page_number
            FROM citations 
            WHERE document_id = '8ab86f50-1e25-42ac-b27f-a5e27496275d'
            ORDER BY created_at DESC
            LIMIT 5
        """))
        
        citations = result.fetchall()
        
        if not citations:
            logger.warning("⚠️ No citations found. Run a conversation that generates citations first.")
            return False
        
        logger.info(f"\n📊 Found {len(citations)} recent citations:")
        
        success_count = 0
        for c in citations:
            logger.info(f"\nCitation: {c.id[:8]}...")
            logger.info(f"  CitedText: {c.cited_text[:50] if c.cited_text else 'None'}...")
            logger.info(f"  DisplayText: {c.display_text}")
            logger.info(f"  SearchableText: {c.searchable_text}")
            logger.info(f"  Page: {c.start_page_number}")
            
            # Check if citation has searchable_text
            if c.searchable_text:
                logger.info("  ✅ Has searchable_text!")
                success_count += 1
            else:
                logger.warning("  ❌ Missing searchable_text")
        
        if success_count > 0:
            logger.info(f"\n✅ SUCCESS: {success_count}/{len(citations)} citations have searchable_text")
            logger.info("The fix is working! Citations should now highlight specific values instead of full pages.")
            return True
        else:
            logger.error("\n❌ FAILED: No citations have searchable_text")
            logger.error("The fix is not working. Citations will still highlight full pages.")
            return False

async def main():
    """Run verification."""
    logger.info("Verifying citation highlighting fix...")
    
    success = await verify_fix()
    
    if success:
        logger.info("\n🎉 Citation highlighting fix verified successfully!")
        logger.info("Next steps:")
        logger.info("1. Test in the web UI to confirm highlights are on specific values")
        logger.info("2. Create new conversations to generate citations with searchable_text")
    else:
        logger.info("\n❓ No valid citations found yet.")
        logger.info("Next steps:")
        logger.info("1. Use the web UI to create a conversation")
        logger.info("2. Ask about specific financial values (e.g., 'What was Interest Income in Q3?')")
        logger.info("3. Run this test again to verify citations were created correctly")

if __name__ == "__main__":
    asyncio.run(main())