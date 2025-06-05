#!/usr/bin/env python3
"""
Database Creation Script
========================

This script is responsible for initializing the database schema for the CFIN financial
analysis platform. It creates all necessary tables based on the SQLAlchemy ORM models
defined in `models.database_models.py` and can also populate initial data, such as a default user.

It supports both asynchronous (for databases like PostgreSQL) and synchronous (for SQLite)
initialization routines.

Primary responsibilities:
- Create all database tables defined by the ORM models.
- Optionally drop existing tables before creation for a clean setup.
- Create a default user if one does not already exist.
- Select the appropriate database engine (async or sync) based on the DATABASE_URL.

Key Components:
- create_database(): Asynchronous function to initialize the database using an async engine.
- create_database_sync(): Synchronous function to initialize the database using a sync engine (primarily for SQLite).
- Main execution block (`if __name__ == "__main__"`): Determines which initialization function to call based on the DATABASE_URL.

Interactions with other files:
-----------------------------
1. cfin/backend/models/database_models.py:
   - Imports all SQLAlchemy ORM models (User, Document, Citation, Conversation, Message, AnalysisResult, AnalysisBlock, etc.) and the `Base` metadata object.
   - Uses `Base.metadata.create_all()` and `Base.metadata.drop_all()` to manage the schema.

2. cfin/backend/utils/database.py:
   - Imports `get_db`, `SyncSessionLocal`, and `sync_engine` for database session and engine management.
   - Uses the DATABASE_URL environment variable, which is also configured/used by `utils.database.py`.

Usage:
- This script is typically run once during application setup or when the database schema needs to be reset or updated.
- It ensures that the database is correctly structured for the application to function.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import os

from models.database_models import Base
from utils.database import SyncSessionLocal, sync_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fdas.db")

async def create_database():
    """Create the database tables."""
    try:
        # Create tables
        from models.database_models import (
            User, Document, Citation, MessageCitation, 
            Conversation, ConversationDocument, Message,
            AnalysisResult, AnalysisBlock
        )
        
        # Explicitly import Message for content_blocks column
        logger.info("Ensuring Message model includes content_blocks column")
        
        # Create tables
        async with create_async_engine(
            DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1) if DATABASE_URL.startswith("sqlite") else DATABASE_URL, 
            echo=True
        ) as engine:
            async with engine.begin() as conn:
                logger.info("Creating database tables...")
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database tables created successfully.")
            
            # Create default user
            async with AsyncSession(engine) as session:
                # Check if default user exists
                result = await session.execute(text("SELECT id FROM users WHERE username = 'default'"))
                user = result.scalar_one_or_none()
                
                if not user:
                    # Create default user
                    logger.info("Creating default user...")
                    await session.execute(
                        text("""
                            INSERT INTO users (id, username, email, hashed_password, is_active, created_at)
                            VALUES ('default-user', 'default', 'default@example.com', 'not-a-real-password', 1, CURRENT_TIMESTAMP)
                        """)
                    )
                    await session.commit()
                    logger.info("Default user created successfully.")
                else:
                    logger.info("Default user already exists.")
            
            logger.info("Database initialization completed successfully.")
        
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}", exc_info=True)
        raise

def create_database_sync():
    """Create the database tables synchronously."""
    try:
        # Create tables
        from models.database_models import (
            User, Document, Citation, MessageCitation, 
            Conversation, ConversationDocument, Message,
            AnalysisResult, AnalysisBlock
        )
        
        # Explicitly import Message for content_blocks column
        logger.info("Ensuring Message model includes content_blocks column")
        
        # Create tables using sync engine
        logger.info("Creating database tables synchronously...")
        Base.metadata.drop_all(sync_engine)
        Base.metadata.create_all(sync_engine)
        
        logger.info("Database tables created successfully.")
        
        # Create default user
        with SyncSessionLocal() as session:
            # Check if default user exists
            user = session.execute(text("SELECT id FROM users WHERE username = 'default'")).scalar_one_or_none()
            
            if not user:
                # Create default user
                logger.info("Creating default user...")
                session.execute(
                    text("""
                        INSERT INTO users (id, username, email, hashed_password, is_active, created_at)
                        VALUES ('default-user', 'default', 'default@example.com', 'not-a-real-password', 1, CURRENT_TIMESTAMP)
                    """)
                )
                session.commit()
                logger.info("Default user created successfully.")
            else:
                logger.info("Default user already exists.")
        
        logger.info("Database initialization completed successfully.")
        
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    logger.info("Initializing database...")
    
    # Run the database creation
    if DATABASE_URL.startswith("sqlite"):
        # SQLite - use synchronous version for simplicity
        create_database_sync()
    else:
        # PostgreSQL or other async-compatible DB - use async version
        asyncio.run(create_database())