---
sidebar_position: 5
---

# API Reference

> **Note:** A dedicated `@synkora/sdk` npm package is not yet published. Use the live Swagger UI at `/api/v1/docs` on your instance for the complete, up-to-date REST API reference.

The endpoint reference below describes the resource shape. All endpoints are under `<your-instance>/api/v1/` and accept `Authorization: Bearer <api-key>`.

## Base URL Configuration

| Option | Description |
|--------|-------------|
| `SYNKORA_API_URL` | Base URL of your Synkora instance (e.g. `http://localhost:5001`) |
| `SYNKORA_API_KEY` | Your API key (create in Settings → API Keys) |

## Agents

### synkora.agents.list(options?)

List all agents.

### synkora.agents.create(data)

Create a new agent.

### synkora.agents.get(id)

Get an agent by ID.

### synkora.agents.update(id, data)

Update an agent.

### synkora.agents.delete(id)

Delete an agent.

### synkora.agents.chat(id, data)

Send a message to an agent.

### synkora.agents.chatStream(id, data)

Stream a chat response.

## Knowledge Bases

### synkora.knowledgeBases.list(options?)

List knowledge bases.

### synkora.knowledgeBases.create(data)

Create a knowledge base.

### synkora.knowledgeBases.get(id)

Get a knowledge base.

### synkora.knowledgeBases.uploadDocument(id, data)

Upload a document.

### synkora.knowledgeBases.search(id, data)

Search the knowledge base.

## Conversations

### synkora.conversations.list(options?)

List conversations.

### synkora.conversations.get(id)

Get a conversation.

### synkora.conversations.getMessages(id, options?)

Get conversation messages.

## Billing

### synkora.billing.getSubscription()

Get current subscription.

### synkora.billing.getCredits()

Get credit balance.

### synkora.billing.getUsage(options?)

Get usage statistics.

## Types

```typescript
interface Agent {
  id: string;
  name: string;
  slug: string;
  modelName: string;
  systemPrompt: string;
  temperature: number;
  maxTokens: number;
  status: 'active' | 'inactive';
  createdAt: Date;
  updatedAt: Date;
}

interface ChatResponse {
  id: string;
  conversationId: string;
  content: string;
  citations: Citation[];
  toolCalls: ToolCall[];
  usage: Usage;
}

interface StreamChunk {
  type: 'content' | 'citations' | 'tool_call' | 'usage' | 'end';
  content?: string;
  citations?: Citation[];
  toolCall?: ToolCall;
  usage?: Usage;
}
```
