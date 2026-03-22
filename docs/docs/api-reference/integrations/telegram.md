---
sidebar_position: 2
---

# Telegram Integration API

Deploy and manage Telegram bot integrations.

## Create Telegram Integration

```http
POST /api/v1/integrations/telegram
```

### Request Body

```json
{
  "agent_id": "agent-123",
  "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
  "config": {
    "welcome_message": "Hello! How can I help you?",
    "allowed_users": [],
    "commands": [
      {
        "command": "start",
        "description": "Start conversation"
      },
      {
        "command": "help",
        "description": "Get help"
      }
    ]
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "tg-int-123",
    "agent_id": "agent-123",
    "bot_username": "@my_synkora_bot",
    "status": "active",
    "webhook_url": "https://api.synkora.io/webhooks/telegram/tg-int-123",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Get Telegram Integration

```http
GET /api/v1/integrations/telegram/{integration_id}
```

---

## Update Telegram Integration

```http
PATCH /api/v1/integrations/telegram/{integration_id}
```

---

## Delete Telegram Integration

```http
DELETE /api/v1/integrations/telegram/{integration_id}
```

---

## Set Bot Commands

```http
POST /api/v1/integrations/telegram/{integration_id}/commands
```

### Request Body

```json
{
  "commands": [
    { "command": "start", "description": "Start conversation" },
    { "command": "help", "description": "Get help" },
    { "command": "reset", "description": "Reset conversation" }
  ]
}
```

---

## Send Message

```http
POST /api/v1/integrations/telegram/{integration_id}/send
```

### Request Body

```json
{
  "chat_id": 123456789,
  "text": "Hello from Synkora!",
  "parse_mode": "Markdown",
  "reply_markup": {
    "inline_keyboard": [
      [
        { "text": "Option 1", "callback_data": "opt1" },
        { "text": "Option 2", "callback_data": "opt2" }
      ]
    ]
  }
}
```
