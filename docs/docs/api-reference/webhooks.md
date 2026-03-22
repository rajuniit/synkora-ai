---
sidebar_position: 8
---

# Webhooks

Subscribe to events and receive real-time notifications.

## Create Webhook

```http
POST /api/v1/webhooks
```

### Request Body

```json
{
  "url": "https://example.com/webhooks/synkora",
  "events": [
    "conversation.created",
    "conversation.message",
    "agent.updated"
  ],
  "secret": "your-webhook-secret"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "webhook-123",
    "url": "https://example.com/webhooks/synkora",
    "events": ["conversation.created", "conversation.message", "agent.updated"],
    "status": "active",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Available Events

### Agent Events

| Event | Description |
|-------|-------------|
| `agent.created` | Agent created |
| `agent.updated` | Agent configuration updated |
| `agent.deleted` | Agent deleted |

### Conversation Events

| Event | Description |
|-------|-------------|
| `conversation.created` | New conversation started |
| `conversation.message` | Message sent/received |
| `conversation.ended` | Conversation archived |

### Knowledge Base Events

| Event | Description |
|-------|-------------|
| `knowledge_base.created` | Knowledge base created |
| `knowledge_base.updated` | Knowledge base updated |
| `document.processed` | Document finished processing |
| `document.failed` | Document processing failed |

### Billing Events

| Event | Description |
|-------|-------------|
| `subscription.created` | New subscription |
| `subscription.updated` | Subscription changed |
| `subscription.cancelled` | Subscription cancelled |
| `credits.low` | Credits below threshold |
| `credits.depleted` | Credits exhausted |
| `invoice.created` | Invoice generated |
| `payment.failed` | Payment failed |

---

## Webhook Payload

```json
{
  "id": "evt-123",
  "event": "conversation.message",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "conversation_id": "conv-456",
    "message": {
      "id": "msg-789",
      "role": "user",
      "content": "Hello!"
    }
  }
}
```

---

## Webhook Signature

Verify webhook authenticity using the signature:

```
X-Webhook-Signature: sha256=abc123...
```

### Verification (Node.js)

```javascript
const crypto = require('crypto');

function verifySignature(payload, signature, secret) {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  return `sha256=${expected}` === signature;
}
```

### Verification (Python)

```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return f"sha256={expected}" == signature
```

---

## List Webhooks

```http
GET /api/v1/webhooks
```

---

## Get Webhook

```http
GET /api/v1/webhooks/{webhook_id}
```

---

## Update Webhook

```http
PATCH /api/v1/webhooks/{webhook_id}
```

### Request Body

```json
{
  "events": ["conversation.message"],
  "status": "paused"
}
```

---

## Delete Webhook

```http
DELETE /api/v1/webhooks/{webhook_id}
```

---

## Test Webhook

```http
POST /api/v1/webhooks/{webhook_id}/test
```

Sends a test event to the webhook URL.

---

## Webhook Logs

```http
GET /api/v1/webhooks/{webhook_id}/logs
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "log-123",
      "event": "conversation.message",
      "status_code": 200,
      "response_time_ms": 150,
      "success": true,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## Retry Policy

Failed webhooks are retried with exponential backoff:

| Attempt | Delay |
|---------|-------|
| 1 | Immediate |
| 2 | 1 minute |
| 3 | 5 minutes |
| 4 | 30 minutes |
| 5 | 2 hours |

After 5 failed attempts, the webhook is paused.
