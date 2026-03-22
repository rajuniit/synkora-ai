---
sidebar_position: 1
---

# Slack Integration API

Deploy and manage Slack bot integrations.

## Create Slack Integration

```http
POST /api/v1/integrations/slack
```

### Request Body

```json
{
  "agent_id": "agent-123",
  "bot_token": "xoxb-your-bot-token",
  "signing_secret": "your-signing-secret",
  "config": {
    "respond_to_mentions": true,
    "respond_in_threads": true,
    "allowed_channels": ["C123456", "C789012"],
    "dm_enabled": true
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "slack-int-123",
    "agent_id": "agent-123",
    "workspace_id": "T12345",
    "workspace_name": "Acme Corp",
    "bot_user_id": "U12345",
    "status": "active",
    "webhook_url": "https://api.synkora.io/webhooks/slack/slack-int-123",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Get Slack Integration

```http
GET /api/v1/integrations/slack/{integration_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "slack-int-123",
    "agent_id": "agent-123",
    "workspace_id": "T12345",
    "workspace_name": "Acme Corp",
    "bot_user_id": "U12345",
    "status": "active",
    "config": {
      "respond_to_mentions": true,
      "respond_in_threads": true,
      "dm_enabled": true
    },
    "stats": {
      "total_messages": 1500,
      "active_channels": 5,
      "last_message_at": "2024-01-15T10:30:00Z"
    }
  }
}
```

---

## Update Slack Integration

```http
PATCH /api/v1/integrations/slack/{integration_id}
```

### Request Body

```json
{
  "config": {
    "respond_to_mentions": false,
    "allowed_channels": ["C123456"]
  }
}
```

---

## Delete Slack Integration

```http
DELETE /api/v1/integrations/slack/{integration_id}
```

---

## List Slack Channels

```http
GET /api/v1/integrations/slack/{integration_id}/channels
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "C123456",
      "name": "general",
      "is_member": true,
      "message_count": 150
    }
  ]
}
```

---

## OAuth Flow

### Initiate OAuth

```http
GET /api/v1/integrations/slack/oauth/authorize
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `agent_id` | string | Agent to connect |
| `redirect_uri` | string | Callback URL |

Redirects to Slack OAuth consent page.

### OAuth Callback

```http
GET /api/v1/integrations/slack/oauth/callback
```

Handles Slack OAuth callback and creates integration.

---

## Webhook Events

Configure Slack event subscriptions to:

```
https://api.synkora.io/webhooks/slack/{integration_id}
```

### Supported Events

| Event | Description |
|-------|-------------|
| `message` | Message in channel |
| `app_mention` | Bot mentioned |
| `im` | Direct message |

---

## Send Message

```http
POST /api/v1/integrations/slack/{integration_id}/send
```

### Request Body

```json
{
  "channel": "C123456",
  "text": "Hello from Synkora!",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Hello!* This is a formatted message."
      }
    }
  ]
}
```
