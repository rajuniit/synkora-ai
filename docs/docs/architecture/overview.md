---
sidebar_position: 1
---

# Architecture Overview

Synkora is built on a modern, scalable architecture designed for AI workloads.

## System Architecture

```
                                 ┌──────────────────┐
                                 │   Load Balancer  │
                                 └────────┬─────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
    ┌─────────▼─────────┐       ┌─────────▼─────────┐       ┌─────────▼─────────┐
    │   Web (Next.js)   │       │   API (FastAPI)   │       │   API (FastAPI)   │
    │      Port 3005    │       │      Port 5001    │       │      Port 5001    │
    └─────────┬─────────┘       └─────────┬─────────┘       └─────────┬─────────┘
              │                           │                           │
              └───────────────────────────┼───────────────────────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
    ┌─────────▼─────────┐       ┌─────────▼─────────┐       ┌─────────▼─────────┐
    │    PostgreSQL     │       │       Redis       │       │      Qdrant       │
    │    (Primary DB)   │       │  (Cache/Queue)    │       │   (Vector DB)     │
    └───────────────────┘       └─────────┬─────────┘       └───────────────────┘
                                          │
                                ┌─────────▼─────────┐
                                │   Celery Workers  │
                                │  (Background Jobs) │
                                └───────────────────┘
```

## Components

### Frontend (Next.js)

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: Zustand
- **Forms**: React Hook Form + Zod

### Backend (FastAPI)

- **Framework**: FastAPI
- **Language**: Python 3.11
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic

### Database

- **Primary**: PostgreSQL 15 with pgvector
- **Cache**: Redis 7
- **Vector**: Qdrant or Pinecone

### Background Jobs

- **Queue**: Celery with Redis broker
- **Scheduler**: Celery Beat

### LLM Integration

- **Unified Client**: LiteLLM
- **Observability**: Langfuse

## Data Flow

### Chat Request Flow

```
1. User sends message via Web/API
2. API validates request
3. Agent retrieves context (KB, history)
4. LLM generates response
5. Response streamed back to user
6. Message stored in database
```

### RAG Flow

```
1. Query received
2. Embed query using embedding model
3. Search vector database
4. Retrieve top-k chunks
5. Rerank results (optional)
6. Inject into LLM context
7. Generate response
```

## Scalability

### Horizontal Scaling

- Stateless API servers
- Redis for session/cache
- Managed databases

### Vertical Scaling

- Celery workers for CPU-intensive tasks
- GPU workers for embedding generation

## Next Steps

- [Backend Architecture](/docs/architecture/backend)
- [Frontend Architecture](/docs/architecture/frontend)
- [Database Schema](/docs/architecture/database)
