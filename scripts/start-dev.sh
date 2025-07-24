#!/bin/bash

# Development start script
set -e

echo "🚀 Starting LMS AI Services (Development)..."

# Install development dependencies
echo "📦 Installing dependencies..."
pip install -r requirements/development.txt

# Wait for database
echo "⏳ Waiting for database..."
python scripts/wait_for_db.py

# Run database migrations
echo "📊 Running database migrations..."
python scripts/migrate.py

# Start with hot reload
echo "🔥 Starting development server with hot reload..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
