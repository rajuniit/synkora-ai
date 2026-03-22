---
sidebar_position: 5
---

# Agent Knowledge Bases API

Manage knowledge bases connected to an agent.

## List Connected Knowledge Bases

```http
GET /api/v1/agents/{agent_id}/knowledge-bases
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "kb-123",
      "name": "Product Documentation",
      "document_count": 50,
      "search_config": {
        "top_k": 5,
        "threshold": 0.7,
        "search_type": "hybrid"
      },
      "connected_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## Connect Knowledge Base

```http
POST /api/v1/agents/{agent_id}/knowledge-bases
```

### Request Body

```json
{
  "knowledge_base_id": "kb-123",
  "search_config": {
    "top_k": 5,
    "threshold": 0.7,
    "search_type": "hybrid"
  }
}
```

### Search Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `top_k` | integer | 5 | Number of results to retrieve |
| `threshold` | number | 0.7 | Minimum similarity score |
| `search_type` | string | `semantic` | `semantic`, `keyword`, or `hybrid` |
| `reranking` | boolean | false | Enable result reranking |

### Response

```json
{
  "success": true,
  "data": {
    "agent_id": "agent-456",
    "knowledge_base_id": "kb-123",
    "search_config": {
      "top_k": 5,
      "threshold": 0.7,
      "search_type": "hybrid"
    },
    "connected_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Update Search Configuration

```http
PATCH /api/v1/agents/{agent_id}/knowledge-bases/{kb_id}
```

### Request Body

```json
{
  "search_config": {
    "top_k": 10,
    "threshold": 0.8
  }
}
```

---

## Disconnect Knowledge Base

```http
DELETE /api/v1/agents/{agent_id}/knowledge-bases/{kb_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "message": "Knowledge base disconnected successfully"
  }
}
```

---

## Test Search

Test knowledge base search without a full chat:

```http
POST /api/v1/agents/{agent_id}/knowledge-bases/search
```

### Request Body

```json
{
  "query": "How do I reset my password?",
  "knowledge_base_ids": ["kb-123"],
  "top_k": 5
}
```

### Response

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "content": "To reset your password, click on 'Forgot Password'...",
        "score": 0.92,
        "knowledge_base_id": "kb-123",
        "document_id": "doc-789",
        "document_name": "user-guide.pdf",
        "metadata": {
          "page": 15,
          "section": "Account Settings"
        }
      }
    ]
  }
}
```
