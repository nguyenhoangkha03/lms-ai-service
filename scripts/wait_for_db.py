#!/usr/bin/env python3
"""Wait for database to be ready"""

import asyncio
import sys
import time
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.database import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def wait_for_database(max_retries: int = 30, delay: int = 2):
    """Wait for database to be ready"""
    retries = 0
    
    while retries < max_retries:
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.info("✅ Database is ready!")
            return True
            
        except Exception as e:
            retries += 1
            logger.warning(f"Database not ready (attempt {retries}/{max_retries}): {str(e)}")
            
            if retries >= max_retries:
                logger.error("❌ Database connection timeout")
                return False
                
            await asyncio.sleep(delay)
    
    return False

async def main():
    """Main function"""
    success = await wait_for_database()
    
    if not success:
        sys.exit(1)
    
    # Close engine
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())