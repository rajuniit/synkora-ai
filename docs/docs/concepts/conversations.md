---
sidebar_position: 4
---

# Conversations

Conversations manage the interaction history between users and agents, maintaining context across multiple messages.

## What is a Conversation?

A conversation represents a chat session between a user and an agent:

- **Message History**: All messages in the session
- **Context**: Maintained across messages
- **Metadata**: User info, session data
- **State**: Active, archived, or deleted

```
┌─────────────────────────────────────────────────────────┐
│                    Conversation                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Agent: Support Bot                               │    │
│  │ User: user-123                                   │    │
│  │ Created: 2024-01-15 10:30:00                    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Messages                                         │    │
│  │ ├─ User: "Hello, I need help with my order"    │    │
│  │ ├─ Assistant: "Hi! I'd be happy to help..."    │    │
│  │ ├─ User: "It hasn't arrived yet"               │    │
│  │ └─ Assistant: "Let me check the status..."     │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Creating Conversations

### Implicit Creation

Conversations are created automatically when chatting:

```typescript
// This creates a new conversation
const response = await synkora.agents.chat(agentId, {
  message: 'Hello!',
});

// Conversation ID is in the response
const conversationId = response.conversationId;
```

### Explicit Creation

Create a conversation with specific settings:

```typescript
const conversation = await synkora.conversations.create({
  agentId: agent.id,
  metadata: {
    userId: 'user-123',
    channel: 'web',
    sessionId: 'session-abc',
  },
});
```

## Sending Messages

### Continue a Conversation

```typescript
// First message
const response1 = await synkora.agents.chat(agentId, {
  message: 'What is your return policy?',
});

// Continue the conversation
const response2 = await synkora.agents.chat(agentId, {
  conversationId: response1.conversationId,
  message: 'And how long does a refund take?',
});
```

### Streaming Responses

```typescript
const stream = await synkora.agents.chatStream(agentId, {
  conversationId: conversationId,
  message: 'Tell me about your products',
});

for await (const chunk of stream) {
  process.stdout.write(chunk.content);
}
```

### With Attachments

```typescript
const response = await synkora.agents.chat(agentId, {
  conversationId: conversationId,
  message: 'Can you analyze this image?',
  attachments: [
    {
      type: 'image',
      url: 'https://example.com/image.png',
    },
  ],
});
```

## Message Types

### User Messages

```typescript
{
  role: 'user',
  content: 'Hello, I need help',
  timestamp: '2024-01-15T10:30:00Z',
}
```

### Assistant Messages

```typescript
{
  role: 'assistant',
  content: 'Hi! How can I help you today?',
  timestamp: '2024-01-15T10:30:01Z',
  toolCalls: [/* if tools were used */],
  citations: [/* if RAG was used */],
}
```

### System Messages

```typescript
{
  role: 'system',
  content: 'User upgraded to premium plan',
  timestamp: '2024-01-15T10:30:02Z',
}
```

### Tool Messages

```typescript
{
  role: 'tool',
  toolCallId: 'call-123',
  content: '{"weather": "sunny", "temp": 22}',
  timestamp: '2024-01-15T10:30:03Z',
}
```

## Conversation Management

### Retrieve Conversation

```typescript
const conversation = await synkora.conversations.get(conversationId);

console.log(conversation.messages);
console.log(conversation.metadata);
```

### List Conversations

```typescript
const conversations = await synkora.conversations.list({
  agentId: agent.id,
  userId: 'user-123',
  startDate: '2024-01-01',
  limit: 20,
});
```

### Get Messages

```typescript
const messages = await synkora.conversations.getMessages(conversationId, {
  limit: 50,
  before: 'message-id', // Pagination
});
```

### Archive Conversation

```typescript
await synkora.conversations.archive(conversationId);
```

### Delete Conversation

```typescript
await synkora.conversations.delete(conversationId);
```

## Context Management

### Context Window

LLMs have limited context windows. Synkora manages this automatically:

```typescript
// Configure context handling
await synkora.agents.update(agentId, {
  contextConfig: {
    maxMessages: 50,        // Max messages to include
    maxTokens: 8000,        // Max context tokens
    strategy: 'sliding',    // sliding, summary, or hybrid
  },
});
```

#### Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `sliding` | Keep most recent N messages | Short conversations |
| `summary` | Summarize older messages | Long conversations |
| `hybrid` | Recent + summary | General use |

### Message Summarization

For long conversations:

```typescript
// Enable automatic summarization
await synkora.agents.update(agentId, {
  contextConfig: {
    strategy: 'hybrid',
    summaryThreshold: 20,    // Summarize after 20 messages
    summaryModel: 'gpt-3.5-turbo',
  },
});
```

### Memory Injection

Add context from external sources:

```typescript
const response = await synkora.agents.chat(agentId, {
  conversationId: conversationId,
  message: 'What is my order status?',
  context: {
    // Injected into the prompt
    userInfo: {
      name: 'John Doe',
      accountType: 'premium',
    },
    recentOrders: [
      { id: 'order-123', status: 'shipped' },
    ],
  },
});
```

## Metadata and Variables

### Conversation Metadata

Store additional information:

```typescript
await synkora.conversations.update(conversationId, {
  metadata: {
    userId: 'user-123',
    channel: 'slack',
    department: 'sales',
    priority: 'high',
    tags: ['urgent', 'billing'],
  },
});
```

### Conversation Variables

Store stateful data:

```typescript
// Set variables
await synkora.conversations.setVariable(conversationId, 'currentStep', 'payment');
await synkora.conversations.setVariable(conversationId, 'cart', {
  items: ['product-1', 'product-2'],
  total: 99.99,
});

// Get variables
const step = await synkora.conversations.getVariable(conversationId, 'currentStep');
```

## Multi-Channel Conversations

### Channel Continuity

Continue conversations across channels:

```typescript
// Start on web
const webConv = await synkora.conversations.create({
  agentId: agent.id,
  metadata: { channel: 'web', userId: 'user-123' },
});

// Continue on Slack
const slackMessage = await synkora.agents.chat(agentId, {
  conversationId: webConv.id,  // Same conversation
  message: 'Continuing from web...',
  metadata: { channel: 'slack' },
});
```

### Channel-Specific Formatting

```typescript
// Response formatting varies by channel
const response = await synkora.agents.chat(agentId, {
  conversationId: conversationId,
  message: 'Show my options',
  channelConfig: {
    channel: 'slack',
    formatting: {
      enableBlocks: true,
      enableButtons: true,
    },
  },
});
```

## Analytics

### Conversation Metrics

```typescript
const analytics = await synkora.conversations.getAnalytics(conversationId);

console.log(analytics);
// {
//   messageCount: 15,
//   duration: 1800,  // seconds
//   avgResponseTime: 1.2,
//   toolCalls: 5,
//   ragQueries: 3,
//   sentiment: 'positive',
// }
```

### Aggregated Analytics

```typescript
const agentAnalytics = await synkora.agents.getConversationAnalytics(agentId, {
  startDate: '2024-01-01',
  endDate: '2024-01-31',
});

console.log(agentAnalytics);
// {
//   totalConversations: 1500,
//   avgDuration: 300,
//   resolutionRate: 0.85,
//   satisfactionScore: 4.2,
// }
```

## Best Practices

### Conversation Design

1. **Clear handoffs** - Handle context when switching agents
2. **State management** - Use variables for complex flows
3. **Error recovery** - Handle mid-conversation errors gracefully
4. **Privacy** - Don't store sensitive data unnecessarily

### Performance

1. **Context limits** - Configure appropriate max messages
2. **Cleanup** - Archive old conversations
3. **Pagination** - Use pagination for message history
4. **Caching** - Cache frequently accessed conversations

### User Experience

1. **Continuity** - Let users resume conversations
2. **History** - Provide conversation history access
3. **Export** - Allow users to export conversations
4. **Feedback** - Collect satisfaction ratings

## Related Concepts

- [Agents](/docs/concepts/agents) - Creating agents
- [Tools](/docs/concepts/tools) - Tool calls in conversations
