# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `prometheus-client` library replaces custom metrics implementation (thread-safe, standard Prometheus format)
- `METRICS_AUTH_TOKEN` setting — when set, `/metrics` and `/api/v1/stats/performance` require `Authorization: Bearer <token>`
- `LANGFUSE_ENCRYPTION_KEY` is now required (no default) — `docker-compose` errors loudly if not set

### Changed
- JWT access tokens moved from `localStorage` to in-memory storage — XSS cannot steal in-memory variables
- Refresh tokens moved from `localStorage` to `sessionStorage` (cleared when browser tab closes)
- Axios client now sends `withCredentials: true` — HttpOnly session cookie set by backend is used automatically
- Redis auth checks in `get_current_account` combined into a single pipeline round-trip (was 2 sequential calls)
- Telegram bot auto-start removed from API process — bots are managed exclusively by the dedicated `bot-worker` service
- `docker-compose.yml` `version:` field removed (deprecated in modern Docker Compose)
- MinIO credentials now read from environment variables with dev-only defaults clearly documented

### Security
- `/metrics` and `/api/v1/stats/performance` endpoints protected by optional bearer token
- `LANGFUSE_ENCRYPTION_KEY` default (all-zeros) removed to prevent accidental production deployment with weak key
- Access tokens no longer written to `localStorage` — mitigates XSS token theft

## [1.0.0] - 2026-01-29

### Added
- Core agent development platform
- Multi-LLM provider support (OpenAI, Anthropic, Google, Azure, etc.)
- Knowledge base integration with RAG capabilities
- Tool registration system for extensibility
- Webhook support for integrations
- Comprehensive API endpoints for agent management
- Docker and Kubernetes deployment configurations
- Sub-agent workflows (sequential, parallel, loop, custom)
- Voice capabilities integration
- Slack, WhatsApp, and Microsoft Teams bot integrations
- Custom tool builder interface
- MCP (Model Context Protocol) server support
- Scheduled tasks and automation
- Data source connectors (Gmail, GitHub, Google Drive, etc.)
- Agent domain management with custom instructions
- Chat customization and widget builder
- Output configuration system
- OAuth app management
- Database connection management
- File upload and knowledge base management
- Team collaboration features
- Billing and credit system
- Activity logging and monitoring

### Security
- Enterprise-grade security policies
- Input validation and sanitization
- SQL injection prevention
- XSS and CSRF protection
- RBAC (Role-Based Access Control) implementation
- Secure credential management
- JWT token authentication
- API rate limiting

### Infrastructure
- Helm charts for Kubernetes deployment
- Docker Compose for local development
- Celery for async task processing
- Redis for caching and pub/sub
- PostgreSQL database support
- Elasticsearch integration
- S3 storage integration

[Unreleased]: https://github.com/getsynkora/synkora-ai/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/getsynkora/synkora-ai/releases/tag/v1.0.0
