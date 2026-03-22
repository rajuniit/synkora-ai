---
sidebar_position: 4
---

# Microsoft Teams Integration API

Deploy agents on Microsoft Teams.

## Create Teams Integration

```http
POST /api/v1/integrations/teams
```

### Request Body

```json
{
  "agent_id": "agent-123",
  "app_id": "your-teams-app-id",
  "app_password": "your-teams-app-password",
  "tenant_id": "your-azure-tenant-id",
  "config": {
    "respond_to_mentions": true,
    "respond_in_channels": true,
    "direct_messages": true
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "teams-int-123",
    "agent_id": "agent-123",
    "app_id": "your-teams-app-id",
    "status": "active",
    "messaging_endpoint": "https://api.synkora.io/webhooks/teams/teams-int-123/messages",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Send Proactive Message

```http
POST /api/v1/integrations/teams/{integration_id}/send
```

### Request Body

```json
{
  "conversation_id": "19:xxx@thread.tacv2",
  "message": {
    "type": "message",
    "text": "Hello from Synkora!",
    "attachments": [
      {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
          "type": "AdaptiveCard",
          "body": [
            {
              "type": "TextBlock",
              "text": "Hello World"
            }
          ]
        }
      }
    ]
  }
}
```

---

## Bot Framework Setup

Configure your Teams bot to send messages to:

```
https://api.synkora.io/webhooks/teams/{integration_id}/messages
```
