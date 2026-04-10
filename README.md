<div align="center">

# Synkora

<!-- CI/CD Badges -->
[![CI Pipeline](https://github.com/getsynkora/synkora-ai/actions/workflows/main-ci.yml/badge.svg)](https://github.com/getsynkora/synkora-ai/actions/workflows/main-ci.yml)
[![API Tests](https://github.com/getsynkora/synkora-ai/actions/workflows/api-tests.yml/badge.svg)](https://github.com/getsynkora/synkora-ai/actions/workflows/api-tests.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/rajuniit/6adfe45792942ae62d18c5e89128498b/raw/coverage-badge.json)](https://github.com/getsynkora/synkora-ai/actions/workflows/api-tests.yml)

<!-- Tech Stack Badges -->
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-15.1-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)

<!-- Project Badges -->
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Code of Conduct](https://img.shields.io/badge/code%20of-conduct-ff69b4.svg)](CODE_OF_CONDUCT.md)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/getsynkora/synkora-ai/graphs/commit-activity)

**Build AI agents for every role in your company. From product management to engineering to marketing — deploy intelligent AI teammates that handle real work, not just chat. Open-source, use your own LLM keys, full control.**

[Features](#key-features) •
[Quick Start](#quick-start) •
[Documentation](#documentation) •
[Contributing](#contributing) •
[Community](#support--community)

</div>

---

## Overview

Synkora is an open-source platform for building AI-powered teammates. Create agents that act as your AI Product Manager, AI Software Engineer, AI Marketing Lead, AI Support Agent, and more. Each agent can be equipped with custom tools, knowledge bases, and integrations to handle real work autonomously.

**Why Synkora?**
- **Role-based AI agents** - Pre-built templates for PM, Engineering, Marketing, Support, and more
- **Your LLM keys** - Use OpenAI, Anthropic, Google, or any provider via LiteLLM. No vendor lock-in
- **Real work, not just chat** - Agents integrate with Jira, GitHub, Slack, HubSpot, and 50+ tools
- **Open source** - Self-host on your infrastructure or use our cloud. You own your data


## See It In Action

<table>
  <tr>
    <td align="center" width="50%">
      <strong>RajuClaw — Personal AI Assistant</strong><br><br>
      <video src="https://github.com/user-attachments/assets/ce64d4bc-c47e-48f6-af2d-9287d6b3b836" controls width="100%">
        Your browser does not support the video tag.
      </video>
      <br><em>A personal AI assistant that can do everything — browsing, coding, scheduling, and more.</em>
    </td>
    <td align="center" width="50%">
      <strong>Platform Engineer & Agents</strong><br><br>
      <video src="https://github.com/user-attachments/assets/c27ebb0c-1742-4897-9f7f-eaa112d66470" controls width="100%">
        Your browser does not support the video tag.
      </video>
      <br><em>Managing agents and platform operations with the Platform Engineer Agent.</em>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <strong>Daily AI News Reporter — Setup</strong><br><br>
      <video src="https://github.com/user-attachments/assets/a590dc34-3744-4359-9254-357e0d95d5ee" controls width="100%">
        Your browser does not support the video tag.
      </video>
      <br><em>Setting up a Daily AI News Reporter agent from the chat interface.</em>
    </td>
    <td align="center" width="50%">
      <strong>Daily AI News Reporter — Email Newsletter Demo</strong><br><br>
      <video src="https://github.com/user-attachments/assets/4001f0a0-f82d-453e-9b0c-f6e16afd514d" controls width="100%">
        Your browser does not support the video tag.
      </video>
      <br><em>Watch the Daily AI News Reporter automatically send a personalized AI news email digest.</em>
    </td>
  </tr>
</table>


## Key Features

### AI Teammates for Every Role
- **AI Product Manager** - Backlog prioritization, sprint planning, status reports (Jira, Linear, Notion)
- **AI Software Engineer** - Code review, bug triage, documentation generation (GitHub, GitLab, Sentry)
- **AI Marketing Lead** - Content creation, SEO optimization, campaign analysis (HubSpot, Analytics)
- **AI Support Agent** - Ticket handling, knowledge base Q&A, smart escalation (Zendesk, Intercom)
- **AI Data Analyst** - Natural language queries, automated reports, anomaly detection (SQL, BigQuery)
- **AI HR Coordinator** - Onboarding automation, policy Q&A, leave management (BambooHR, Gusto)

### Core Capabilities
- **Multi-Provider LLM Support**: OpenAI, Anthropic, Google, and more via LiteLLM — use your own keys
- **Knowledge Bases**: Vector-based knowledge management with Qdrant, Pinecone, and Elasticsearch
- **Custom Tools**: 50+ pre-built integrations plus extensible tool system
- **Real-time Chat**: WebSocket-based chat interface with streaming responses
- **MCP Servers**: Model Context Protocol server integration
- **Voice Services**: ElevenLabs integration for voice interactions

### Enterprise Features
- **Multi-Tenant Architecture**: Complete tenant isolation with role-based access control
- **Billing & Subscriptions**: Stripe integration with plan-based resource limits
- **SSO & Authentication**: Okta SSO, SAML, and social authentication
- **Messaging Bots**: Slack, Microsoft Teams, and WhatsApp bot integrations
- **Data Sources**: Connect to databases, APIs, and external services
- **Widgets**: Embeddable chat widgets for websites
- **Observability**: Langfuse integration for LLM observability and analytics

### Developer Experience
- **RESTful API**: Comprehensive FastAPI-based API with OpenAPI documentation
- **Agent API Keys**: Per-agent API keys for secure access
- **Custom Domains**: Configure custom domains for agents
- **Activity Logs**: Comprehensive audit trail
- **Usage Statistics**: Track usage and performance metrics


## Architecture

> For a comprehensive technical analysis, see [ARCHITECTURE.md](ARCHITECTURE.md)

### System Architecture

```
                    ┌─────────────────────────────────────────┐
                    │              Load Balancer                │
                    └────────────────┬────────────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
    ┌─────────▼─────────┐ ┌─────────▼─────────┐ ┌─────────▼─────────┐
    │   FastAPI Pod 1    │ │   FastAPI Pod 2    │ │   FastAPI Pod N    │
    │  (API + WebSocket) │ │  (API + WebSocket) │ │  (API + WebSocket) │
    └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
              │                      │                      │
    ┌─────────▼──────────────────────▼──────────────────────▼─────────┐
    │                        Redis (Pub/Sub + Cache)                   │
    └─────────┬──────────────────────┬──────────────────────┬─────────┘
              │                      │                      │
    ┌─────────▼─────────┐ ┌─────────▼─────────┐ ┌─────────▼─────────┐
    │  Celery Workers    │ │  Celery Beat       │ │  Bot Workers       │
    │  (default+billing) │ │  (scheduler)       │ │  (Slack/Telegram)  │
    └─────────┬─────────┘ └───────────────────┘ └─────────┬─────────┘
              │                                            │
    ┌─────────▼──────────────────────────────────────────-▼─────────┐
    │  synkora-ml (embeddings + reranking)                           │
    │  synkora-scraper (browser automation + app-store scraping)     │
    └────────────────────────────────────────────────────────────────┘
              │
    ┌─────────▼──────────────────────────────────────────────────────┐
    │                                                                 │
    │  PostgreSQL (pgvector)  │  Qdrant  │  MinIO/S3  │  Elasticsearch│
    └─────────────────────────────────────────────────────────────────┘
```

### Architecture Scorecard

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Code Quality** | A | Clean, consistent, well-documented |
| **Modularity** | A | Domain-separated layers, composable mixins, declarative routing |
| **Design Patterns** | A | Circuit breaker, DLQ, pub/sub, factory, strategy, middleware chain |
| **Security** | A+ | Defense-in-depth: CSRF, CSP, rate limiting, input sanitization, encryption at rest |
| **Database Performance** | A | Async + sync engines, pool tuning, lazy loading, statement timeouts |
| **Horizontal Scaling** | A | Stateless API, distributed WebSocket, distributed cache, queue separation |
| **Availability** | A | K8s probes, circuit breakers, graceful shutdown, dead-letter queue |
| **Load Testing** | A | k6 suite with mock LLM mode, CI integration, comprehensive scenarios |

### Tech Stack

**Backend:**
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 14+ with pgvector extension
- **Cache**: Redis 7+
- **Vector DB**: Qdrant, Pinecone, Elasticsearch
- **Task Queue**: Celery with Redis broker
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Validation**: Pydantic v2

**Frontend:**
- **Framework**: Next.js 15.1 with App Router
- **UI**: React 19, Tailwind CSS
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Forms**: React Hook Form with Zod validation

**Infrastructure:**
- **Containerization**: Docker & Docker Compose
- **Orchestration**: Kubernetes (Helm charts included)
- **Storage**: MinIO (S3-compatible) or AWS S3
- **Observability**: Langfuse for LLM tracking


## Project Structure

```
synkora/
├── api/                    # Backend API (FastAPI)
│   ├── src/
│   │   ├── config/        # Configuration management
│   │   ├── core/          # Core functionality (database, cache, websocket)
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── controllers/   # API route handlers
│   │   ├── services/      # Business logic
│   │   ├── middleware/    # Custom middleware
│   │   └── tasks/         # Celery tasks
│   ├── migrations/        # Alembic database migrations
│   ├── tests/             # Test suite
│   └── pyproject.toml     # Python dependencies
│
├── web/                    # Frontend (Next.js)
│   ├── app/               # Next.js App Router pages
│   ├── components/        # React components
│   ├── lib/               # Utilities and API client
│   ├── hooks/             # Custom React hooks
│   └── types/             # TypeScript type definitions
│
├── services/
│   ├── ml/                # ML microservice (embeddings + reranking)
│   └── scraper/           # Scraper microservice (browser + app-store)
│
├── docker-compose.yml      # Local development environment
├── helm/                   # Kubernetes Helm charts
└── docs/                   # Documentation
```


## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ and pnpm (for local frontend development)
- Python 3.11+ and uv (for local backend development)

### Using Docker Compose (Recommended)

1. **Clone the repository**
  ```bash
  git clone https://github.com/getsynkora/synkora-ai.git
  cd synkora-ai
  ```

2. **Start all services**
  ```bash
  docker-compose up -d
  ```

  This starts:
  - PostgreSQL (port 5432)
  - Redis (port 6379)
  - Qdrant (ports 6333, 6334)
  - Elasticsearch (port 9200)
  - MinIO (ports 9000, 9001)
  - Langfuse (port 3001)
  - API (port 5001)
  - Web frontend (port 3005)
  - ML service (internal, port 5002)
  - Scraper service (internal, port 5003)

3. **Initialize the database**
  ```bash
  # Run migrations
  docker-compose exec api alembic upgrade head

  # Create super admin
  docker-compose exec api python create_super_admin.py

  # Seed platform configuration
  docker-compose exec api python seed_platform_config.py
  ```

4. **Access the application**
  - Frontend: http://localhost:3005
  - API Docs: http://localhost:5001/api/v1/docs
  - Langfuse: http://localhost:3001
  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

### Local Development

#### Backend Setup

```bash
cd api

# Install dependencies (using uv)
uv sync

# Or using pip
pip install -e .

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
alembic upgrade head
python create_super_admin.py
python seed_platform_config.py

# Run development server
uvicorn src.app:app --reload --host 0.0.0.0 --port 5001
```

#### Frontend Setup

```bash
cd web

# Install dependencies
pnpm install

# Set up environment
cp .env.example .env.local
# Edit .env.local if needed

# Run development server
pnpm dev
```


## Configuration

### Environment Variables

#### Backend (`api/.env`)
```bash
# Database
DATABASE_URL=postgresql://synkora:synkora@localhost:5432/synkora

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
ENCRYPTION_KEY=your-encryption-key

# Application
APP_ENV=development
API_HOST=0.0.0.0
API_PORT=5001

# Storage
STORAGE_PROVIDER=s3
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_ENDPOINT_URL=http://localhost:9000
AWS_BUCKET_NAME=synkora-storage

# LLM Providers (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Langfuse (optional)
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=http://localhost:3001
```

#### Frontend (`web/.env.local`)
```bash
NEXT_PUBLIC_API_URL=http://localhost:5001
NEXT_PUBLIC_APP_URL=http://localhost:3005
```


## Documentation

- [Architecture Report](ARCHITECTURE.md) - Comprehensive technical analysis, design patterns, and scorecard
- [API Documentation](api/README.md) - Backend API details and setup
- [Frontend Documentation](web/README.md) - Frontend setup and development
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute
- [Security Policy](SECURITY.md) - Security guidelines and reporting
- [Changelog](CHANGELOG.md) - Version history and changes
- [Load Testing Guide](api/tests/load/README.md) - k6 load testing suite documentation


## Testing

### CI/CD Pipeline

Our CI/CD pipeline runs on every push and pull request:

| Workflow | Description | Status |
|----------|-------------|--------|
| **Main CI** | Orchestrates all tests | [![CI Pipeline](https://github.com/getsynkora/synkora-ai/actions/workflows/main-ci.yml/badge.svg)](https://github.com/getsynkora/synkora-ai/actions/workflows/main-ci.yml) |
| **API Tests** | Python unit & integration tests | [![API Tests](https://github.com/getsynkora/synkora-ai/actions/workflows/api-tests.yml/badge.svg)](https://github.com/getsynkora/synkora-ai/actions/workflows/api-tests.yml) |
| **Web Tests** | Frontend linting & type checks | [![Web Tests](https://github.com/getsynkora/synkora-ai/actions/workflows/web-tests.yml/badge.svg)](https://github.com/getsynkora/synkora-ai/actions/workflows/web-tests.yml) |
| **Style Check** | Code formatting & linting | [![Style](https://github.com/getsynkora/synkora-ai/actions/workflows/style.yml/badge.svg)](https://github.com/getsynkora/synkora-ai/actions/workflows/style.yml) |
| **Docker Build** | Container build validation | [![Docker](https://github.com/getsynkora/synkora-ai/actions/workflows/docker-build.yml/badge.svg)](https://github.com/getsynkora/synkora-ai/actions/workflows/docker-build.yml) |

### Code Coverage

[![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/rajuniit/6adfe45792942ae62d18c5e89128498b/raw/coverage-badge.json)](https://github.com/getsynkora/synkora-ai/actions/workflows/api-tests.yml)

Coverage reports are generated for every pull request with inline annotations.

### Backend Tests
```bash
cd api
pytest                              # Run all tests
pytest --cov=src                    # With coverage
pytest --cov=src --cov-report=html  # Generate HTML coverage report
pytest tests/unit/                  # Unit tests only
pytest tests/integration/           # Integration tests only
pytest -v -k "test_name"            # Run specific test
pytest -x                           # Stop on first failure
```

### Frontend Tests
```bash
cd web
pnpm test                # Run tests
pnpm type-check          # TypeScript type checking
pnpm lint                # ESLint
```

### Running Tests Locally with Act

You can run GitHub Actions locally using [act](https://github.com/nektos/act):

```bash
# Install act (macOS)
brew install act

# Run API tests locally
act workflow_dispatch -W .github/workflows/api-tests.yml -j test --matrix python-version:3.11 -P ubuntu-latest=catthehacker/ubuntu:act-latest --container-architecture linux/amd64
```


## Development

### Database Migrations

```bash
# Create a new migration
cd api
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Quality

**Backend:**
```bash
cd api
ruff format .           # Format code
ruff check .            # Lint code
basedpyright            # Type checking
```

**Frontend:**
```bash
cd web
pnpm lint               # ESLint
pnpm type-check         # TypeScript
```

### Adding Dependencies

**Backend:**
```bash
cd api
uv add package-name              # Production dependency
uv add --dev package-name        # Development dependency
```

**Frontend:**
```bash
cd web
pnpm add package-name            # Production dependency
pnpm add -D package-name         # Development dependency
```


## Deployment

### Docker Compose

```bash
# Build all images
docker-compose build

# Start all services
docker-compose up -d
```

### Kubernetes

Helm charts are provided in the `helm/` directory:

```bash
# Install
helm install synkora ./helm/synkora

# Upgrade
helm upgrade synkora ./helm/synkora

# Uninstall
helm uninstall synkora
```


## Security

> Detailed in [ARCHITECTURE.md — Security](ARCHITECTURE.md#security)

- **Authentication**: JWT with token blacklisting, version tracking, and secure sessionStorage
- **Authorization**: Role-based access control (RBAC) with fine-grained permissions and tenant isolation
- **CSRF Protection**: Server-side token validation in Redis with session binding and fail-closed design
- **Security Headers**: CSP with nonces, HSTS with preload, X-Frame-Options DENY, Permissions-Policy
- **Input Sanitization**: 60+ XSS pattern detection covering HTML5 event handlers
- **Encryption**: Fernet encryption at rest for API keys, OAuth tokens, and secrets
- **Rate Limiting**: Redis-backed distributed rate limiting with per-endpoint configuration
- **SSO**: Okta and SAML support for enterprise authentication


## Monitoring & Observability

- **Langfuse**: LLM observability, tracing, and analytics
- **Prometheus Metrics**: `/metrics` endpoint for scraping (request counts, latencies, LLM usage)
- **Performance Stats**: `/api/v1/stats/performance` for connection pools, circuit breakers
- **Health Checks**: `/health` endpoint for liveness probes
- **Logging**: Structured JSON logging with configurable levels


## Performance & Scalability

> Detailed in [ARCHITECTURE.md — Scalability](ARCHITECTURE.md#scalability--horizontal-scaling)

- **Stateless API**: All state in PostgreSQL/Redis, enabling horizontal pod scaling
- **Distributed WebSocket**: Redis pub/sub for cross-pod message delivery with source-pod deduplication
- **Distributed Cache**: Cross-pod cache invalidation via Redis pub/sub
- **Circuit Breakers**: Full state machine (CLOSED/OPEN/HALF_OPEN) with decorator API
- **Connection Pooling**: 50+25 DB connections, 200 Redis connections, pooled vector DB clients
- **Celery Queue Separation**: Default, email, notifications, agents, billing queues with dedicated workers
- **Streaming Uploads**: Multipart S3 uploads for large files without memory overhead
- **Async Database**: Dual engine architecture (asyncpg for FastAPI, psycopg2 for Celery)

### Load Test Results (Stress Test @ 300 VUs)

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Health check p95 | < 100ms | 42ms | Pass |
| List agents p95 | < 500ms | 198ms | Pass |
| Chat stream p95 | < 5s | 2.8s | Pass |
| KB search p95 | < 1s | 342ms | Pass |
| Error rate | < 5% | 0.8% | Pass |

See [Load Testing Guide](api/tests/load/README.md) for running your own tests.


## Contributing

We welcome contributions from the community! Whether you're fixing bugs, improving documentation, or proposing new features, your help is appreciated.

### How to Contribute

1. **Fork the repository** and create your branch from `master`
2. **Make your changes** following our coding standards
3. **Add tests** for any new functionality
4. **Run the test suite** to ensure everything passes
5. **Update documentation** as needed
6. **Submit a pull request** with a clear description of your changes

Please read our [Contributing Guidelines](CONTRIBUTING.md) for detailed information.

### Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

### Development Setup

See the [Quick Start](#quick-start) section for development environment setup instructions.


## Bug Reports & Feature Requests

- **Bug Reports**: [Submit a bug report](.github/ISSUE_TEMPLATE/bug_report.md)
- **Feature Requests**: [Request a feature](.github/ISSUE_TEMPLATE/feature_request.md)
- **Security Issues**: See our [Security Policy](SECURITY.md)


## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

You are free to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of this software for any purpose, including commercial use, without restriction.


## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and version history.


## Acknowledgments

Built with amazing open source technologies:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Next.js](https://nextjs.org/) - React framework
- [LiteLLM](https://github.com/BerriAI/litellm) - LLM provider integration
- [Langfuse](https://langfuse.com/) - LLM observability
- [Qdrant](https://qdrant.tech/) - Vector database
- And many more! See [package files](api/pyproject.toml) for complete list


## Support & Community

### Getting Help

- **Documentation**: See [api/README.md](api/README.md) and [web/README.md](web/README.md) for detailed setup
- **API Reference**: Interactive API docs at `/api/v1/docs` when running locally
- **Discussions**: Join our GitHub Discussions for questions and community support
- **Issues**: Report bugs via [GitHub Issues](https://github.com/getsynkora/synkora-ai/issues)
- **Security**: Report vulnerabilities via our [Security Policy](SECURITY.md)

### Community

- **GitHub Discussions**: Ask questions and share ideas
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
- **Code of Conduct**: Read our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)


## Roadmap

See [CHANGELOG.md](CHANGELOG.md) for recent changes and version history.

### Upcoming Features
- Enhanced multi-agent workflow orchestration
- Advanced analytics dashboard with custom reports
- Additional LLM provider integrations
- Improved knowledge base search with hybrid retrieval
- Multi-language UI support
- Plugin marketplace


## Project Status

Synkora is actively maintained and in production use. We follow semantic versioning and maintain backward compatibility wherever possible.

- **Stability**: Production-ready
- **Maintenance**: Actively maintained
- **Release Cycle**: Regular updates and security patches

---

<div align="center">

Built with ❤️ by the Synkora Community

[Back to Top](#synkora)

</div>
