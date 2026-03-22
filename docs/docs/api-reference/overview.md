---
sidebar_position: 1
---

# API Overview

The Synkora API is a RESTful API that enables you to programmatically manage agents, knowledge bases, conversations, and more.

## Base URL

```
Production: https://api.synkora.io/api/v1
Development: http://localhost:5001/api/v1
```

## Authentication

All API requests require authentication using either:

### Bearer Token (JWT)

```bash
curl -X GET https://api.synkora.io/api/v1/agents \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### API Key

```bash
curl -X GET https://api.synkora.io/api/v1/agents \
  -H "X-API-Key: sk_live_your_api_key"

# Or in Authorization header
curl -X GET https://api.synkora.io/api/v1/agents \
  -H "Authorization: Bearer sk_live_your_api_key"
```

## Request Format

### Content-Type

All POST/PUT/PATCH requests should use JSON:

```bash
curl -X POST https://api.synkora.io/api/v1/agents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Agent", "model_name": "gpt-4o"}'
```

### Query Parameters

Use query parameters for filtering and pagination:

```bash
curl "https://api.synkora.io/api/v1/agents?page=1&limit=20&status=active"
```

## Response Format

### Success Response

```json
{
  "success": true,
  "data": {
    "id": "agent-123",
    "name": "My Agent",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### List Response

```json
{
  "success": true,
  "data": [
    { "id": "agent-1", "name": "Agent 1" },
    { "id": "agent-2", "name": "Agent 2" }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "totalPages": 3
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "name": ["Name is required"]
    }
  }
}
```

## HTTP Methods

| Method | Description |
|--------|-------------|
| `GET` | Retrieve resources |
| `POST` | Create new resources |
| `PUT` | Replace existing resources |
| `PATCH` | Partially update resources |
| `DELETE` | Delete resources |

## Common Parameters

### Pagination

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `limit` | integer | 20 | Items per page (max 100) |

### Filtering

| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Search query |
| `status` | string | Filter by status |
| `created_after` | datetime | Filter by creation date |
| `created_before` | datetime | Filter by creation date |

### Sorting

| Parameter | Type | Description |
|-----------|------|-------------|
| `sort_by` | string | Field to sort by |
| `sort_order` | string | `asc` or `desc` |

## API Endpoints Summary

### Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/agents` | List agents |
| `POST` | `/agents` | Create agent |
| `GET` | `/agents/{id}` | Get agent |
| `PATCH` | `/agents/{id}` | Update agent |
| `DELETE` | `/agents/{id}` | Delete agent |
| `POST` | `/agents/{id}/chat` | Chat with agent |

### Knowledge Bases

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/knowledge-bases` | List knowledge bases |
| `POST` | `/knowledge-bases` | Create knowledge base |
| `GET` | `/knowledge-bases/{id}` | Get knowledge base |
| `POST` | `/knowledge-bases/{id}/documents` | Upload document |
| `POST` | `/knowledge-bases/{id}/search` | Search knowledge base |

### Conversations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/conversations` | List conversations |
| `GET` | `/conversations/{id}` | Get conversation |
| `GET` | `/conversations/{id}/messages` | Get messages |
| `DELETE` | `/conversations/{id}` | Delete conversation |

### Billing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/billing/subscription` | Get subscription |
| `GET` | `/billing/credits` | Get credit balance |
| `GET` | `/billing/usage` | Get usage statistics |

## Rate Limits

| Plan | Requests/minute | Requests/hour |
|------|-----------------|---------------|
| Free | 60 | 1,000 |
| Pro | 300 | 10,000 |
| Enterprise | Custom | Custom |

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 299
X-RateLimit-Reset: 1234567890
```

## Versioning

The API version is included in the URL path (`/api/v1/`). We maintain backward compatibility within major versions.

## SDKs

Official SDKs are available:

- [TypeScript/JavaScript SDK](/docs/sdk/typescript/installation)
- [Python SDK](/docs/sdk/python/installation)

## OpenAPI Specification

Download the OpenAPI specification:

```bash
curl https://api.synkora.io/openapi.json -o openapi.json
```

Or view interactive documentation:

- **Swagger UI**: https://api.synkora.io/docs
- **ReDoc**: https://api.synkora.io/redoc
