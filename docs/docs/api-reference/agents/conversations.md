---
sidebar_position: 3
---

# Conversations API

Manage conversations between users and agents.

## List Conversations

```http
GET /api/v1/conversations
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `agent_id` | string | Filter by agent |
| `user_id` | string | Filter by user |
| `status` | string | `active`, `archived` |
| `start_date` | datetime | Filter by date range |
| `end_date` | datetime | Filter by date range |
| `page` | integer | Page number |
| `limit` | integer | Items per page |

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "conv-123",
      "agent_id": "agent-456",
      "status": "active",
      "message_count": 15,
      "last_message_at": "2024-01-15T10:30:00Z",
      "metadata": {
        "user_id": "user-789",
        "channel": "web"
      },
      "created_at": "2024-01-15T09:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

---

## Get Conversation

```http
GET /api/v1/conversations/{conversation_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "conv-123",
    "agent_id": "agent-456",
    "status": "active",
    "message_count": 15,
    "metadata": {
      "user_id": "user-789",
      "channel": "web"
    },
    "summary": "Customer asked about return policy and shipping times.",
    "created_at": "2024-01-15T09:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Get Messages

```http
GET /api/v1/conversations/{conversation_id}/messages
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Messages per page (default: 50) |
| `before` | string | Cursor for pagination |
| `after` | string | Cursor for pagination |

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "msg-001",
      "role": "user",
      "content": "Hello, I need help",
      "created_at": "2024-01-15T09:00:00Z"
    },
    {
      "id": "msg-002",
      "role": "assistant",
      "content": "Hi! How can I help you today?",
      "citations": [],
      "tool_calls": [],
      "created_at": "2024-01-15T09:00:01Z"
    }
  ],
  "pagination": {
    "has_more": true,
    "next_cursor": "msg-010"
  }
}
```

---

## Create Conversation

```http
POST /api/v1/conversations
```

### Request Body

```json
{
  "agent_id": "agent-456",
  "metadata": {
    "user_id": "user-789",
    "channel": "web",
    "session_id": "session-abc"
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "conv-123",
    "agent_id": "agent-456",
    "status": "active",
    "created_at": "2024-01-15T09:00:00Z"
  }
}
```

---

## Update Conversation

```http
PATCH /api/v1/conversations/{conversation_id}
```

### Request Body

```json
{
  "metadata": {
    "priority": "high",
    "tags": ["urgent", "billing"]
  }
}
```

---

## Archive Conversation

```http
POST /api/v1/conversations/{conversation_id}/archive
```

### Response

```json
{
  "success": true,
  "data": {
    "message": "Conversation archived successfully"
  }
}
```

---

## Delete Conversation

```http
DELETE /api/v1/conversations/{conversation_id}
```

Permanently deletes the conversation and all messages.

### Response

```json
{
  "success": true,
  "data": {
    "message": "Conversation deleted successfully"
  }
}
```

---

## Export Conversation

```http
GET /api/v1/conversations/{conversation_id}/export
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `format` | string | `json`, `csv`, `txt` |

### Response

Returns the conversation in the requested format.

---

## Conversation Analytics

```http
GET /api/v1/conversations/{conversation_id}/analytics
```

### Response

```json
{
  "success": true,
  "data": {
    "message_count": 15,
    "user_messages": 8,
    "assistant_messages": 7,
    "duration_seconds": 1800,
    "avg_response_time_ms": 1200,
    "tool_calls": 3,
    "rag_queries": 2,
    "tokens_used": {
      "prompt": 5000,
      "completion": 2500,
      "total": 7500
    },
    "sentiment": "positive"
  }
}
```
