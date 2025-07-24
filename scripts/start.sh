#!/bin/bash

# Start script for production
set -e

echo "🚀 Starting LMS AI Services..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
python scripts/wait_for_db.py

# Run database migrations
echo "📊 Running database migrations..."
python scripts/migrate.py

# Download required models
echo "🤖 Downloading AI models..."
python scripts/download_models.py

# Start the application
echo "🔥 Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
