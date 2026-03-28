---
sidebar_position: 2
---

# Installation

Synkora can be deployed in several ways depending on your needs. Choose the method that best fits your infrastructure.

## Docker Compose (Recommended)

The easiest way to get started with all services configured.

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 10GB disk space

### Installation

```bash
# Clone the repository
git clone https://github.com/getsynkora/synkora-ai.git
cd synkora

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
# At minimum, set your LLM provider API key

# Start all services
docker-compose up -d
```

### Services Started

| Service | Port | Description |
|---------|------|-------------|
| api | 5001 | FastAPI backend |
| web | 3005 | Next.js frontend |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache & message broker |
| qdrant | 6333 | Vector database |
| celery-worker | - | Background task worker |
| celery-beat | - | Scheduled task runner |

### Verify Installation

```bash
# Check all services are running
docker-compose ps

# View logs
docker-compose logs -f api

# Run database migrations
docker-compose exec api alembic upgrade head

# Create admin user
docker-compose exec api python create_super_admin.py
```

## Kubernetes with Helm

For production deployments with high availability.

### Prerequisites

- Kubernetes 1.24+
- Helm 3.0+
- kubectl configured

### Installation

```bash
# Add Synkora Helm repository
helm repo add synkora https://charts.synkora.io
helm repo update

# Create namespace
kubectl create namespace synkora

# Create secrets
kubectl create secret generic synkora-secrets \
  --namespace synkora \
  --from-literal=OPENAI_API_KEY=sk-your-key \
  --from-literal=DATABASE_URL=postgresql://... \
  --from-literal=SECRET_KEY=$(openssl rand -hex 32)

# Install Synkora
helm install synkora synkora/synkora \
  --namespace synkora \
  --values values.yaml
```

### Example values.yaml

```yaml
global:
  domain: synkora.example.com

api:
  replicas: 3
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "2Gi"
      cpu: "1000m"

web:
  replicas: 2

postgresql:
  enabled: true
  primary:
    persistence:
      size: 50Gi

redis:
  enabled: true
  architecture: standalone

qdrant:
  enabled: true
  persistence:
    size: 20Gi

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: synkora.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: synkora-tls
      hosts:
        - synkora.example.com
```

## Manual Installation

For development or custom setups.

### Backend Setup

```bash
cd api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e .
# Or using uv (recommended)
uv sync

# Set environment variables
export DATABASE_URL=postgresql://user:pass@localhost:5432/synkora
export REDIS_URL=redis://localhost:6379
export OPENAI_API_KEY=sk-your-key
export SECRET_KEY=$(openssl rand -hex 32)

# Run migrations
alembic upgrade head

# Start the server
uvicorn src.app:app --reload --host 0.0.0.0 --port 5001
```

### Frontend Setup

```bash
cd web

# Install dependencies
pnpm install

# Set environment variables
echo "NEXT_PUBLIC_API_URL=http://localhost:5001" > .env.local

# Start development server
pnpm dev
```

### Required Services

Start these services separately or use Docker:

```bash
# PostgreSQL
docker run -d \
  --name synkora-postgres \
  -e POSTGRES_USER=synkora \
  -e POSTGRES_PASSWORD=synkora \
  -e POSTGRES_DB=synkora \
  -p 5432:5432 \
  postgres:15

# Redis
docker run -d \
  --name synkora-redis \
  -p 6379:6379 \
  redis:7

# Qdrant
docker run -d \
  --name synkora-qdrant \
  -p 6333:6333 \
  qdrant/qdrant
```

### Celery Workers

For background tasks:

```bash
# Worker
celery -A src.celery_app worker --loglevel=info

# Scheduler (in another terminal)
celery -A src.celery_app beat --loglevel=info
```

## Cloud Deployments

### AWS

Recommended architecture:
- **ECS/EKS** for API and web services
- **RDS PostgreSQL** for database
- **ElastiCache Redis** for caching
- **S3** for file storage

### Google Cloud

Recommended architecture:
- **GKE** for container orchestration
- **Cloud SQL** for PostgreSQL
- **Memorystore** for Redis
- **Cloud Storage** for files

### Azure

Recommended architecture:
- **AKS** for Kubernetes
- **Azure Database for PostgreSQL**
- **Azure Cache for Redis**
- **Blob Storage** for files

## Post-Installation

After installation, complete these steps:

1. **Run migrations**: `alembic upgrade head`
2. **Create admin user**: `python create_super_admin.py`
3. **Seed platform config**: `python seed_platform_config.py`
4. **Configure LLM providers** in the dashboard
5. **Set up integrations** (Slack, etc.) as needed

## Upgrading

### Docker Compose

```bash
git pull
docker-compose pull
docker-compose up -d
docker-compose exec api alembic upgrade head
```

### Kubernetes

```bash
helm repo update
helm upgrade synkora synkora/synkora --namespace synkora
```

## Uninstalling

### Docker Compose

```bash
docker-compose down -v  # -v removes volumes (data)
```

### Kubernetes

```bash
helm uninstall synkora --namespace synkora
kubectl delete namespace synkora
```
