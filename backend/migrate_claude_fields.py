#!/usr/bin/env python3
"""
Migration script to add Claude API optimization fields to documents table.
Run this script to add the new columns: full_text, text_sha256, claude_file_id
"""

import asyncio
import logging
import sys
from sqlalchemy import text
from utils.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_claude_fields():
    """Add Claude optimization fields to documents table."""
    
    migration_sql = """
    -- Add Claude API optimization fields
    ALTER TABLE documents
        ADD COLUMN full_text TEXT,
        ADD COLUMN text_sha256 VARCHAR(64),
        ADD COLUMN claude_file_id VARCHAR(40);

    -- Create index for text deduplication
    CREATE INDEX IF NOT EXISTS idx_documents_text_sha ON documents(text_sha256);
    """
    
    try:
        # engine is already imported from utils.database
        
        # Check if columns already exist
        check_sql = """
        SELECT name FROM pragma_table_info('documents') 
        WHERE name IN ('full_text', 'text_sha256', 'claude_file_id');
        """
        
        async with engine.begin() as conn:
            result = await conn.execute(text(check_sql))
            existing_columns = [row[0] for row in result.fetchall()]
            
            if len(existing_columns) > 0:
                logger.info(f"Some Claude fields already exist: {existing_columns}")
                if len(existing_columns) == 3:
                    logger.info("All Claude fields already exist. Migration not needed.")
                    return
            
            logger.info("Adding Claude optimization fields to documents table...")
            
            # SQLite doesn't support adding multiple columns in one statement
            statements = [
                "ALTER TABLE documents ADD COLUMN full_text TEXT",
                "ALTER TABLE documents ADD COLUMN text_sha256 VARCHAR(64)", 
                "ALTER TABLE documents ADD COLUMN claude_file_id VARCHAR(40)",
                "CREATE INDEX IF NOT EXISTS idx_documents_text_sha ON documents(text_sha256)"
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
            logger.info("Migration completed successfully!")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        if 'engine' in locals():
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_claude_fields()) 