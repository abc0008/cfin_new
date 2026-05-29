import asyncio
import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from .database import engine, Base, SessionLocal

logger = logging.getLogger(__name__)

async def create_tables():
    """Create database tables."""
    # Ensure all SQLAlchemy model classes are registered with Base.metadata.
    import models.database_models  # noqa: F401

    try:
        async with engine.begin() as conn:
            logger.info("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise

async def create_default_user():
    """Create a default user if no users exist."""
    # Import here to avoid circular imports
    from models.database_models import User
    
    try:
        async with SessionLocal() as session:
            # API routes currently use this stable ID when auth is not present.
            result = await session.execute(select(User).where(User.id == "default-user"))
            existing_user = result.scalars().first()
            
            if not existing_user:
                logger.info("Creating default API user...")
                default_user = User(
                    id="default-user",
                    username="default-user",
                    email="default-user@example.com",
                    hashed_password="notarealpassword",  # In a real app, this would be properly hashed
                    is_active=True
                )
                session.add(default_user)
                try:
                    await session.commit()
                    logger.info(f"Default API user created with ID: {default_user.id}")
                    return default_user
                except IntegrityError:
                    await session.rollback()
                    result = await session.execute(select(User).where(User.id == "default-user"))
                    existing_user = result.scalars().first()
                    if existing_user:
                        return existing_user
                    raise
            
            logger.info("Default API user already exists.")
            return existing_user
    except Exception as e:
        logger.error(f"Error creating default user: {str(e)}")
        raise

async def init_db():
    """Initialize the database."""
    try:
        await create_tables()
        await create_default_user()
        logger.info("Database initialization completed successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

def run_init_db():
    """Run the database initialization."""
    asyncio.run(init_db())

if __name__ == "__main__":
    run_init_db()
