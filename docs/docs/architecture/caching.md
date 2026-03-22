---
sidebar_position: 5
---

# Caching Strategy

Redis-based caching for performance optimization.

## Cache Layers

```
Request → Cache Check → [HIT] → Return cached
                      → [MISS] → Compute → Cache → Return
```

## Implementation

### Cache Decorator

```python
from functools import wraps
from core.cache import redis_client

def cache(ttl: int = 3600, prefix: str = ""):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{prefix}:{hash(args)}:{hash(frozenset(kwargs.items()))}"

            cached = await redis_client.get(key)
            if cached:
                return json.loads(cached)

            result = await func(*args, **kwargs)
            await redis_client.setex(key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

### Usage

```python
@cache(ttl=300, prefix="agent")
async def get_agent(agent_id: str) -> Agent:
    return await db.agents.get(agent_id)
```

## Cache Patterns

### Agent Configuration

```python
# Cache agent config for fast chat responses
AGENT_CACHE_TTL = 300  # 5 minutes

async def get_cached_agent(agent_id: str):
    key = f"agent:{agent_id}"
    cached = await redis.get(key)

    if cached:
        return Agent.parse_raw(cached)

    agent = await db.agents.get(agent_id)
    await redis.setex(key, AGENT_CACHE_TTL, agent.json())
    return agent
```

### Session Data

```python
# Store session state in Redis
SESSION_TTL = 86400  # 24 hours

async def set_session(session_id: str, data: dict):
    await redis.setex(f"session:{session_id}", SESSION_TTL, json.dumps(data))

async def get_session(session_id: str) -> dict:
    data = await redis.get(f"session:{session_id}")
    return json.loads(data) if data else None
```

### Rate Limiting

```python
# Sliding window rate limiter
async def check_rate_limit(key: str, limit: int, window: int) -> bool:
    current = await redis.incr(key)

    if current == 1:
        await redis.expire(key, window)

    return current <= limit
```

## Cache Invalidation

### Manual Invalidation

```python
async def update_agent(agent_id: str, data: UpdateRequest):
    agent = await db.agents.update(agent_id, data)

    # Invalidate cache
    await redis.delete(f"agent:{agent_id}")

    return agent
```

### Pattern Invalidation

```python
# Delete all keys matching pattern
async def invalidate_tenant_cache(tenant_id: str):
    keys = await redis.keys(f"*:tenant:{tenant_id}:*")
    if keys:
        await redis.delete(*keys)
```

## Recommended TTLs

| Data Type | TTL | Reason |
|-----------|-----|--------|
| Agent config | 5 min | Rarely changes |
| User session | 24 hours | Session duration |
| API responses | 1 min | Freshness vs load |
| Rate limits | 1 min | Window size |
