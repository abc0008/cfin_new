#!/usr/bin/env python3
"""
Migration script to add missing fields to messages table for camelCase/snake_case consistency.
Run this script to add the missing columns: referenced_documents, referenced_analyses
"""

import asyncio
import logging
import sys
from sqlalchemy import text
from utils.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_message_fields():
    """Add missing referenced_documents and referenced_analyses fields to messages table."""
    
    try:
        # Check if columns already exist
        check_sql = """
        SELECT name FROM pragma_table_info('messages') 
        WHERE name IN ('referenced_documents', 'referenced_analyses');
        """
        
        async with engine.begin() as conn:
            result = await conn.execute(text(check_sql))
            existing_columns = [row[0] for row in result.fetchall()]
            
            if len(existing_columns) > 0:
                logger.info(f"Some message fields already exist: {existing_columns}")
                if len(existing_columns) == 2:
                    logger.info("All message fields already exist. Migration not needed.")
                    return
            
            logger.info("Adding referenced documents and analyses fields to messages table...")
            
            # SQLite doesn't support adding multiple columns in one statement
            statements = [
                "ALTER TABLE messages ADD COLUMN referenced_documents JSON DEFAULT '[]'",
                "ALTER TABLE messages ADD COLUMN referenced_analyses JSON DEFAULT '[]'"
            ]
            
            for stmt in statements:
                try:
                    await conn.execute(text(stmt))
                    logger.info(f"Executed: {stmt}")
                except Exception as e:
                    if "duplicate column name" in str(e).lower():
                        logger.info(f"Column already exists, skipping: {stmt}")
                    else:
                        raise
                        
            await conn.commit()
            logger.info("Message fields migration completed successfully!")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        if 'engine' in locals():
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_message_fields())