---
sidebar_position: 2
---

# Add Tools to Agents

Tools extend your agent's capabilities beyond conversation, enabling them to perform actions and retrieve external data.

## Understanding Tools

Tools allow agents to:

- Search the web
- Execute code
- Access external APIs
- Perform CRUD operations
- Interact with third-party services

## Enable Built-in Tools

### Web Search

Allow your agent to search the web:

```typescript
await synkora.agents.enableTool(agent.id, 'web_search', {
  maxResults: 5,
});
```

Test it:

```typescript
const response = await synkora.agents.chat(agent.id, {
  message: 'What are the latest news about AI?',
});
```

### Code Execution

Enable code execution in a sandbox:

```typescript
await synkora.agents.enableTool(agent.id, 'code_execution', {
  languages: ['python', 'javascript'],
  timeout: 30000,
});
```

Example prompt:

```
"Calculate the compound interest on $10,000 at 5% for 10 years"
```

### URL Fetching

Allow fetching content from URLs:

```typescript
await synkora.agents.enableTool(agent.id, 'fetch_url');
```

## Create Custom Tools

Build tools specific to your use case.

### Tool Definition

```typescript
const orderStatusTool = {
  name: 'get_order_status',
  description: 'Get the current status of a customer order by order ID',
  parameters: {
    type: 'object',
    properties: {
      order_id: {
        type: 'string',
        description: 'The unique order identifier (e.g., ORD-12345)',
      },
    },
    required: ['order_id'],
  },
};
```

### Register with Webhook Handler

```typescript
await synkora.agents.registerTool(agent.id, {
  ...orderStatusTool,
  handler: {
    type: 'webhook',
    url: 'https://api.yourcompany.com/orders/status',
    method: 'POST',
    headers: {
      'Authorization': 'Bearer ${ORDERS_API_KEY}',
      'Content-Type': 'application/json',
    },
  },
});
```

### Implement the Handler

On your server:

```typescript
// Express.js example
app.post('/orders/status', async (req, res) => {
  const { order_id } = req.body;

  const order = await db.orders.findById(order_id);

  if (!order) {
    return res.json({
      error: 'Order not found',
    });
  }

  res.json({
    order_id: order.id,
    status: order.status,
    shipped_at: order.shippedAt,
    tracking_number: order.trackingNumber,
  });
});
```

## OAuth Tools

Connect to external services via OAuth.

### Google Calendar

```typescript
// Enable Google Calendar tool
await synkora.agents.enableOAuthTool(agent.id, {
  provider: 'google',
  tools: ['google_calendar'],
  scopes: ['calendar.readonly', 'calendar.events'],
});
```

Your agent can now:

- List calendar events
- Create new events
- Check availability

### GitHub

```typescript
await synkora.agents.enableOAuthTool(agent.id, {
  provider: 'github',
  tools: ['github_issues', 'github_repos'],
  scopes: ['repo', 'issues'],
});
```

Your agent can now:

- Create issues
- List repositories
- Search code

### Slack

```typescript
await synkora.agents.enableOAuthTool(agent.id, {
  provider: 'slack',
  tools: ['slack_messages'],
  scopes: ['chat:write', 'channels:read'],
});
```

## Tool Best Practices

### Clear Descriptions

Write descriptions that help the LLM understand when to use the tool:

```typescript
// ❌ Bad
{
  name: 'get_data',
  description: 'Gets data',
}

// ✅ Good
{
  name: 'get_order_status',
  description: 'Retrieves the current status and tracking information for a customer order. Use this when a customer asks about their order, delivery status, or tracking number.',
}
```

### Specific Parameters

Define parameters with detailed descriptions:

```typescript
{
  parameters: {
    type: 'object',
    properties: {
      email: {
        type: 'string',
        description: 'Customer email address in format user@domain.com',
        pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$',
      },
      date_range: {
        type: 'object',
        description: 'Date range for the query',
        properties: {
          start: { type: 'string', format: 'date' },
          end: { type: 'string', format: 'date' },
        },
      },
    },
    required: ['email'],
  },
}
```

### Handle Errors Gracefully

Return helpful error messages:

```typescript
app.post('/orders/status', async (req, res) => {
  try {
    const order = await getOrder(req.body.order_id);

    if (!order) {
      return res.json({
        success: false,
        message: 'No order found with that ID. Please verify the order number.',
      });
    }

    return res.json({
      success: true,
      data: order,
    });
  } catch (error) {
    return res.json({
      success: false,
      message: 'Unable to retrieve order status. Please try again later.',
    });
  }
});
```

### Require Confirmation for Sensitive Actions

```typescript
await synkora.agents.registerTool(agent.id, {
  name: 'delete_account',
  description: 'Permanently delete a user account',
  requiresConfirmation: true,
  parameters: { /* ... */ },
});
```

## System Prompt for Tool Usage

Update your agent's system prompt:

```text
You are a customer support agent with access to tools.

Available tools:
- get_order_status: Check order status by order ID
- create_ticket: Create a support ticket
- send_email: Send email to customer

Guidelines:
- Use tools proactively when they can help
- Confirm with the user before performing actions
- Report tool errors clearly
- Don't make up information - use tools to verify
```

## Monitor Tool Usage

Track tool usage in your analytics:

```typescript
const usage = await synkora.agents.getToolUsage(agent.id, {
  startDate: '2024-01-01',
  endDate: '2024-01-31',
});

console.log(usage);
// {
//   tools: [
//     { name: 'get_order_status', calls: 500, success_rate: 0.98 },
//     { name: 'create_ticket', calls: 150, success_rate: 0.95 },
//   ],
// }
```

## Next Steps

- [Build custom tools](/docs/guides/agents/custom-tools) with complex logic
- [Connect MCP servers](/docs/guides/agents/mcp-servers) for advanced integrations
