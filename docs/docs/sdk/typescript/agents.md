---
sidebar_position: 3
---

# Working with Agents

Manage agents using the TypeScript SDK.

## List Agents

```typescript
const agents = await synkora.agents.list({
  page: 1,
  limit: 20,
});

for (const agent of agents.data) {
  console.log(`${agent.name}: ${agent.id}`);
}
```

## Create Agent

```typescript
const agent = await synkora.agents.create({
  name: 'Customer Support',
  description: 'Handles customer inquiries',
  modelName: 'gpt-4o',
  systemPrompt: 'You are a helpful support agent...',
  temperature: 0.7,
  maxTokens: 1000,
});
```

## Get Agent

```typescript
const agent = await synkora.agents.get('agent-id');
console.log(agent.name, agent.status);
```

## Update Agent

```typescript
const updated = await synkora.agents.update('agent-id', {
  name: 'Updated Name',
  temperature: 0.5,
});
```

## Delete Agent

```typescript
await synkora.agents.delete('agent-id');
```

## Knowledge Bases

```typescript
// Add knowledge base
await synkora.agents.addKnowledgeBase(agentId, kbId, {
  searchConfig: {
    topK: 5,
    threshold: 0.7,
  },
});

// Remove knowledge base
await synkora.agents.removeKnowledgeBase(agentId, kbId);

// List connected knowledge bases
const kbs = await synkora.agents.listKnowledgeBases(agentId);
```

## Tools

```typescript
// Enable built-in tool
await synkora.agents.enableTool(agentId, 'web_search');

// Register custom tool
await synkora.agents.registerTool(agentId, {
  name: 'get_order',
  description: 'Get order status',
  parameters: {
    type: 'object',
    properties: {
      orderId: { type: 'string' },
    },
    required: ['orderId'],
  },
  handler: {
    type: 'webhook',
    url: 'https://api.example.com/orders',
  },
});

// List tools
const tools = await synkora.agents.listTools(agentId);
```

## Cloning

```typescript
const clone = await synkora.agents.clone(agentId, {
  name: 'Support Bot (Copy)',
});
```
