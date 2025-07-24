#!/usr/bin/env python3
"""Download required AI models"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_models():
    """Download required AI models"""
    settings = get_settings()
    
    try:
        logger.info("📥 Downloading AI models...")
        
        # Create models directory
        models_dir = Path(settings.MODEL_CACHE_DIR)
        models_dir.mkdir(exist_ok=True)
        
        # Download sentence transformer model
        logger.info(f"📥 Downloading sentence transformer: {settings.EMBEDDING_MODEL}")
        from sentence_transformers import SentenceTransformer
        
        model = SentenceTransformer(settings.EMBEDDING_MODEL)
        model.save(str(models_dir / "sentence_transformer"))
        
        # Download spaCy model if not already downloaded
        logger.info("📥 Downloading spaCy model...")
        import spacy
        
        try:
            spacy.load("en_core_web_sm")
            logger.info("✅ spaCy model already available")
        except OSError:
            logger.info("📥 Downloading spaCy en_core_web_sm...")
            os.system("python -m spacy download en_core_web_sm")
        
        logger.info("✅ All models downloaded successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to download models: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    download_models()