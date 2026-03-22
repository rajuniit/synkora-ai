---
sidebar_position: 3
---

# Production Checklist

Essential steps before deploying Synkora to production.

## Security

- [ ] Generate strong `SECRET_KEY` (32+ characters)
- [ ] Enable HTTPS/TLS everywhere
- [ ] Configure CORS properly
- [ ] Set secure cookie flags
- [ ] Enable rate limiting
- [ ] Rotate default credentials

## Database

- [ ] Use managed PostgreSQL (RDS, Cloud SQL)
- [ ] Enable SSL for connections
- [ ] Configure connection pooling
- [ ] Set up automated backups
- [ ] Run migrations: `alembic upgrade head`

## Redis

- [ ] Use managed Redis (ElastiCache, Memorystore)
- [ ] Enable persistence
- [ ] Configure password authentication

## Vector Database

- [ ] Use Qdrant Cloud or managed Pinecone
- [ ] Configure API key authentication
- [ ] Size appropriately for your data

## Environment Variables

```env
# Core
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=your-very-long-random-secret-key

# Database
DATABASE_URL=postgresql://user:pass@host:5432/synkora?sslmode=require
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://:password@host:6379/0

# LLM
OPENAI_API_KEY=sk-prod-key

# Storage
STORAGE_TYPE=s3
S3_BUCKET=synkora-prod

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_FROM_EMAIL=noreply@your-domain.com
```

## Monitoring

- [ ] Set up application logging
- [ ] Configure error tracking (Sentry)
- [ ] Enable LLM observability (Langfuse)
- [ ] Set up uptime monitoring
- [ ] Configure alerts

## Performance

- [ ] Enable caching
- [ ] Configure CDN for static assets
- [ ] Optimize database queries
- [ ] Set appropriate timeouts

## Backups

- [ ] Database: Daily automated backups
- [ ] Vector DB: Regular snapshots
- [ ] File storage: Cross-region replication
- [ ] Test restore procedures

## Scaling

- [ ] API: 2+ replicas minimum
- [ ] Workers: Scale based on queue size
- [ ] Database: Read replicas for high traffic
