---
sidebar_position: 10
---

# Rate Limits

Synkora enforces rate limits to ensure fair usage and platform stability.

## Rate Limit Tiers

| Plan | Requests/min | Requests/hour | Chat requests/min |
|------|--------------|---------------|-------------------|
| Free | 60 | 1,000 | 10 |
| Pro | 300 | 10,000 | 60 |
| Enterprise | Custom | Custom | Custom |

## Rate Limit Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 299
X-RateLimit-Reset: 1705312800
```

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests per window |
| `X-RateLimit-Remaining` | Remaining requests in window |
| `X-RateLimit-Reset` | Unix timestamp when limit resets |

## Rate Limited Response

When rate limited, you'll receive a `429` response:

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Please try again later.",
    "retry_after": 60
  }
}
```

The `Retry-After` header indicates seconds to wait:

```
Retry-After: 60
```

## Endpoint-Specific Limits

Some endpoints have additional limits:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /agents/{id}/chat` | 60/min (Pro) | 1 minute |
| `POST /knowledge-bases/{id}/documents` | 10/min | 1 minute |
| `POST /knowledge-bases/{id}/crawl` | 5/hour | 1 hour |
| `POST /billing/credits/purchase` | 5/hour | 1 hour |

## Burst Limits

Short burst limits apply to prevent abuse:

| Plan | Burst limit | Window |
|------|-------------|--------|
| Free | 10 | 1 second |
| Pro | 30 | 1 second |
| Enterprise | 100 | 1 second |

## Best Practices

### Implement Exponential Backoff

```typescript
async function requestWithRetry(fn, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (error.code === 'RATE_LIMITED' && i < maxRetries - 1) {
        const delay = Math.pow(2, i) * 1000 + Math.random() * 1000;
        await new Promise(r => setTimeout(r, delay));
        continue;
      }
      throw error;
    }
  }
}
```

### Monitor Rate Limit Headers

```typescript
const response = await fetch(url, options);
const remaining = response.headers.get('X-RateLimit-Remaining');

if (parseInt(remaining) < 10) {
  console.warn('Approaching rate limit');
}
```

### Use Batch Operations

Instead of multiple single requests:

```typescript
// ❌ Bad: Multiple requests
for (const doc of documents) {
  await synkora.knowledgeBases.uploadDocument(kbId, doc);
}

// ✅ Good: Batch request
await synkora.knowledgeBases.uploadDocuments(kbId, documents);
```

### Cache Responses

Cache read operations where appropriate:

```typescript
const cache = new Map();

async function getAgent(id) {
  if (cache.has(id)) {
    return cache.get(id);
  }

  const agent = await synkora.agents.get(id);
  cache.set(id, agent);
  return agent;
}
```

## Increasing Limits

### Pro Plan

Upgrade to Pro for higher limits:
- 5x more requests per minute
- 10x more requests per hour
- Priority queue access

### Enterprise Plan

Contact sales for:
- Custom rate limits
- Dedicated infrastructure
- SLA guarantees
- Priority support

## Monitoring Usage

Check your current rate limit status:

```http
GET /api/v1/rate-limit/status
```

```json
{
  "success": true,
  "data": {
    "plan": "pro",
    "limits": {
      "requests_per_minute": 300,
      "requests_per_hour": 10000
    },
    "current": {
      "minute": {
        "used": 45,
        "remaining": 255,
        "resets_at": "2024-01-15T10:31:00Z"
      },
      "hour": {
        "used": 1500,
        "remaining": 8500,
        "resets_at": "2024-01-15T11:00:00Z"
      }
    }
  }
}
```
