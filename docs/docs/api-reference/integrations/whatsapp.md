---
sidebar_position: 3
---

# WhatsApp Integration API

Deploy agents on WhatsApp Business API.

## Create WhatsApp Integration

```http
POST /api/v1/integrations/whatsapp
```

### Request Body

```json
{
  "agent_id": "agent-123",
  "phone_number_id": "123456789",
  "access_token": "your-whatsapp-access-token",
  "verify_token": "your-webhook-verify-token",
  "config": {
    "welcome_message": "Hello! How can I help you?",
    "business_hours": {
      "enabled": true,
      "timezone": "America/New_York",
      "hours": {
        "monday": { "start": "09:00", "end": "17:00" },
        "tuesday": { "start": "09:00", "end": "17:00" }
      },
      "away_message": "We're currently offline. We'll respond during business hours."
    }
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "wa-int-123",
    "agent_id": "agent-123",
    "phone_number": "+1234567890",
    "status": "active",
    "webhook_url": "https://api.synkora.io/webhooks/whatsapp/wa-int-123",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Send Message

```http
POST /api/v1/integrations/whatsapp/{integration_id}/send
```

### Request Body

```json
{
  "to": "+1234567890",
  "type": "text",
  "text": {
    "body": "Hello from Synkora!"
  }
}
```

### Send Template Message

```json
{
  "to": "+1234567890",
  "type": "template",
  "template": {
    "name": "hello_world",
    "language": { "code": "en_US" }
  }
}
```

---

## Webhook Events

| Event | Description |
|-------|-------------|
| `messages` | Incoming message |
| `statuses` | Message delivery status |
