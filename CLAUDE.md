# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Synkora is a production-ready AI/LLM application platform for building, deploying, and managing AI agents. It's a full-stack monorepo with a FastAPI backend (`api/`) and Next.js frontend (`web/`).

## Development Commands

### Backend (api/)

```bash
cd api

# Install dependencies
uv sync                                    # Using uv (recommended)
pip install -e .                           # Using pip

# Database setup
alembic upgrade head                       # Run migrations
python create_super_admin.py               # Create admin user
python seed_platform_config.py             # Seed platform config

# Development server
uvicorn src.app:app --reload --host 0.0.0.0 --port 5001

# Code quality
ruff format .                              # Format code
ruff check .                               # Lint code
basedpyright                               # Type checking

# Testing
pytest                                     # Run all tests
pytest tests/unit/                         # Unit tests only
pytest tests/integration/                  # Integration tests only
pytest --cov=src                           # With coverage
pytest -v -k "test_name"                   # Run specific test

# Database migrations
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                              # Apply migrations
alembic downgrade -1                              # Rollback one

# Celery workers (run separately)
celery -A src.celery_app worker --loglevel=info   # Worker
celery -A src.celery_app beat --loglevel=info     # Scheduler
```

### Frontend (web/)

```bash
cd web

pnpm install                # Install dependencies
pnpm dev                    # Development server (port 3005)
pnpm build                  # Production build
pnpm lint                   # ESLint
pnpm type-check             # TypeScript checking
```

### Docker Compose

```bash
docker-compose up -d                      # Start all services
docker-compose logs -f api                # View API logs
docker-compose exec api pytest            # Run tests in container
docker-compose exec api alembic upgrade head  # Run migrations
```

## Architecture

### Backend Structure (api/src/)

- **app.py** - FastAPI application entry point
- **celery_app.py** - Celery configuration
- **config/** - Settings and configuration (settings.py is the main config)
- **core/** - Database connections, WebSocket, caching, exceptions
- **models/** - SQLAlchemy models (70+ models, all inherit from BaseModel with UUID primary keys)
- **schemas/** - Pydantic request/response schemas
- **controllers/** - API route handlers organized by domain
- **services/** - Business logic layer (agents/, knowledge_base/, billing/, oauth/, etc.)
- **middleware/** - Auth, rate limiting, CORS, error handling
- **tasks/** - Celery background tasks

### Frontend Structure (web/)

- **app/** - Next.js 15 App Router pages
  - **(auth)/** - Authentication pages (signin, signup, verify, reset)
  - **(dashboard)/** - Dashboard pages (agents, knowledge-bases, settings, etc.)
- **components/** - React components
  - **chat/** - Chat interface components
  - **agents/** - Agent management components
  - **ui/** - Base UI components (Button, Input, Modal, Card, etc.)
- **lib/** - Utilities
  - **api/client.ts** - Axios API client with interceptors
  - **store/** - Zustand state stores
  - **hooks/** - Custom React hooks
  - **types/** - TypeScript type definitions

### Key Services

- **agents/agent_manager.py** - Agent lifecycle and orchestration
- **agents/chat_stream_service.py** - Real-time chat streaming via SSE
- **agents/llm_client.py** - Multi-provider LLM client (via LiteLLM)
- **knowledge_base/rag_service.py** - RAG with vector search
- **knowledge_base/enhanced_rag_service.py** - Advanced RAG features
- **billing/credit_service.py** - Credit-based billing
- **oauth/** - OAuth provider implementations (Google, GitHub, Slack, Jira, etc.)

### Multi-Tenancy

Most models include `tenant_id` for data isolation. Use the `TenantMixin` for new models requiring tenant isolation. Authentication middleware extracts tenant context from JWT tokens.

### Database

PostgreSQL with pgvector extension. Key model relationships:
- Tenant -> Accounts (via TenantAccountJoin)
- Agent -> AgentTool, AgentKnowledgeBase, AgentLLMConfig, AgentWidget
- KnowledgeBase -> Document -> DocumentSegment
- Conversation -> Message

## Code Patterns

### Backend

- SQLAlchemy models use UUID primary keys with `created_at`/`updated_at` timestamps
- Sensitive data (API keys, tokens) encrypted at rest using Fernet
- Services follow async patterns with `run_in_executor` for blocking operations
- Tool integrations are in `services/agents/internal_tools/` and registered in `tool_registrations/`
- OAuth providers are in `services/oauth/` with a common interface

### Frontend

- App Router with route groups: `(auth)` for public auth, `(dashboard)` for authenticated
- State management via Zustand stores in `lib/store/`
- Forms use React Hook Form + Zod validation
- API calls through `lib/api/client.ts` with auth token interceptors
- Tailwind CSS for styling with custom design tokens in globals.css

## Testing

Backend tests use pytest with markers:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests (requires database)
- `@pytest.mark.slow` - Slow-running tests

Test database runs on port 5433 (via docker-compose postgres-test service).

## Code Quality

### Backend (Ruff)
- Line length: 120 characters
- Target: Python 3.11
- Rules: E, W, F, I (isort), B, C4, UP, ARG, SIM

### Frontend (ESLint + TypeScript)
- Strict TypeScript mode enabled
- Path alias: `@/*` maps to project root

## Important Files

| Purpose | Path |
|---------|------|
| API entry | api/src/app.py |
| Settings | api/src/config/settings.py |
| Base model | api/src/models/base.py |
| Agent model | api/src/models/agent.py |
| Chat streaming | api/src/services/agents/chat_stream_service.py |
| Tool definitions | api/src/services/agents/adk_tools.py |
| API client | web/lib/api/client.ts |
| Auth store | web/lib/store/auth.ts |

## External Dependencies

- **LiteLLM** - Unified LLM provider interface (OpenAI, Anthropic, Google, etc.)
- **Qdrant/Pinecone** - Vector databases for knowledge base search
- **Langfuse** - LLM observability and tracing
- **Celery + Redis** - Background task queue
- **MinIO/S3** - File storage
- **Stripe** - Billing and subscriptions
