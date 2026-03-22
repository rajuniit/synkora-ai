---
sidebar_position: 4
---

# Agent Tools API

Manage tools enabled for an agent.

## List Agent Tools

```http
GET /api/v1/agents/{agent_id}/tools
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "name": "search_knowledge_base",
      "type": "builtin",
      "enabled": true,
      "config": {
        "top_k": 5,
        "threshold": 0.7
      }
    },
    {
      "name": "web_search",
      "type": "builtin",
      "enabled": true,
      "config": {}
    },
    {
      "name": "create_ticket",
      "type": "custom",
      "enabled": true,
      "config": {
        "webhook_url": "https://api.example.com/tickets"
      }
    }
  ]
}
```

---

## Enable Tool

```http
POST /api/v1/agents/{agent_id}/tools
```

### Request Body

```json
{
  "name": "web_search",
  "config": {
    "max_results": 5
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "name": "web_search",
    "type": "builtin",
    "enabled": true,
    "config": {
      "max_results": 5
    }
  }
}
```

---

## Update Tool Configuration

```http
PATCH /api/v1/agents/{agent_id}/tools/{tool_name}
```

### Request Body

```json
{
  "config": {
    "max_results": 10
  }
}
```

---

## Disable Tool

```http
DELETE /api/v1/agents/{agent_id}/tools/{tool_name}
```

### Response

```json
{
  "success": true,
  "data": {
    "message": "Tool disabled successfully"
  }
}
```

---

## Register Custom Tool

```http
POST /api/v1/agents/{agent_id}/tools/custom
```

### Request Body

```json
{
  "name": "get_order_status",
  "description": "Get the status of a customer order",
  "parameters": {
    "type": "object",
    "properties": {
      "order_id": {
        "type": "string",
        "description": "The order ID to look up"
      }
    },
    "required": ["order_id"]
  },
  "handler": {
    "type": "webhook",
    "url": "https://api.example.com/orders/status",
    "method": "POST",
    "headers": {
      "Authorization": "Bearer ${ORDERS_API_KEY}"
    }
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "name": "get_order_status",
    "type": "custom",
    "enabled": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Available Built-in Tools

| Tool | Description |
|------|-------------|
| `search_knowledge_base` | Search connected knowledge bases |
| `web_search` | Search the web |
| `fetch_url` | Fetch content from a URL |
| `code_execution` | Execute Python/JavaScript code |
| `image_generation` | Generate images with DALL-E |

---

## OAuth Tools

Enable OAuth-connected tools:

```http
POST /api/v1/agents/{agent_id}/tools/oauth
```

### Request Body

```json
{
  "provider": "google",
  "tools": ["google_calendar", "google_drive"],
  "scopes": [
    "calendar.readonly",
    "calendar.events",
    "drive.readonly"
  ]
}
```

### Available OAuth Tools

| Provider | Tools |
|----------|-------|
| Google | `google_calendar`, `google_drive`, `google_gmail` |
| GitHub | `github_repos`, `github_issues`, `github_prs` |
| Slack | `slack_channels`, `slack_messages` |
| Jira | `jira_issues`, `jira_projects` |

---

## MCP Server Tools

Connect MCP (Model Context Protocol) servers:

```http
POST /api/v1/agents/{agent_id}/tools/mcp
```

### Request Body

```json
{
  "name": "database-tools",
  "url": "http://localhost:3001/mcp",
  "transport": "http"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "name": "database-tools",
    "status": "connected",
    "tools": [
      "query_database",
      "list_tables",
      "get_schema"
    ]
  }
}
```
