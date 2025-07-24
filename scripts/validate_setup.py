#!/usr/bin/env python3
"""Validate the complete setup"""

import asyncio
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import get_settings
from app.config.database import engine
from app.config.redis import init_redis_pool
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def validate_setup():
    """Validate the complete setup"""
    logger.info("🔍 Validating AI Services setup...")
    
    success = True
    
    # Validate settings
    try:
        settings = get_settings()
        logger.info("✅ Settings loaded successfully")
        logger.info(f"   Environment: {settings.ENVIRONMENT}")
        logger.info(f"   Database: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}")
        logger.info(f"   Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    except Exception as e:
        logger.error(f"❌ Settings validation failed: {str(e)}")
        success = False
    
    # Validate database
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT VERSION()"))
            version = result.scalar()
            logger.info(f"✅ Database connected successfully (MySQL {version})")
    except Exception as e:
        logger.error(f"❌ Database validation failed: {str(e)}")
        success = False
    
    # Validate Redis
    try:
        await init_redis_pool()
        logger.info("✅ Redis connected successfully")
    except Exception as e:
        logger.error(f"❌ Redis validation failed: {str(e)}")
        success = False
    
    # Validate AI models
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        test_embedding = model.encode(["Test sentence"])
        logger.info(f"✅ Sentence transformer loaded (embedding dim: {test_embedding.shape[1]})")
    except Exception as e:
        logger.error(f"❌ AI model validation failed: {str(e)}")
        success = False
    
    # Validate spaCy
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp("Test sentence")
        logger.info(f"✅ spaCy model loaded ({len(doc)} tokens processed)")
    except Exception as e:
        logger.error(f"❌ spaCy validation failed: {str(e)}")
        success = False
    
    # Clean up
    await engine.dispose()
    
    if success:
        logger.info("🎉 All validations passed! AI Services ready to run.")
        return True
    else:
        logger.error("💥 Some validations failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(validate_setup())
    sys.exit(0 if success else 1)