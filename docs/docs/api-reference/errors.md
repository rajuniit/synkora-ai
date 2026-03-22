---
sidebar_position: 9
---

# Error Codes

Synkora uses conventional HTTP response codes and returns structured error responses.

## HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `201` | Created |
| `204` | No content |
| `400` | Bad request |
| `401` | Unauthorized |
| `403` | Forbidden |
| `404` | Not found |
| `409` | Conflict |
| `422` | Validation error |
| `429` | Rate limited |
| `500` | Internal server error |
| `503` | Service unavailable |

## Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "name": ["Name is required"],
      "model_name": ["Invalid model name"]
    },
    "request_id": "req-123456"
  }
}
```

## Error Codes Reference

### Authentication Errors (401)

| Code | Description |
|------|-------------|
| `INVALID_TOKEN` | JWT token is invalid or malformed |
| `EXPIRED_TOKEN` | JWT token has expired |
| `INVALID_API_KEY` | API key is invalid |
| `MISSING_AUTH` | No authentication provided |

### Authorization Errors (403)

| Code | Description |
|------|-------------|
| `FORBIDDEN` | User lacks permission for this action |
| `TENANT_ACCESS_DENIED` | User cannot access this tenant |
| `SCOPE_INSUFFICIENT` | API key lacks required scope |

### Resource Errors (404)

| Code | Description |
|------|-------------|
| `AGENT_NOT_FOUND` | Agent does not exist |
| `CONVERSATION_NOT_FOUND` | Conversation does not exist |
| `KNOWLEDGE_BASE_NOT_FOUND` | Knowledge base does not exist |
| `DOCUMENT_NOT_FOUND` | Document does not exist |
| `USER_NOT_FOUND` | User does not exist |

### Validation Errors (422)

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Request body validation failed |
| `INVALID_MODEL` | Model name is not supported |
| `INVALID_FILE_TYPE` | File type not supported |
| `FILE_TOO_LARGE` | File exceeds size limit |
| `INVALID_URL` | URL is malformed |

### Conflict Errors (409)

| Code | Description |
|------|-------------|
| `SLUG_ALREADY_EXISTS` | Slug is already in use |
| `EMAIL_ALREADY_EXISTS` | Email is already registered |
| `DUPLICATE_RESOURCE` | Resource already exists |

### Limit Errors (429/402)

| Code | Description |
|------|-------------|
| `RATE_LIMITED` | Too many requests |
| `AGENT_LIMIT_EXCEEDED` | Maximum agents for plan |
| `KB_LIMIT_EXCEEDED` | Maximum knowledge bases for plan |
| `INSUFFICIENT_CREDITS` | Not enough credits |
| `QUOTA_EXCEEDED` | Monthly quota exceeded |

### Processing Errors (500)

| Code | Description |
|------|-------------|
| `INTERNAL_ERROR` | Unexpected server error |
| `LLM_ERROR` | Error from LLM provider |
| `EMBEDDING_ERROR` | Error generating embeddings |
| `VECTOR_DB_ERROR` | Error from vector database |

### External Service Errors (503)

| Code | Description |
|------|-------------|
| `SERVICE_UNAVAILABLE` | Service temporarily unavailable |
| `LLM_UNAVAILABLE` | LLM provider unavailable |
| `EXTERNAL_SERVICE_ERROR` | Third-party service error |

## Handling Errors

### JavaScript/TypeScript

```typescript
try {
  const agent = await synkora.agents.create({ name: 'Test' });
} catch (error) {
  if (error.code === 'VALIDATION_ERROR') {
    console.error('Validation failed:', error.details);
  } else if (error.code === 'AGENT_LIMIT_EXCEEDED') {
    console.error('Upgrade your plan for more agents');
  } else {
    console.error('Unexpected error:', error.message);
  }
}
```

### Python

```python
try:
    agent = synkora.agents.create(name="Test")
except SynkoraError as e:
    if e.code == "VALIDATION_ERROR":
        print(f"Validation failed: {e.details}")
    elif e.code == "AGENT_LIMIT_EXCEEDED":
        print("Upgrade your plan for more agents")
    else:
        print(f"Unexpected error: {e.message}")
```

## Request IDs

Every response includes a request ID for debugging:

```
X-Request-ID: req-123456
```

Include this ID when contacting support.
