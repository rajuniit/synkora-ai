---
sidebar_position: 3
---

# Configuration

Synkora is configured through environment variables. This guide covers all available configuration options.

## Environment Variables

### Core Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | Application secret key for JWT signing | - | Yes |
| `DEBUG` | Enable debug mode | `false` | No |
| `ENVIRONMENT` | Environment name (development, staging, production) | `development` | No |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` | No |

### Database

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `DATABASE_POOL_SIZE` | Connection pool size | `10` | No |
| `DATABASE_MAX_OVERFLOW` | Max overflow connections | `20` | No |

```env
DATABASE_URL=postgresql://user:password@localhost:5432/synkora
DATABASE_POOL_SIZE=20
```

### Redis

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `REDIS_URL` | Redis connection URL | - | Yes |
| `CACHE_TTL` | Default cache TTL in seconds | `3600` | No |

```env
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600
```

### LLM Providers

Configure API keys for LLM providers you want to use:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | If using OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic API key | If using Anthropic |
| `GOOGLE_API_KEY` | Google AI API key | If using Google |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI key | If using Azure |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | If using Azure |
| `AZURE_OPENAI_API_VERSION` | Azure API version | If using Azure |

```env
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
GOOGLE_API_KEY=your-google-key
```

### Vector Database

#### Qdrant

| Variable | Description | Default |
|----------|-------------|---------|
| `QDRANT_URL` | Qdrant server URL | `http://localhost:6333` |
| `QDRANT_API_KEY` | Qdrant API key (for cloud) | - |

#### Pinecone

| Variable | Description | Required |
|----------|-------------|----------|
| `PINECONE_API_KEY` | Pinecone API key | If using Pinecone |
| `PINECONE_ENVIRONMENT` | Pinecone environment | If using Pinecone |

```env
# Qdrant (self-hosted)
QDRANT_URL=http://localhost:6333

# Or Pinecone (cloud)
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=us-east-1-aws
```

### File Storage

| Variable | Description | Default |
|----------|-------------|---------|
| `STORAGE_TYPE` | Storage backend (local, s3, minio) | `local` |
| `STORAGE_PATH` | Local storage path | `./uploads` |
| `S3_BUCKET` | S3 bucket name | - |
| `S3_ACCESS_KEY` | AWS access key | - |
| `S3_SECRET_KEY` | AWS secret key | - |
| `S3_REGION` | AWS region | `us-east-1` |
| `S3_ENDPOINT` | Custom S3 endpoint (for MinIO) | - |

```env
# Local storage
STORAGE_TYPE=local
STORAGE_PATH=/data/uploads

# S3
STORAGE_TYPE=s3
S3_BUCKET=synkora-uploads
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_REGION=us-east-1

# MinIO
STORAGE_TYPE=minio
S3_ENDPOINT=http://minio:9000
S3_BUCKET=synkora
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
```

### Authentication

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiry | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry | `7` |

### OAuth Providers

For SSO integration:

```env
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# GitHub OAuth
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret

# Microsoft OAuth
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
```

### Email

| Variable | Description | Default |
|----------|-------------|---------|
| `SMTP_HOST` | SMTP server host | - |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username | - |
| `SMTP_PASSWORD` | SMTP password | - |
| `SMTP_FROM_EMAIL` | Default from email | - |

```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_FROM_EMAIL=noreply@your-domain.com
```

### Billing (Stripe)

| Variable | Description | Required |
|----------|-------------|----------|
| `STRIPE_SECRET_KEY` | Stripe secret key | If using billing |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret | If using billing |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | If using billing |

### Observability

| Variable | Description | Default |
|----------|-------------|---------|
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | - |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | - |
| `LANGFUSE_HOST` | Langfuse host URL | - |

```env
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Celery

| Variable | Description | Default |
|----------|-------------|---------|
| `CELERY_BROKER_URL` | Celery broker URL | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://localhost:6379/0` |

## Frontend Configuration

Frontend-specific environment variables (prefixed with `NEXT_PUBLIC_`):

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:5001` |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL | `ws://localhost:5001` |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | - |

Create a `.env.local` file in the `web/` directory:

```env
NEXT_PUBLIC_API_URL=https://api.your-domain.com
NEXT_PUBLIC_WS_URL=wss://api.your-domain.com
```

## Example Configuration

### Development

```env
# Core
DEBUG=true
ENVIRONMENT=development
SECRET_KEY=dev-secret-key-change-in-production
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql://synkora:synkora@localhost:5432/synkora

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM
OPENAI_API_KEY=sk-your-dev-key

# Vector DB
QDRANT_URL=http://localhost:6333

# Storage
STORAGE_TYPE=local
STORAGE_PATH=./uploads
```

### Production

```env
# Core
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=your-very-long-random-secret-key-at-least-32-chars
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://synkora:secure-password@db.example.com:5432/synkora
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://:password@redis.example.com:6379/0

# LLM
OPENAI_API_KEY=sk-prod-key
ANTHROPIC_API_KEY=sk-ant-prod-key

# Vector DB
QDRANT_URL=https://qdrant.example.com:6333
QDRANT_API_KEY=your-qdrant-api-key

# Storage
STORAGE_TYPE=s3
S3_BUCKET=synkora-prod
S3_REGION=us-east-1

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-key
SMTP_FROM_EMAIL=noreply@your-domain.com

# Billing
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Observability
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use strong, unique `SECRET_KEY`** (at least 32 characters)
3. **Rotate API keys** regularly
4. **Use secrets management** in production (AWS Secrets Manager, HashiCorp Vault, etc.)
5. **Encrypt database connections** with SSL in production
6. **Restrict database access** to application servers only
