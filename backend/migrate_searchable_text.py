#!/usr/bin/env python3
"""
Migration script to add searchable_text column to citations table.

Run this script after updating the Citation model to include searchable_text field.
"""

import asyncio
import logging
from sqlalchemy import text
from utils.database import engine
from models.database_models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_searchable_text_column():
    """Add searchable_text column to citations table if it doesn't exist."""
    async with engine.begin() as conn:
        try:
            # Check if column already exists
            result = await conn.execute(text("""
                SELECT COUNT(*) 
                FROM pragma_table_info('citations') 
                WHERE name = 'searchable_text'
            """))
            column_exists = result.scalar() > 0
            
            if not column_exists:
                logger.info("Adding searchable_text column to citations table...")
                await conn.execute(text("""
                    ALTER TABLE citations 
                    ADD COLUMN searchable_text TEXT
                """))
                logger.info("✅ Successfully added searchable_text column")
            else:
                logger.info("✅ searchable_text column already exists")
                
        except Exception as e:
            logger.error(f"❌ Error during migration: {e}")
            raise

async def main():
    """Run the migration."""
    logger.info("Starting searchable_text migration...")
    
    try:
        await add_searchable_text_column()
        logger.info("✅ Migration completed successfully")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())