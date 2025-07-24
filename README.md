# LMS AI Services

AI-powered backend services for Learning Management System built with FastAPI, integrating with NestJS main backend.

## 🚀 Features

-   **Learning Analytics**: Real-time analysis of student behavior and performance
-   **AI Recommendations**: Personalized learning path and content suggestions
-   **Auto Assessment**: Automated grading for multiple choice and essay questions
-   **Chatbot 24/7**: Intelligent tutoring and support system
-   **Predictive Analytics**: Dropout risk prediction and intervention recommendations
-   **Content Analysis**: Quality assessment and plagiarism detection

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Next.js       │────│   NestJS API     │────│   Python AI     │
│   Frontend      │    │   Gateway        │    │   Services      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                         │
                       ┌────────┴────────┐               │
                       │                 │               │
                  ┌────▼────┐      ┌────▼────┐    ┌────▼────┐
                  │  MySQL  │      │  Redis  │    │ Vector  │
                  │Database │      │ Cache   │    │   DB    │
                  └─────────┘      └─────────┘    └─────────┘
```

## 🛠️ Tech Stack

-   **Framework**: FastAPI 0.104+
-   **Database**: MySQL with SQLAlchemy
-   **Cache**: Redis
-   **ML/AI**: scikit-learn, PyTorch, Transformers
-   **NLP**: spaCy, NLTK, sentence-transformers
-   **Background Tasks**: Celery
-   **Deployment**: Docker, Docker Compose

## 📋 Prerequisites

-   Python 3.11+
-   MySQL 8.0+
-   Redis 7.0+
-   Docker & Docker Compose (for containerized setup)

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository

```bash
git clone <repository-url>
cd ai-services
```

2. Copy environment file

```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start services

```bash
make docker-up
```

4. The API will be available at `http://localhost:8001`

### Manual Setup

1. Install dependencies

```bash
make install-dev
```

2. Setup database and download models

```bash
make setup
```

3. Start the development server

```bash
make run-dev
```

## 📚 API Documentation

-   **Swagger UI**: `http://localhost:8001/docs` (development only)
-   **ReDoc**: `http://localhost:8001/redoc` (development only)
-   **Health Check**: `http://localhost:8001/health`

## 🧪 Testing

Run tests with coverage:

```bash
make test-cov
```

## 📦 Development

### Code Quality

```bash
# Format code
make format

# Run linting
make lint

# Run tests
make test
```

### Environment Variables

Key environment variables (see `.env.example` for full list):

```bash
ENVIRONMENT=development
SECRET_KEY=your-secret-key
MYSQL_HOST=localhost
REDIS_HOST=localhost
NESTJS_API_URL=http://localhost:3000
OPENAI_API_KEY=your-openai-key
```

## 🚀 Deployment

### Production with Docker

1. Create production environment file:

```bash
cp .env.example .env.production
# Configure production values
```

2. Deploy with production compose:

```bash
docker-compose -f docker/docker-compose.prod.yml up -d
```

### Kubernetes

Kubernetes manifests available in the `k8s/` directory.

## 📊 Monitoring

-   **Health Checks**: `/health`, `/health/detailed`
-   **Metrics**: Prometheus metrics available
-   **Logging**: Structured logging with request tracing

## 🤝 Integration with NestJS

The AI services integrate with the main NestJS backend through:

-   **Authentication**: JWT token validation via NestJS API
-   **Data Sync**: Real-time events for learning activities
-   **APIs**: RESTful APIs for AI predictions and recommendations

## 📝 Project Structure

```
ai-services/
├── app/
│   ├── api/v1/              # API endpoints
│   ├── config/              # Configuration
│   ├── core/                # Core utilities
│   ├── models/              # Database models & schemas
│   ├── services/            # Business logic services
│   ├── tasks/               # Background tasks
│   └── tests/               # Test suite
├── docker/                  # Docker configuration
├── requirements/            # Python dependencies
└── scripts/                 # Utility scripts
```

## 🔄 Background Tasks

Celery workers handle:

-   ML model training and inference
-   Analytics data processing
-   Notification delivery
-   Content analysis jobs

Start workers:

```bash
celery -A app.tasks.background worker --loglevel=info
```

## 📈 Performance

-   **Response Time**: < 200ms for most endpoints
-   **Throughput**: 1000+ requests/second
-   **Scalability**: Horizontal scaling with multiple workers
-   **Caching**: Redis caching for ML predictions

## 🛡️ Security

-   JWT authentication with NestJS backend
-   Input validation with Pydantic
-   SQL injection prevention with SQLAlchemy
-   Rate limiting and CORS protection
-   Secure headers and HTTPS support

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**

    ```bash
    # Check MySQL is running and accessible
    python scripts/wait_for_db.py
    ```

2. **Redis Connection Failed**

    ```bash
    # Verify Redis configuration
    redis-cli ping
    ```

3. **Model Loading Errors**
    ```bash
    # Re-download models
    make download-models
    ```

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For support and questions:

-   GitHub Issues: Create an issue
-   Documentation: See `/docs` directory
-   API Docs: Visit `/docs` endpoint
