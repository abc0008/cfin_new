#!/usr/bin/env python3
"""
Update existing citations to add searchable_text field.
"""

import asyncio
import logging
import re
from sqlalchemy import text
from utils.database import engine
from models.database_models import Citation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def update_existing_citations():
    """Update existing citations to add searchable_text."""
    async with engine.begin() as conn:
        try:
            # Get all citations
            result = await conn.execute(text("""
                SELECT id, cited_text, display_text
                FROM citations
                WHERE searchable_text IS NULL
            """))
            
            citations = result.fetchall()
            logger.info(f"Found {len(citations)} citations to update")
            
            updated_count = 0
            for citation in citations:
                citation_id = citation.id
                cited_text = citation.cited_text or ""
                display_text = citation.display_text
                
                # Extract numeric value for searchable_text
                searchable_text = None
                
                # If we have display_text, extract numeric value from it
                if display_text:
                    numeric_match = re.search(r'(\d+\.?\d*)', display_text)
                    if numeric_match:
                        searchable_text = numeric_match.group(1)
                elif ":" in cited_text and len(cited_text) < 100:
                    # Try to extract from cited_text if it's already processed
                    numeric_match = re.search(r'(\d+\.?\d*)', cited_text.split(":")[-1])
                    if numeric_match:
                        searchable_text = numeric_match.group(1)
                
                if searchable_text:
                    await conn.execute(text("""
                        UPDATE citations
                        SET searchable_text = :searchable_text
                        WHERE id = :id
                    """), {"searchable_text": searchable_text, "id": citation_id})
                    updated_count += 1
                    logger.info(f"Updated citation {citation_id[:8]}... with searchable_text: {searchable_text}")
            
            logger.info(f"✅ Updated {updated_count} citations with searchable_text")
            
        except Exception as e:
            logger.error(f"❌ Error updating citations: {e}")
            raise

async def main():
    """Run the update."""
    logger.info("Starting citation update...")
    
    try:
        await update_existing_citations()
        logger.info("✅ Update completed successfully")
    except Exception as e:
        logger.error(f"❌ Update failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())