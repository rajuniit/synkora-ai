# Synkora API


Production-ready API backend for the Synkora AI application platform.


<!-- CI/CD Badges -->
[![API Tests](https://github.com/getsynkora/synkora-ai/actions/workflows/api-tests.yml/badge.svg)](https://github.com/getsynkora/synkora-ai/actions/workflows/api-tests.yml)
[![codecov](https://codecov.io/gh/getsynkora/synkora-ai/branch/main/graph/badge.svg?flag=api)](https://codecov.io/gh/getsynkora/synkora-ai)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)


## Features


- **Multi-tenant Architecture**: Complete tenant isolation with role-based access control
- **Modern Python Stack**: Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2
- **Type Safety**: Full type hints with Pyright/Basedpyright validation
- **Database Migrations**: Alembic for version-controlled schema changes
- **Comprehensive Testing**: Unit and integration tests with pytest + 44% code coverage
- **Production Ready**: Docker support, monitoring, logging, and error handling


## Project Structure


```
api/
├── src/                    # Source code
│   ├── config/            # Configuration management
│   ├── core/              # Core functionality (database, cache, etc.)
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   ├── api/               # API routes
│   └── utils/             # Utility functions
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── migrations/            # Alembic migrations
├── pyproject.toml        # Project dependencies
└── .env.example          # Environment variables template
```


## Prerequisites


- Python 3.12 or higher
- PostgreSQL 14+
- Redis 7+
- uv (recommended) or pip for package management


## Quick Start


### 1. Install Dependencies


Using uv (recommended):
```bash
cd api
uv sync
```


Using pip:
```bash
cd api
pip install -e .
```


### 2. Set Up Environment


```bash
cp .env.example .env
# Edit .env with your configuration
```


Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Application secret key
- `JWT_SECRET_KEY`: JWT signing key


### 3. Initialize Database


```bash
# Create database tables
alembic upgrade head


# Seed system roles and permissions
python -m src.services.permissions.seed_roles_permissions


# Create super admin user (interactive)
python create_super_admin.py


# Seed platform configuration (interactive)
python seed_platform_config.py
```


### 4. Run Development Server


```bash
# Using uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 5001


# Or using the development script
python -m src.main
```


The API will be available at `http://localhost:5001`


## Initial Setup & Seeding


### Creating a Super Admin


After setting up the database, you need to create a super admin user with Platform Owner role:


```bash
# Interactive mode (recommended for first-time setup)
python create_super_admin.py


# You'll be prompted for:
# - Email address
# - Password (min 8 characters)
# - Full name
# - Tenant/organization name
```


This script will:
1. Seed system roles and permissions (if not already done)
2. Create a tenant for the super admin
3. Create the account with Platform Owner role
4. Provide login credentials


**Important:** Save the credentials securely - this is your platform administrator account.


### Seeding Platform Configuration


Configure platform-wide default settings for SMTP, Stripe, and other services:


```bash
# Interactive mode
python seed_platform_config.py


# Non-interactive mode (using environment variables)
python seed_platform_config.py --non-interactive


# Update existing configuration
python seed_platform_config.py --update
```


**Configuration Options:**


1. **Platform Branding**
  - Platform name
  - Logo URL
  - Support email
  - Application base URL


2. **SMTP Configuration** (for email notifications)
  - SMTP host (e.g., smtp.gmail.com)
  - SMTP port (default: 587)
  - SMTP username
  - SMTP password
  - From email address
  - From name


3. **Stripe Configuration** (for billing)
  - Stripe secret key
  - Stripe publishable key
  - Stripe webhook secret


4. **Storage Configuration**
  - Storage provider (default: s3)
  - Storage configuration


**Environment Variables (for non-interactive mode):**


```bash
# Platform settings
export PLATFORM_NAME="synkora"
export PLATFORM_LOGO_URL="https://example.com/logo.png"
export SUPPORT_EMAIL="support@example.com"
export APP_BASE_URL="https://app.example.com"


# SMTP settings
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="your-email@gmail.com"
export SMTP_PASSWORD="your-password"
export SMTP_FROM_EMAIL="noreply@example.com"
export SMTP_FROM_NAME="Synkora"


# Stripe settings
export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_PUBLISHABLE_KEY="pk_test_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."


# Storage settings
export STORAGE_PROVIDER="s3"
```


### Promoting Existing Users


To promote an existing user to Platform Owner:


```bash
python promote_to_platform_owner.py user@example.com
```


**Note:** The user must already exist and system roles must be seeded first.


### Complete Initial Setup Workflow


For a fresh installation, follow this order:


```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your configuration


# 2. Initialize database
alembic upgrade head


# 3. Create super admin (includes role seeding)
python create_super_admin.py


# 4. Configure platform defaults
python seed_platform_config.py


# 5. Start the application
uvicorn src.main:app --reload --host 0.0.0.0 --port 5001
```


## Development


### Running Tests


Tests are run automatically on every push and pull request via GitHub Actions.


```bash
# Run all tests
pytest


# Run with coverage
pytest --cov=src --cov-report=html --cov-report=xml


# Run unit tests only
pytest tests/unit/ -v


# Run integration tests only
pytest tests/integration/ -v


# Run specific test file
pytest tests/unit/test_models.py


# Run specific test by name
pytest -v -k "test_chat_stream"


# Run with verbose output and stop on first failure
pytest -v -x


# Run with coverage and generate reports
pytest --cov=src --cov-report=term --cov-report=html --cov-report=xml
```


### Test Structure


```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_models.py
│   ├── test_services.py
│   └── ...
└── integration/             # Integration tests (require database/services)
   ├── test_api.py
   ├── agents/
   │   ├── test_chat_integration.py
   │   ├── test_conversations_integration.py
   │   └── test_llm_configs_integration.py
   └── ...
```


### Test Markers


```bash
# Run only unit tests
pytest -m unit


# Run only integration tests
pytest -m integration


# Run slow tests
pytest -m slow
```


### Database Migrations


```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"


# Apply migrations
alembic upgrade head


# Rollback one migration
alembic downgrade -1


# View migration history
alembic history
```


### Code Quality


```bash
# Format code
ruff format .


# Lint code
ruff check .


# Type checking
basedpyright


# Run all checks
ruff format . && ruff check . && basedpyright
```


### Adding Dependencies


Using uv:
```bash
# Add production dependency
uv add package-name


# Add development dependency
uv add --dev package-name
```


Using pip:
```bash
# Edit pyproject.toml, then:
pip install -e .
```


## Configuration


Configuration is managed through environment variables and the `src/config/settings.py` module.


Key configuration areas:
- **Application**: Environment, debug mode, host/port
- **Database**: Connection pooling, timeouts
- **Redis**: Connection settings
- **JWT**: Token expiration, algorithm
- **CORS**: Allowed origins
- **Rate Limiting**: Request limits
- **File Upload**: Size limits, allowed extensions


See `.env.example` for all available options.


## API Documentation


Once the server is running, interactive API documentation is available at:
- Swagger UI: `http://localhost:5001/docs`
- ReDoc: `http://localhost:5001/redoc`
- OpenAPI JSON: `http://localhost:5001/openapi.json`


## Database Models


### Core Models


- **Tenant**: Organization/workspace for multi-tenancy
- **Account**: User accounts with authentication
- **TenantAccountJoin**: Many-to-many relationship with roles


### Model Features


- UUID primary keys
- Automatic timestamps (created_at, updated_at)
- Soft delete support
- Status tracking
- Utility methods (to_dict, update_from_dict)


## Testing


The test suite includes:


### Unit Tests
- Model validation and methods
- Business logic
- Utility functions


### Integration Tests
- Database operations
- API endpoints
- External service integrations


### Test Fixtures
- Database session management
- Test data factories
- Mock services


## Deployment


### Docker


```bash
# Build image
docker build -t synkora-api .


# Run container
docker run -p 5001:5001 --env-file .env synkora-api
```


### Docker Compose


```bash
# Start all services
docker-compose up -d


# View logs
docker-compose logs -f api


# Stop services
docker-compose down
```


### Production Checklist


- [ ] Set `APP_ENV=production`
- [ ] Use strong `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Configure database connection pooling
- [ ] Set up Redis for caching and Celery
- [ ] Enable rate limiting
- [ ] Configure CORS origins
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Configure logging
- [ ] Set up SSL/TLS
- [ ] Configure backup strategy
- [ ] Set up CI/CD pipeline


## Monitoring


### Health Checks


```bash
# API health
curl http://localhost:5001/health


# Database health
curl http://localhost:5001/health/db
```


### Logging


Logs are output in JSON format (configurable) and include:
- Request/response details
- Error traces
- Performance metrics
- Database queries (in debug mode)


### Metrics


Integration with monitoring services:
- Sentry for error tracking
- Prometheus for metrics
- Custom application metrics


## Troubleshooting


### Common Issues


**Database connection errors**
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Ensure database exists


**Migration errors**
- Check for conflicting migrations
- Verify database schema matches models
- Review migration history with `alembic history`


**Import errors**
- Ensure virtual environment is activated
- Run `uv sync` or `pip install -e .`
- Check Python version (3.12+ required)


**Test failures**
- Ensure test database is configured
- Check test fixtures in conftest.py
- Run tests with `-v` for verbose output


## Contributing


1. Create a feature branch
2. Make your changes
3. Add/update tests
4. Run code quality checks
5. Submit a pull request


## License


See LICENSE file for details.


## Support


For issues and questions:
- GitHub Issues: [Project Issues](https://github.com/getsynkora/synkora-ai/issues)
- Documentation: [Full Documentation](https://docs.synkora.ai)



