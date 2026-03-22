---
sidebar_position: 1
---

# Docker Deployment

Deploy Synkora using Docker Compose.

## Quick Start

```bash
git clone https://github.com/rajuniit/synkora-ai.git
cd synkora
cp .env.example .env
docker-compose up -d
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: ./api
    ports:
      - "5001:5001"
    environment:
      - DATABASE_URL=postgresql://synkora:synkora@postgres:5432/synkora
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - postgres
      - redis
      - qdrant

  web:
    build: ./web
    ports:
      - "3005:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:5001

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=synkora
      - POSTGRES_PASSWORD=synkora
      - POSTGRES_DB=synkora
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

  qdrant:
    image: qdrant/qdrant
    volumes:
      - qdrant_data:/qdrant/storage

  celery-worker:
    build: ./api
    command: celery -A src.celery_app worker --loglevel=info
    depends_on:
      - redis
      - postgres

  celery-beat:
    build: ./api
    command: celery -A src.celery_app beat --loglevel=info
    depends_on:
      - redis

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
```

## Post-Deployment

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create admin user
docker-compose exec api python create_super_admin.py

# Check logs
docker-compose logs -f api
```

## SSL/TLS

Use a reverse proxy (nginx, Traefik) for SSL termination.

## Next Steps

- [Kubernetes deployment](/docs/guides/deployment/kubernetes)
- [Production checklist](/docs/guides/deployment/production)
