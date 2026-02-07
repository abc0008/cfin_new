#!/usr/bin/env python3
"""
Migration script to update citations table for Anthropic citation integration.
This migration:
- Adds new fields for different citation types (page, char, block)
- Converts bounding_box to rects array
- Adds highlight_id and other required fields
"""

import asyncio
import logging
import sys
import json
from sqlalchemy import text
from utils.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_citations_anthropic():
    """Update citations table for Anthropic integration."""
    
    try:
        async with engine.begin() as conn:
            # Check if new columns already exist
            check_sql = """
            SELECT name FROM pragma_table_info('citations') 
            WHERE name IN ('type', 'rects', 'highlight_id', 'cited_text');
            """
            
            result = await conn.execute(text(check_sql))
            existing_columns = [row[0] for row in result.fetchall()]
            
            if len(existing_columns) >= 4:
                logger.info("Citation fields already migrated. Skipping migration.")
                return
            
            logger.info("Starting citation table migration...")
            
            # Create temporary table with new schema
            create_temp_table_sql = """
            CREATE TABLE citations_new (
                id VARCHAR PRIMARY KEY,
                document_id VARCHAR NOT NULL,
                type VARCHAR(50),
                page INTEGER,
                text TEXT NOT NULL,
                section VARCHAR,
                cited_text TEXT,
                document_title VARCHAR(255),
                start_page_number INTEGER,
                end_page_number INTEGER,
                start_char_index INTEGER,
                end_char_index INTEGER,
                start_block_index INTEGER,
                end_block_index INTEGER,
                rects TEXT DEFAULT '[]',
                highlight_id VARCHAR(36),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );
            """
            
            await conn.execute(text(create_temp_table_sql))
            logger.info("Created temporary table with new schema")
            
            # Copy existing data, converting bounding_box to rects
            migrate_data_sql = """
            INSERT INTO citations_new (
                id, document_id, page, text, section, 
                type, cited_text, rects, highlight_id
            )
            SELECT 
                id, 
                document_id, 
                page, 
                text, 
                section,
                'page_location' as type,
                text as cited_text,
                CASE 
                    WHEN bounding_box IS NOT NULL THEN 
                        json_array(json(bounding_box))
                    ELSE 
                        '[]'
                END as rects,
                id as highlight_id
            FROM citations;
            """
            
            await conn.execute(text(migrate_data_sql))
            logger.info("Migrated existing citation data")
            
            # Drop old table and rename new one
            await conn.execute(text("DROP TABLE citations;"))
            await conn.execute(text("ALTER TABLE citations_new RENAME TO citations;"))
            logger.info("Replaced old table with new schema")
            
            # Create indexes
            indexes = [
                "CREATE INDEX idx_citations_document_id ON citations(document_id);",
                "CREATE INDEX idx_citations_type ON citations(type);",
                "CREATE INDEX idx_citations_highlight_id ON citations(highlight_id);",
                "CREATE INDEX idx_citations_page ON citations(page);"
            ]
            
            for idx_sql in indexes:
                await conn.execute(text(idx_sql))
                logger.info(f"Created index: {idx_sql.split(' ')[2]}")
            
            await conn.commit()
            logger.info("Citation migration completed successfully!")
        
        # Verify migration in a new connection
        async with engine.begin() as conn:
            verify_sql = "SELECT COUNT(*) as count FROM citations;"
            result = await conn.execute(text(verify_sql))
            count = result.scalar()
            logger.info(f"Migrated {count} citations")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        logger.error("Rolling back changes...")
        try:
            async with engine.begin() as conn:
                await conn.execute(text("DROP TABLE IF EXISTS citations_new;"))
        except:
            pass
        sys.exit(1)
    finally:
        if 'engine' in locals():
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_citations_anthropic())