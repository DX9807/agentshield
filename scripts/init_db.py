"""Initialize the database with tables."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentshield.infrastructure.database.session import db_manager
from agentshield.infrastructure.database.base import Base
from agentshield.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def init_database():
    """Initialize database tables."""
    logger.info("Initializing database...")
    try:
        await db_manager.create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(init_database())