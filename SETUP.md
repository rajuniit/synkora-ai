# Synkora Setup Guide

Setup commands after a fresh Docker volume cleanup.

## 1. Start Docker Services

```bash
docker-compose up -d
```

Wait ~10-15 seconds for PostgreSQL to be ready.

## 2. Run Database Migrations

```bash
# Check for multiple heads
docker-compose exec api alembic heads

# If multiple heads exist, merge them first
docker-compose exec api alembic merge heads -m "merge_heads"

# Run migrations
docker-compose exec api alembic upgrade head
```

### If tables already exist (DuplicateTable error)

```bash
# Stamp all migrations as already applied
docker-compose exec api alembic stamp heads

# Verify
docker-compose exec api alembic current
```

## 3. Create Super Admin

```bash
docker-compose exec api python create_super_admin.py
```

Interactive prompts will ask for:
- Email
- Password
- Full name
- Tenant/organization name

## 4. Seed Platform Config

```bash
docker-compose exec api python seed_platform_config.py
```

Interactive prompts for:
- Platform branding (name, logo URL, support email)
- SMTP configuration (optional)
- Stripe configuration (optional)
- Storage configuration (S3/MinIO)

For non-interactive mode (uses environment variables):
```bash
docker-compose exec api python seed_platform_config.py --non-interactive
```

## 5. Seed Billing Plans (Optional)

```bash
docker-compose exec api python -c "from src.core.database import get_db; from src.services.billing.seed_plans import seed_subscription_plans; db = next(get_db()); seed_subscription_plans(db); print('Billing plans seeded!')"
```

## 6. Start Frontend

```bash
cd web
pnpm install
pnpm dev
```

## Service Ports

| Service | Port | URL |
|---------|------|-----|
| Web Frontend | 3005 | http://localhost:3005 |
| API | 5001 | http://localhost:5001 |
| API Docs | 5001 | http://localhost:5001/api/v1/docs |
| PostgreSQL | 5432 | - |
| Redis | 6379 | - |
| Qdrant | 6333 | http://localhost:6333 |
| MinIO Console | 9001 | http://localhost:9001 (minioadmin/minioadmin) |
| Langfuse | 3001 | http://localhost:3001 |

## Quick Reset (Full Cleanup)

```bash
# Stop and remove everything including volumes
docker-compose down -v

# Start fresh
docker-compose up -d

# Then follow steps 2-5 above
```
