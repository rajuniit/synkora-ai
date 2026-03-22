---
sidebar_position: 1
---

# Subscriptions API

Manage subscription plans and billing.

## Get Current Subscription

```http
GET /api/v1/billing/subscription
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "sub-123",
    "plan": "pro",
    "status": "active",
    "current_period_start": "2024-01-01T00:00:00Z",
    "current_period_end": "2024-02-01T00:00:00Z",
    "cancel_at_period_end": false,
    "features": {
      "max_agents": 20,
      "max_knowledge_bases": 10,
      "max_users": 20,
      "included_credits": 5000,
      "support_level": "email"
    },
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

---

## List Available Plans

```http
GET /api/v1/billing/plans
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "free",
      "name": "Free",
      "price_monthly": 0,
      "price_yearly": 0,
      "features": {
        "max_agents": 3,
        "max_knowledge_bases": 1,
        "max_users": 3,
        "included_credits": 100
      }
    },
    {
      "id": "pro",
      "name": "Pro",
      "price_monthly": 49,
      "price_yearly": 490,
      "features": {
        "max_agents": 20,
        "max_knowledge_bases": 10,
        "max_users": 20,
        "included_credits": 5000
      }
    },
    {
      "id": "enterprise",
      "name": "Enterprise",
      "price_monthly": null,
      "price_yearly": null,
      "features": {
        "max_agents": "unlimited",
        "max_knowledge_bases": "unlimited",
        "max_users": "unlimited",
        "included_credits": "custom",
        "sso": true,
        "sla": "99.9%"
      }
    }
  ]
}
```

---

## Update Subscription

```http
POST /api/v1/billing/subscription
```

### Request Body

```json
{
  "plan": "pro",
  "billing_cycle": "yearly"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "sub-123",
    "plan": "pro",
    "status": "active",
    "billing_cycle": "yearly",
    "next_billing_date": "2025-01-01T00:00:00Z"
  }
}
```

---

## Cancel Subscription

```http
POST /api/v1/billing/subscription/cancel
```

### Request Body

```json
{
  "cancel_at_period_end": true,
  "reason": "Not using all features"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "status": "active",
    "cancel_at_period_end": true,
    "cancel_at": "2024-02-01T00:00:00Z",
    "message": "Your subscription will be cancelled at the end of the billing period"
  }
}
```

---

## Reactivate Subscription

```http
POST /api/v1/billing/subscription/reactivate
```

### Response

```json
{
  "success": true,
  "data": {
    "status": "active",
    "cancel_at_period_end": false,
    "message": "Subscription reactivated successfully"
  }
}
```

---

## Create Checkout Session

For Stripe-hosted checkout:

```http
POST /api/v1/billing/checkout
```

### Request Body

```json
{
  "plan": "pro",
  "billing_cycle": "monthly",
  "success_url": "https://app.example.com/billing?success=true",
  "cancel_url": "https://app.example.com/billing?cancelled=true"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "checkout_url": "https://checkout.stripe.com/c/pay/cs_xxx",
    "session_id": "cs_xxx"
  }
}
```

---

## Customer Portal

Access Stripe customer portal:

```http
POST /api/v1/billing/portal
```

### Request Body

```json
{
  "return_url": "https://app.example.com/billing"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "portal_url": "https://billing.stripe.com/p/session/xxx"
  }
}
```
