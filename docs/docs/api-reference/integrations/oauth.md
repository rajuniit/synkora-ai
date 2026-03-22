---
sidebar_position: 5
---

# OAuth Integrations API

Manage OAuth connections for agent tools.

## List OAuth Providers

```http
GET /api/v1/integrations/oauth/providers
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "provider": "google",
      "name": "Google",
      "tools": ["google_calendar", "google_drive", "google_gmail"],
      "scopes_available": [
        "calendar.readonly",
        "calendar.events",
        "drive.readonly",
        "gmail.readonly"
      ]
    },
    {
      "provider": "github",
      "name": "GitHub",
      "tools": ["github_repos", "github_issues", "github_prs"],
      "scopes_available": ["repo", "issues", "pull_requests"]
    },
    {
      "provider": "slack",
      "name": "Slack",
      "tools": ["slack_channels", "slack_messages"],
      "scopes_available": ["channels:read", "chat:write"]
    },
    {
      "provider": "jira",
      "name": "Jira",
      "tools": ["jira_issues", "jira_projects"],
      "scopes_available": ["read:jira-work", "write:jira-work"]
    }
  ]
}
```

---

## Initiate OAuth Connection

```http
POST /api/v1/integrations/oauth/{provider}/authorize
```

### Request Body

```json
{
  "agent_id": "agent-123",
  "scopes": ["calendar.readonly", "calendar.events"],
  "redirect_uri": "https://app.example.com/oauth/callback"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
    "state": "oauth-state-123"
  }
}
```

---

## OAuth Callback

```http
POST /api/v1/integrations/oauth/{provider}/callback
```

### Request Body

```json
{
  "code": "authorization-code",
  "state": "oauth-state-123"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "connection_id": "oauth-conn-123",
    "provider": "google",
    "agent_id": "agent-123",
    "account_email": "user@gmail.com",
    "scopes": ["calendar.readonly", "calendar.events"],
    "status": "active"
  }
}
```

---

## List OAuth Connections

```http
GET /api/v1/integrations/oauth/connections
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `agent_id` | string | Filter by agent |
| `provider` | string | Filter by provider |

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "oauth-conn-123",
      "provider": "google",
      "agent_id": "agent-123",
      "account_email": "user@gmail.com",
      "scopes": ["calendar.readonly"],
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## Revoke OAuth Connection

```http
DELETE /api/v1/integrations/oauth/connections/{connection_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "message": "OAuth connection revoked successfully"
  }
}
```

---

## Refresh Token

Manually refresh an OAuth token:

```http
POST /api/v1/integrations/oauth/connections/{connection_id}/refresh
```

### Response

```json
{
  "success": true,
  "data": {
    "status": "active",
    "expires_at": "2024-01-16T10:30:00Z"
  }
}
```
