---
sidebar_position: 6
---

# Background Jobs

Celery-based task queue for async operations.

## Architecture

```
API → Redis (Broker) → Celery Workers → Result Backend (Redis)
                     → Celery Beat (Scheduler)
```

## Configuration

```python
# celery_app.py
from celery import Celery

celery = Celery(
    "synkora",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_routes={
        "tasks.document.*": {"queue": "documents"},
        "tasks.embedding.*": {"queue": "embeddings"},
    },
)
```

## Task Types

### Document Processing

```python
@celery.task
def process_document(document_id: str):
    """Process uploaded document."""
    document = get_document(document_id)

    # Parse content
    content = parse_document(document.file_path)

    # Chunk
    chunks = chunk_content(content, document.kb.chunking_config)

    # Embed
    for chunk in chunks:
        embed_chunk.delay(chunk.id)

    update_document_status(document_id, "ready")
```

### Embedding Generation

```python
@celery.task
def embed_chunk(chunk_id: str):
    """Generate embedding for a chunk."""
    chunk = get_chunk(chunk_id)

    embedding = generate_embedding(chunk.content)

    store_embedding(chunk_id, embedding)
```

### Webhook Delivery

```python
@celery.task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
)
def deliver_webhook(self, webhook_id: str, event: dict):
    """Deliver webhook with retry."""
    try:
        webhook = get_webhook(webhook_id)
        response = requests.post(
            webhook.url,
            json=event,
            headers=sign_request(webhook.secret, event),
            timeout=30,
        )
        response.raise_for_status()
    except Exception as exc:
        self.retry(exc=exc, countdown=2 ** self.request.retries * 60)
```

## Scheduled Tasks

```python
# Celery Beat schedule
celery.conf.beat_schedule = {
    "cleanup-expired-conversations": {
        "task": "tasks.cleanup.cleanup_conversations",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    "generate-usage-reports": {
        "task": "tasks.reports.generate_daily_report",
        "schedule": crontab(hour=0, minute=30),  # Daily at 12:30 AM
    },
    "refresh-oauth-tokens": {
        "task": "tasks.oauth.refresh_expiring_tokens",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
}
```

## Running Workers

```bash
# Main worker
celery -A src.celery_app worker --loglevel=info

# Document processing queue
celery -A src.celery_app worker -Q documents --loglevel=info

# Scheduler
celery -A src.celery_app beat --loglevel=info
```

## Monitoring

```bash
# Flower monitoring
celery -A src.celery_app flower --port=5555
```
