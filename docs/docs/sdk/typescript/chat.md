---
sidebar_position: 4
---

# Chat & Streaming

Send messages and handle streaming responses.

## Simple Chat

```typescript
const response = await synkora.agents.chat(agentId, {
  message: 'What is your return policy?',
});

console.log(response.content);
console.log('Tokens used:', response.usage.totalTokens);
```

## With Conversation

```typescript
// Start conversation
const response1 = await synkora.agents.chat(agentId, {
  message: 'What is your return policy?',
});

// Continue conversation
const response2 = await synkora.agents.chat(agentId, {
  conversationId: response1.conversationId,
  message: 'How long does the refund take?',
});
```

## Streaming

```typescript
const stream = await synkora.agents.chatStream(agentId, {
  message: 'Tell me about your products',
});

for await (const chunk of stream) {
  if (chunk.type === 'content') {
    process.stdout.write(chunk.content);
  } else if (chunk.type === 'citations') {
    console.log('\nCitations:', chunk.citations);
  } else if (chunk.type === 'usage') {
    console.log('\nTokens:', chunk.usage.totalTokens);
  }
}
```

## With Context

```typescript
const response = await synkora.agents.chat(agentId, {
  message: 'What is my order status?',
  context: {
    user: {
      name: 'John Doe',
      email: 'john@example.com',
    },
    recentOrders: [
      { id: 'ORD-123', status: 'shipped' },
    ],
  },
});
```

## With Attachments

```typescript
const response = await synkora.agents.chat(agentId, {
  message: 'What is in this image?',
  attachments: [
    {
      type: 'image',
      url: 'https://example.com/image.png',
    },
  ],
});
```

## Conversations

```typescript
// List conversations
const conversations = await synkora.conversations.list({
  agentId,
  limit: 20,
});

// Get conversation
const conversation = await synkora.conversations.get(conversationId);

// Get messages
const messages = await synkora.conversations.getMessages(conversationId);

// Archive
await synkora.conversations.archive(conversationId);

// Delete
await synkora.conversations.delete(conversationId);
```

## Error Handling

```typescript
try {
  const response = await synkora.agents.chat(agentId, {
    message: 'Hello',
  });
} catch (error) {
  if (error.code === 'RATE_LIMITED') {
    await sleep(error.retryAfter * 1000);
    // Retry
  } else if (error.code === 'INSUFFICIENT_CREDITS') {
    console.error('Out of credits');
  }
}
```
