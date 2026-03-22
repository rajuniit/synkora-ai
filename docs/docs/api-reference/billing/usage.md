---
sidebar_position: 3
---

# Usage API

Track and analyze usage across your organization.

## Get Usage Summary

```http
GET /api/v1/billing/usage
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | datetime | Period start (default: current month) |
| `end_date` | datetime | Period end |
| `granularity` | string | `daily`, `weekly`, `monthly` |

### Response

```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-31T23:59:59Z"
    },
    "summary": {
      "total_credits": 3500,
      "total_tokens": 1250000,
      "total_conversations": 500,
      "total_messages": 2500,
      "api_calls": 15000
    },
    "by_model": [
      {
        "model": "gpt-4o",
        "credits": 2500,
        "tokens": {
          "input": 200000,
          "output": 50000
        }
      },
      {
        "model": "gpt-3.5-turbo",
        "credits": 1000,
        "tokens": {
          "input": 800000,
          "output": 200000
        }
      }
    ],
    "by_operation": {
      "chat": 3000,
      "embedding": 300,
      "tools": 200
    }
  }
}
```

---

## Usage by Agent

```http
GET /api/v1/billing/usage/by-agent
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "agent_id": "agent-123",
      "agent_name": "Support Bot",
      "credits": 2000,
      "tokens": 750000,
      "conversations": 300,
      "messages": 1500,
      "percentage": 57.1
    },
    {
      "agent_id": "agent-456",
      "agent_name": "Sales Bot",
      "credits": 1500,
      "tokens": 500000,
      "conversations": 200,
      "messages": 1000,
      "percentage": 42.9
    }
  ]
}
```

---

## Usage Time Series

```http
GET /api/v1/billing/usage/timeseries
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | datetime | Period start |
| `end_date` | datetime | Period end |
| `granularity` | string | `hourly`, `daily`, `weekly` |
| `metric` | string | `credits`, `tokens`, `conversations` |

### Response

```json
{
  "success": true,
  "data": {
    "metric": "credits",
    "granularity": "daily",
    "data": [
      { "date": "2024-01-01", "value": 100 },
      { "date": "2024-01-02", "value": 150 },
      { "date": "2024-01-03", "value": 120 }
    ]
  }
}
```

---

## Usage by User

```http
GET /api/v1/billing/usage/by-user
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "user_id": "user-123",
      "email": "john@example.com",
      "credits": 500,
      "conversations": 50,
      "messages": 250
    }
  ]
}
```

---

## Export Usage Data

```http
POST /api/v1/billing/usage/export
```

### Request Body

```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "format": "csv",
  "include": ["conversations", "tokens", "credits"]
}
```

### Response

```json
{
  "success": true,
  "data": {
    "job_id": "export-123",
    "status": "processing",
    "download_url": null
  }
}
```

### Check Export Status

```http
GET /api/v1/billing/usage/export/{job_id}
```

```json
{
  "success": true,
  "data": {
    "job_id": "export-123",
    "status": "completed",
    "download_url": "https://storage.synkora.io/exports/export-123.csv",
    "expires_at": "2024-01-20T00:00:00Z"
  }
}
```

---

## Set Usage Budget

```http
POST /api/v1/billing/budget
```

### Request Body

```json
{
  "monthly_limit": 10000,
  "alerts": [
    {
      "percentage": 50,
      "notify_emails": ["finance@example.com"]
    },
    {
      "percentage": 80,
      "notify_emails": ["finance@example.com", "admin@example.com"]
    },
    {
      "percentage": 100,
      "action": "notify"
    }
  ]
}
```

### Actions

| Action | Description |
|--------|-------------|
| `notify` | Send notification only |
| `suspend` | Suspend API access |
| `throttle` | Reduce rate limits |

---

## Usage Forecast

```http
GET /api/v1/billing/usage/forecast
```

### Response

```json
{
  "success": true,
  "data": {
    "current_month": {
      "used": 2500,
      "projected": 4500,
      "budget": 5000,
      "on_track": true
    },
    "daily_average": 150,
    "trend": "increasing",
    "confidence": 0.85
  }
}
```
