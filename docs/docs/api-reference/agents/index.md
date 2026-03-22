---
sidebar_position: 1
---

# Agents API

Manage AI agents through the API.

## List Agents

```http
GET /api/v1/agents
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number (default: 1) |
| `limit` | integer | Items per page (default: 20, max: 100) |
| `search` | string | Search by name |
| `status` | string | Filter by status (`active`, `inactive`) |

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "agent-123",
      "name": "Support Bot",
      "slug": "support-bot",
      "description": "Customer support assistant",
      "model_name": "gpt-4o",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5,
    "totalPages": 1
  }
}
```

### Example

```bash
curl -X GET "https://api.synkora.io/api/v1/agents?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Create Agent

```http
POST /api/v1/agents
```

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Agent name |
| `slug` | string | No | URL-friendly identifier |
| `description` | string | No | Agent description |
| `model_name` | string | Yes | LLM model to use |
| `system_prompt` | string | No | System instructions |
| `temperature` | number | No | Response randomness (0-2) |
| `max_tokens` | integer | No | Max response tokens |
| `top_p` | number | No | Nucleus sampling (0-1) |

### Request

```json
{
  "name": "Support Bot",
  "slug": "support-bot",
  "description": "Customer support assistant",
  "model_name": "gpt-4o",
  "system_prompt": "You are a helpful customer support agent...",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "agent-123",
    "name": "Support Bot",
    "slug": "support-bot",
    "description": "Customer support assistant",
    "model_name": "gpt-4o",
    "system_prompt": "You are a helpful customer support agent...",
    "temperature": 0.7,
    "max_tokens": 1000,
    "status": "active",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Example

```bash
curl -X POST "https://api.synkora.io/api/v1/agents" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Support Bot",
    "model_name": "gpt-4o",
    "system_prompt": "You are a helpful assistant."
  }'
```

---

## Get Agent

```http
GET /api/v1/agents/{agent_id}
```

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `agent_id` | string | Agent ID or slug |

### Response

```json
{
  "success": true,
  "data": {
    "id": "agent-123",
    "name": "Support Bot",
    "slug": "support-bot",
    "description": "Customer support assistant",
    "model_name": "gpt-4o",
    "system_prompt": "You are a helpful customer support agent...",
    "temperature": 0.7,
    "max_tokens": 1000,
    "tools": ["search_knowledge_base", "web_search"],
    "knowledge_bases": ["kb-456"],
    "status": "active",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Update Agent

```http
PATCH /api/v1/agents/{agent_id}
```

### Request Body

All fields are optional. Only provided fields will be updated.

```json
{
  "name": "Updated Bot Name",
  "temperature": 0.5,
  "system_prompt": "Updated system prompt..."
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "agent-123",
    "name": "Updated Bot Name",
    "temperature": 0.5,
    "system_prompt": "Updated system prompt...",
    "updated_at": "2024-01-16T10:30:00Z"
  }
}
```

---

## Delete Agent

```http
DELETE /api/v1/agents/{agent_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "message": "Agent deleted successfully"
  }
}
```

---

## Clone Agent

```http
POST /api/v1/agents/{agent_id}/clone
```

### Request Body

```json
{
  "name": "Support Bot (Copy)",
  "slug": "support-bot-copy"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "agent-789",
    "name": "Support Bot (Copy)",
    "slug": "support-bot-copy",
    "cloned_from": "agent-123"
  }
}
```

---

## Supported Models

| Provider | Model | ID |
|----------|-------|----|
| OpenAI | GPT-4o | `gpt-4o` |
| OpenAI | GPT-4o Mini | `gpt-4o-mini` |
| OpenAI | GPT-4 Turbo | `gpt-4-turbo` |
| OpenAI | GPT-3.5 Turbo | `gpt-3.5-turbo` |
| Anthropic | Claude 3.5 Sonnet | `claude-3-5-sonnet-20241022` |
| Anthropic | Claude 3 Opus | `claude-3-opus-20240229` |
| Anthropic | Claude 3 Haiku | `claude-3-haiku-20240307` |
| Google | Gemini 1.5 Pro | `gemini-1.5-pro` |
| Google | Gemini 1.5 Flash | `gemini-1.5-flash` |

---

## Error Codes

| Code | Description |
|------|-------------|
| `AGENT_NOT_FOUND` | Agent does not exist |
| `AGENT_LIMIT_EXCEEDED` | Maximum agents reached for plan |
| `INVALID_MODEL` | Model name is not supported |
| `SLUG_ALREADY_EXISTS` | Agent with this slug already exists |
