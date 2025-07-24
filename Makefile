.PHONY: help install install-dev run run-dev test lint format clean docker-build docker-up docker-down logs

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $1, $2}'

install:  ## Install production dependencies
	pip install -r requirements/production.txt

install-dev:  ## Install development dependencies
	pip install -r requirements/development.txt
	pre-commit install

run:  ## Run the application in production mode
	uvicorn app.main:app --host 0.0.0.0 --port 8001

run-dev:  ## Run the application in development mode with hot reload
	uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

test:  ## Run tests
	pytest -v

test-cov:  ## Run tests with coverage
	pytest --cov=app --cov-report=html --cov-report=term

lint:  ## Run linting
	flake8 app/
	mypy app/

format:  ## Format code
	black app/
	isort app/

clean:  ## Clean cache and temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .pytest_cache/
	rm -rf htmlcov/

docker-build:  ## Build Docker image
	docker build -t lms-ai-services -f docker/Dockerfile .

docker-up:  ## Start services with Docker Compose
	docker-compose -f docker/docker-compose.yml up -d

docker-down:  ## Stop services with Docker Compose
	docker-compose -f docker/docker-compose.yml down

docker-logs:  ## View Docker logs
	docker-compose -f docker/docker-compose.yml logs -f

migrate:  ## Run database migrations
	python scripts/migrate.py

download-models:  ## Download required AI models
	python scripts/download_models.py

setup:  ## Initial setup for development
	make install-dev
	make download-models
	make migrate