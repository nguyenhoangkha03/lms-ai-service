#!/usr/bin/env python3
"""Database migration script"""

import asyncio
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.database import create_tables, engine
from app.config.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_migrations():
    """Run database migrations"""
    try:
        logger.info("🔄 Starting database migration...")
        
        # Create tables
        await create_tables()
        
        logger.info("✅ Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        sys.exit(1)
    finally:
        # Close engine
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migrations())
