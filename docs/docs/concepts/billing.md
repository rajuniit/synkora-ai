---
sidebar_position: 6
---

# Billing

Synkora provides a flexible credit-based billing system with subscription plans and usage tracking.

## Billing Model

Synkora uses a hybrid billing model:

- **Subscriptions**: Monthly/annual plans with included features
- **Credits**: Consumable units for LLM usage
- **Add-ons**: Optional features and capacity

```
┌─────────────────────────────────────────────────────────┐
│                    Billing Structure                     │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Subscription Plan                   │    │
│  │  • Base features (agents, KBs, users)           │    │
│  │  • Monthly credit allowance                      │    │
│  │  • Support level                                 │    │
│  └─────────────────────────────────────────────────┘    │
│                          +                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Credit Consumption                  │    │
│  │  • LLM API calls                                │    │
│  │  • Embedding generation                          │    │
│  │  • Tool executions                              │    │
│  └─────────────────────────────────────────────────┘    │
│                          +                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │                  Add-ons                         │    │
│  │  • Extra credits                                │    │
│  │  • Additional storage                           │    │
│  │  • Premium support                              │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Subscription Plans

### Available Plans

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Agents | 3 | 20 | Unlimited |
| Knowledge Bases | 1 | 10 | Unlimited |
| Documents | 100 | 1000 | Unlimited |
| Monthly Credits | 100 | 5000 | Custom |
| Users | 3 | 20 | Unlimited |
| Support | Community | Email | Dedicated |
| SSO | - | - | Yes |
| Custom Domain | - | - | Yes |
| SLA | - | 99.5% | 99.9% |

### Managing Subscriptions

```typescript
// Get current subscription
const subscription = await synkora.billing.getSubscription();

console.log(subscription);
// {
//   plan: 'pro',
//   status: 'active',
//   currentPeriodEnd: '2024-02-15',
//   credits: {
//     included: 5000,
//     used: 1500,
//     remaining: 3500,
//   },
// }

// Upgrade plan
await synkora.billing.updateSubscription({
  plan: 'enterprise',
});

// Cancel subscription
await synkora.billing.cancelSubscription({
  cancelAtPeriodEnd: true,
});
```

## Credits

### What Are Credits?

Credits are Synkora's unit of consumption:

| Operation | Credit Cost |
|-----------|-------------|
| GPT-4o message (1K tokens) | 10 credits |
| GPT-3.5-turbo message (1K tokens) | 1 credit |
| Claude 3.5 Sonnet message (1K tokens) | 8 credits |
| Embedding generation (1K tokens) | 0.1 credits |
| Tool execution | 0.5 credits |
| Web search | 1 credit |

### Credit Balance

```typescript
// Check credit balance
const balance = await synkora.billing.getCredits();

console.log(balance);
// {
//   total: 5000,
//   used: 1500,
//   remaining: 3500,
//   resetDate: '2024-02-01',
// }
```

### Purchase Additional Credits

```typescript
// Buy credit pack
await synkora.billing.purchaseCredits({
  amount: 5000,  // 5000 credits
  // Price: $50
});
```

### Credit Alerts

```typescript
// Set up low credit alert
await synkora.billing.setAlert({
  type: 'low_credits',
  threshold: 500,  // Alert when below 500 credits
  notifyEmails: ['admin@example.com'],
});
```

## Usage Tracking

### View Usage

```typescript
const usage = await synkora.billing.getUsage({
  startDate: '2024-01-01',
  endDate: '2024-01-31',
});

console.log(usage);
// {
//   summary: {
//     totalCredits: 3500,
//     totalTokens: 1250000,
//     totalConversations: 500,
//   },
//   byAgent: [
//     { agentId: 'agent-1', credits: 2000, tokens: 750000 },
//     { agentId: 'agent-2', credits: 1500, tokens: 500000 },
//   ],
//   byModel: [
//     { model: 'gpt-4o', credits: 2500, tokens: 250000 },
//     { model: 'gpt-3.5-turbo', credits: 1000, tokens: 1000000 },
//   ],
//   daily: [
//     { date: '2024-01-01', credits: 100, tokens: 35000 },
//     // ...
//   ],
// }
```

### Usage by Agent

```typescript
const agentUsage = await synkora.agents.getUsage(agentId, {
  startDate: '2024-01-01',
  endDate: '2024-01-31',
});

console.log(agentUsage);
// {
//   totalCredits: 2000,
//   totalTokens: 750000,
//   conversations: 300,
//   avgCreditsPerConversation: 6.7,
//   breakdown: {
//     llm: 1800,
//     rag: 100,
//     tools: 100,
//   },
// }
```

## Cost Optimization

### Model Selection

Choose cost-effective models:

```typescript
// Use cheaper models for simple tasks
const simpleAgent = await synkora.agents.create({
  name: 'FAQ Bot',
  modelName: 'gpt-3.5-turbo',  // 1 credit per 1K tokens
});

// Use powerful models for complex tasks
const complexAgent = await synkora.agents.create({
  name: 'Research Assistant',
  modelName: 'gpt-4o',  // 10 credits per 1K tokens
});
```

### Token Optimization

```typescript
// Configure response limits
await synkora.agents.update(agentId, {
  maxTokens: 500,  // Limit response length
  contextConfig: {
    maxMessages: 10,  // Limit context size
  },
});
```

### Caching

```typescript
// Enable response caching
await synkora.agents.update(agentId, {
  caching: {
    enabled: true,
    ttl: 3600,  // Cache for 1 hour
    similarityThreshold: 0.95,
  },
});
```

## Invoices and Payments

### Payment Methods

```typescript
// Add payment method
await synkora.billing.addPaymentMethod({
  type: 'card',
  token: 'stripe_token_xxx',
});

// Set default payment method
await synkora.billing.setDefaultPaymentMethod(paymentMethodId);
```

### Invoices

```typescript
// List invoices
const invoices = await synkora.billing.listInvoices({
  limit: 10,
});

// Download invoice PDF
const pdf = await synkora.billing.downloadInvoice(invoiceId);
```

### Billing Address

```typescript
await synkora.billing.updateBillingAddress({
  name: 'Acme Corp',
  addressLine1: '123 Main St',
  city: 'San Francisco',
  state: 'CA',
  postalCode: '94105',
  country: 'US',
});
```

## Enterprise Billing

### Custom Pricing

Enterprise customers can negotiate:

- Custom credit pricing
- Volume discounts
- Committed use discounts
- Custom payment terms

### Cost Allocation

```typescript
// Tag usage for cost allocation
await synkora.agents.update(agentId, {
  metadata: {
    costCenter: 'engineering',
    project: 'customer-support',
  },
});

// Get usage by cost center
const usage = await synkora.billing.getUsage({
  groupBy: 'costCenter',
});
```

### Budgets

```typescript
// Set budget limits
await synkora.billing.setBudget({
  monthly: 10000,  // $10,000 monthly limit
  alerts: [
    { percentage: 50, notifyEmails: ['finance@example.com'] },
    { percentage: 80, notifyEmails: ['finance@example.com', 'admin@example.com'] },
    { percentage: 100, action: 'notify' },  // or 'suspend'
  ],
});
```

## Webhooks

### Billing Events

```typescript
// Subscribe to billing webhooks
await synkora.webhooks.create({
  url: 'https://example.com/webhooks/billing',
  events: [
    'subscription.created',
    'subscription.updated',
    'subscription.cancelled',
    'credits.low',
    'credits.depleted',
    'invoice.created',
    'payment.failed',
  ],
});
```

### Event Payloads

```json
{
  "event": "credits.low",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "tenantId": "tenant-123",
    "remainingCredits": 450,
    "threshold": 500
  }
}
```

## Self-Hosted Billing

For self-hosted deployments, you can:

1. **Disable billing** - Use Synkora without billing
2. **Custom integration** - Integrate with your billing system
3. **Usage metering** - Export usage for external billing

```env
# Disable billing
BILLING_ENABLED=false

# Or custom integration
BILLING_WEBHOOK_URL=https://your-billing-system.com/webhook
```

## Best Practices

### Cost Management

1. **Monitor usage** - Regular usage reviews
2. **Set alerts** - Early warning for overages
3. **Right-size models** - Match model to task complexity
4. **Optimize prompts** - Shorter prompts = fewer tokens

### Planning

1. **Forecast usage** - Plan capacity needs
2. **Reserved credits** - Pre-purchase for discounts
3. **Annual plans** - Typically 20% savings

## Related Concepts

- [Multi-Tenancy](/docs/concepts/multi-tenancy) - Per-tenant billing
- [Agents](/docs/concepts/agents) - Agent configuration
