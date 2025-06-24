#!/usr/bin/env python3
"""
Migration script to add updated_at field to messages table.

This migration adds the missing updated_at column to the messages table
to fix the schema mismatch where the repository code tries to set updated_at
but the field doesn't exist in the database.
"""

import asyncio
import sys
from datetime import datetime
from sqlalchemy import text
from utils.database import AsyncSessionLocal, engine
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_updated_at_to_messages():
    """Add updated_at column to messages table if it doesn't exist."""
    async with AsyncSessionLocal() as session:
        try:
            # First, check if the column already exists
            result = await session.execute(text("""
                SELECT COUNT(*) as count
                FROM pragma_table_info('messages') 
                WHERE name = 'updated_at'
            """))
            column_exists = result.scalar() > 0
            
            if column_exists:
                logger.info("updated_at column already exists in messages table")
                return
            
            logger.info("Adding updated_at column to messages table...")
            
            # Add the updated_at column (SQLite doesn't support non-constant defaults)
            await session.execute(text("""
                ALTER TABLE messages 
                ADD COLUMN updated_at DATETIME
            """))
            
            # Update existing records to set updated_at = created_at
            result = await session.execute(text("""
                UPDATE messages 
                SET updated_at = created_at
            """))
            
            affected_rows = result.rowcount
            logger.info(f"Updated {affected_rows} existing messages with updated_at = created_at")
            
            await session.commit()
            logger.info("Migration completed successfully!")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Migration failed: {e}")
            raise

async def main():
    """Run the migration."""
    try:
        logger.info("Starting migration to add updated_at field to messages table...")
        await add_updated_at_to_messages()
        logger.info("Migration completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)