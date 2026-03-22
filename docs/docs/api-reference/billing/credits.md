---
sidebar_position: 2
---

# Credits API

Manage and monitor credit usage.

## Get Credit Balance

```http
GET /api/v1/billing/credits
```

### Response

```json
{
  "success": true,
  "data": {
    "total": 5000,
    "used": 1500,
    "remaining": 3500,
    "included_in_plan": 5000,
    "purchased": 0,
    "expires_at": null,
    "reset_date": "2024-02-01T00:00:00Z"
  }
}
```

---

## Purchase Credits

```http
POST /api/v1/billing/credits/purchase
```

### Request Body

```json
{
  "amount": 5000,
  "payment_method_id": "pm_xxx"
}
```

### Credit Packs

| Credits | Price |
|---------|-------|
| 1,000 | $10 |
| 5,000 | $45 |
| 10,000 | $80 |
| 50,000 | $350 |

### Response

```json
{
  "success": true,
  "data": {
    "transaction_id": "txn-123",
    "credits_purchased": 5000,
    "amount_charged": 4500,
    "new_balance": 8500
  }
}
```

---

## Credit History

```http
GET /api/v1/billing/credits/history
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | datetime | Filter start |
| `end_date` | datetime | Filter end |
| `type` | string | `usage`, `purchase`, `refund` |
| `page` | integer | Page number |

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "credit-001",
      "type": "usage",
      "amount": -10,
      "balance_after": 4990,
      "description": "Chat completion: gpt-4o",
      "metadata": {
        "agent_id": "agent-123",
        "conversation_id": "conv-456",
        "model": "gpt-4o",
        "tokens": 1500
      },
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": "credit-002",
      "type": "purchase",
      "amount": 5000,
      "balance_after": 5000,
      "description": "Credit purchase",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 500
  }
}
```

---

## Credit Consumption Rates

```http
GET /api/v1/billing/credits/rates
```

### Response

```json
{
  "success": true,
  "data": {
    "models": [
      {
        "model": "gpt-4o",
        "credits_per_1k_input_tokens": 5,
        "credits_per_1k_output_tokens": 15
      },
      {
        "model": "gpt-4o-mini",
        "credits_per_1k_input_tokens": 0.15,
        "credits_per_1k_output_tokens": 0.6
      },
      {
        "model": "gpt-3.5-turbo",
        "credits_per_1k_input_tokens": 0.5,
        "credits_per_1k_output_tokens": 1.5
      },
      {
        "model": "claude-3-5-sonnet",
        "credits_per_1k_input_tokens": 3,
        "credits_per_1k_output_tokens": 15
      }
    ],
    "operations": {
      "embedding": 0.02,
      "web_search": 1,
      "tool_execution": 0.5
    }
  }
}
```

---

## Set Credit Alert

```http
POST /api/v1/billing/credits/alerts
```

### Request Body

```json
{
  "threshold": 500,
  "notify_emails": ["admin@example.com", "billing@example.com"]
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "alert-123",
    "threshold": 500,
    "notify_emails": ["admin@example.com", "billing@example.com"],
    "enabled": true
  }
}
```

---

## Estimate Cost

Estimate credit cost before execution:

```http
POST /api/v1/billing/credits/estimate
```

### Request Body

```json
{
  "model": "gpt-4o",
  "prompt_tokens": 1000,
  "estimated_completion_tokens": 500
}
```

### Response

```json
{
  "success": true,
  "data": {
    "estimated_credits": 12.5,
    "breakdown": {
      "input": 5,
      "output": 7.5
    }
  }
}
```
