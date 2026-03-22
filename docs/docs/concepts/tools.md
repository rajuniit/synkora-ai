---
sidebar_position: 3
---

# Tools

Tools extend agent capabilities beyond conversation, allowing them to perform actions, retrieve data, and interact with external systems.

## What are Tools?

Tools are functions that agents can call to:

- **Retrieve information** (search, API calls)
- **Perform actions** (create tickets, send emails)
- **Execute code** (calculations, data processing)
- **Access external systems** (databases, third-party APIs)

```
┌─────────────────────────────────────────────────────────┐
│                        Agent                             │
│  ┌─────────────────────────────────────────────────┐    │
│  │                      LLM                         │    │
│  │  "I need to search the knowledge base..."       │    │
│  └──────────────────────┬──────────────────────────┘    │
│                         │                                │
│                         ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │                   Tool Router                    │    │
│  └──────┬────────────────┬─────────────────┬───────┘    │
│         │                │                 │             │
│         ▼                ▼                 ▼             │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐       │
│  │  Search   │    │  Create   │    │   Send    │       │
│  │    KB     │    │  Ticket   │    │   Email   │       │
│  └───────────┘    └───────────┘    └───────────┘       │
└─────────────────────────────────────────────────────────┘
```

## Built-in Tools

Synkora provides several built-in tools:

### Knowledge Base Search

```typescript
// Enabled automatically when KB is connected
await synkora.agents.addKnowledgeBase(agent.id, kbId);
```

### Web Search

```typescript
await synkora.agents.enableTool(agent.id, 'web_search');

// Agent can now search the web
// "Search the web for recent news about AI"
```

### Code Execution

```typescript
await synkora.agents.enableTool(agent.id, 'code_execution', {
  languages: ['python', 'javascript'],
  timeout: 30000,
  sandbox: true,
});

// Agent can execute code
// "Calculate the compound interest on $10,000 at 5% for 10 years"
```

### URL Fetching

```typescript
await synkora.agents.enableTool(agent.id, 'fetch_url');

// Agent can fetch web pages
// "Get the content from https://example.com/api-docs"
```

## OAuth Tools

Connect to external services via OAuth:

### Google Tools

```typescript
// Enable Google integration
await synkora.agents.enableTool(agent.id, 'google_calendar', {
  scopes: ['calendar.readonly', 'calendar.events'],
});

await synkora.agents.enableTool(agent.id, 'google_drive', {
  scopes: ['drive.readonly'],
});

// Agent can access Google services
// "Show my calendar events for tomorrow"
// "Find the Q4 report in my Drive"
```

### GitHub Tools

```typescript
await synkora.agents.enableTool(agent.id, 'github', {
  scopes: ['repo', 'issues'],
});

// "Create an issue in the synkora/synkora repo"
// "List open PRs in the frontend repo"
```

### Slack Tools

```typescript
await synkora.agents.enableTool(agent.id, 'slack', {
  scopes: ['channels:read', 'chat:write'],
});

// "Send a message to #general"
// "Get the last 10 messages from #support"
```

### Jira Tools

```typescript
await synkora.agents.enableTool(agent.id, 'jira', {
  scopes: ['read:jira-work', 'write:jira-work'],
});

// "Create a bug ticket for the login issue"
// "Show my assigned tickets"
```

## Custom Tools

Create your own tools:

### Tool Definition

```typescript
const myTool = {
  name: 'get_weather',
  description: 'Get current weather for a location',
  parameters: {
    type: 'object',
    properties: {
      location: {
        type: 'string',
        description: 'City name or coordinates',
      },
      units: {
        type: 'string',
        enum: ['celsius', 'fahrenheit'],
        default: 'celsius',
      },
    },
    required: ['location'],
  },
};

await synkora.agents.registerTool(agent.id, myTool);
```

### Tool Handler

Implement the tool handler on your server:

```typescript
// In your backend
app.post('/api/tools/get_weather', async (req, res) => {
  const { location, units } = req.body;

  const weather = await weatherApi.get(location, units);

  res.json({
    temperature: weather.temp,
    conditions: weather.conditions,
    humidity: weather.humidity,
  });
});
```

### Webhook Tools

Configure tools as webhooks:

```typescript
await synkora.agents.registerTool(agent.id, {
  name: 'create_order',
  description: 'Create a new order in the system',
  parameters: {
    type: 'object',
    properties: {
      productId: { type: 'string' },
      quantity: { type: 'number' },
    },
    required: ['productId', 'quantity'],
  },
  handler: {
    type: 'webhook',
    url: 'https://api.example.com/orders',
    method: 'POST',
    headers: {
      'Authorization': 'Bearer ${ORDERS_API_KEY}',
    },
  },
});
```

## MCP Servers

Connect Model Context Protocol (MCP) servers:

```typescript
// Register MCP server
await synkora.agents.addMCPServer(agent.id, {
  name: 'database-tools',
  url: 'http://localhost:3001/mcp',
  transport: 'http',
});

// All tools from the MCP server become available
// The agent can now use database query tools, etc.
```

## Tool Configuration

### Rate Limiting

```typescript
await synkora.agents.configureTools(agent.id, {
  rateLimiting: {
    maxCallsPerMinute: 10,
    maxCallsPerConversation: 50,
  },
});
```

### Confirmation

Require user confirmation for sensitive actions:

```typescript
await synkora.agents.registerTool(agent.id, {
  name: 'delete_record',
  description: 'Delete a record from the database',
  requiresConfirmation: true,
  parameters: { /* ... */ },
});
```

### Permissions

Control tool access:

```typescript
await synkora.agents.configureTools(agent.id, {
  permissions: {
    'create_order': {
      allowedRoles: ['sales', 'admin'],
      requiresAuth: true,
    },
    'web_search': {
      allowedRoles: ['*'],  // All roles
    },
  },
});
```

## Tool Execution Flow

1. **LLM decides** to use a tool based on the query
2. **Synkora validates** the tool call parameters
3. **Tool executes** (built-in, webhook, or MCP)
4. **Result returns** to the LLM
5. **LLM generates** response using tool result

```typescript
// Example conversation with tool use
const response = await synkora.agents.chat(agent.id, {
  message: 'What is the weather in Tokyo?',
});

// Behind the scenes:
// 1. LLM: "I should use the get_weather tool"
// 2. Tool call: get_weather({ location: "Tokyo" })
// 3. Tool result: { temperature: 22, conditions: "sunny" }
// 4. LLM: "The weather in Tokyo is 22°C and sunny."
```

## Tool Schemas

### JSON Schema

Tools use JSON Schema for parameter validation:

```typescript
{
  name: 'search_products',
  description: 'Search products in the catalog',
  parameters: {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description: 'Search query',
      },
      category: {
        type: 'string',
        enum: ['electronics', 'clothing', 'home'],
      },
      priceRange: {
        type: 'object',
        properties: {
          min: { type: 'number' },
          max: { type: 'number' },
        },
      },
      inStock: {
        type: 'boolean',
        default: true,
      },
    },
    required: ['query'],
  },
}
```

### Response Schema

Define expected response format:

```typescript
{
  name: 'get_user',
  // ...
  responseSchema: {
    type: 'object',
    properties: {
      id: { type: 'string' },
      name: { type: 'string' },
      email: { type: 'string' },
    },
  },
}
```

## Best Practices

### Tool Design

1. **Clear descriptions** - LLM uses these to decide when to call
2. **Specific parameters** - Well-defined with examples
3. **Focused scope** - One tool, one purpose
4. **Error handling** - Return meaningful error messages

### Security

1. **Validate inputs** - Sanitize all parameters
2. **Use least privilege** - Minimal necessary permissions
3. **Audit logging** - Track all tool calls
4. **Rate limiting** - Prevent abuse

### Performance

1. **Timeout handling** - Set appropriate timeouts
2. **Caching** - Cache repeated calls when appropriate
3. **Async execution** - For long-running tools
4. **Batching** - Combine related calls

## Related Concepts

- [Agents](/docs/concepts/agents) - Using tools in agents
- [Knowledge Bases](/docs/concepts/knowledge-bases) - KB search tool
