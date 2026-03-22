---
sidebar_position: 1
---

# Agents

Agents are the core building blocks of Synkora. An agent is an AI-powered assistant that combines an LLM with customizable behavior, knowledge, and capabilities.

## What is an Agent?

An agent in Synkora consists of:

- **LLM Configuration**: The model, temperature, and other parameters
- **System Prompt**: Instructions that define the agent's behavior
- **Knowledge Bases**: Connected document collections for RAG
- **Tools**: Capabilities the agent can execute
- **Deployment Config**: Channels and widget settings

```
┌─────────────────────────────────────────────────────────┐
│                         Agent                            │
│  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  System Prompt  │  │      LLM Configuration      │  │
│  └─────────────────┘  └─────────────────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ Knowledge Bases │  │          Tools              │  │
│  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Agent Lifecycle

### Creation

When you create an agent, you define its basic properties:

```typescript
const agent = await synkora.agents.create({
  name: 'Support Bot',
  description: 'Customer support assistant',
  modelName: 'gpt-4o',
  systemPrompt: 'You are a helpful support agent...',
  temperature: 0.7,
});
```

### Configuration

After creation, you can enhance the agent:

1. **Add Knowledge Bases** - Connect document collections
2. **Enable Tools** - Add capabilities like web search
3. **Configure Channels** - Set up Slack, Telegram, etc.
4. **Customize Widget** - Design the chat interface

### Deployment

Agents can be deployed to multiple channels:

- **Web Widget**: Embed on any website
- **Slack**: Deploy as a Slack bot
- **Telegram**: Create a Telegram bot
- **WhatsApp**: WhatsApp Business integration
- **Teams**: Microsoft Teams bot
- **API**: Direct API access

## Agent Types

### Basic Agent

A simple conversational agent with an LLM and system prompt:

```typescript
const basicAgent = await synkora.agents.create({
  name: 'FAQ Bot',
  modelName: 'gpt-3.5-turbo',
  systemPrompt: 'Answer user questions concisely.',
});
```

### RAG Agent

An agent enhanced with knowledge base retrieval:

```typescript
const ragAgent = await synkora.agents.create({
  name: 'Documentation Assistant',
  modelName: 'gpt-4o',
  systemPrompt: 'Help users with product documentation.',
  knowledgeBases: [kbId],
});
```

### Tool-Enabled Agent

An agent that can execute actions:

```typescript
const toolAgent = await synkora.agents.create({
  name: 'Action Bot',
  modelName: 'gpt-4o',
  systemPrompt: 'Help users complete tasks.',
  tools: ['web_search', 'create_ticket', 'send_email'],
});
```

## Configuration Options

### LLM Settings

| Parameter | Description | Range |
|-----------|-------------|-------|
| `model_name` | LLM model to use | Provider-specific |
| `temperature` | Response randomness | 0.0 - 2.0 |
| `max_tokens` | Maximum response length | 1 - model max |
| `top_p` | Nucleus sampling | 0.0 - 1.0 |
| `presence_penalty` | Topic diversity | -2.0 - 2.0 |
| `frequency_penalty` | Word repetition penalty | -2.0 - 2.0 |

### Supported Models

| Provider | Models |
|----------|--------|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo |
| Anthropic | claude-3-5-sonnet, claude-3-opus, claude-3-haiku |
| Google | gemini-1.5-pro, gemini-1.5-flash |
| Azure OpenAI | gpt-4, gpt-35-turbo (deployment names) |

### System Prompt

The system prompt defines agent behavior:

```text
You are a customer support agent for TechCorp.

## Your Role
- Answer product questions
- Help with troubleshooting
- Process returns and exchanges

## Guidelines
- Be professional and friendly
- Verify customer identity for account changes
- Escalate complex issues to human support

## Response Format
- Keep responses under 200 words
- Use bullet points for lists
- Include relevant links when helpful
```

## Agent State

Agents maintain state across conversations:

### Conversation Memory

Each conversation has its own context:

```typescript
// Start a conversation
const conv = await synkora.conversations.create({
  agentId: agent.id,
  metadata: { userId: 'user-123' },
});

// Messages within the conversation share context
await synkora.agents.chat(agent.id, {
  conversationId: conv.id,
  message: 'What is your return policy?',
});

// Agent remembers previous messages
await synkora.agents.chat(agent.id, {
  conversationId: conv.id,
  message: 'And how long do I have?', // References previous topic
});
```

### Persistent Variables

Store agent-specific data:

```typescript
await synkora.agents.setVariable(agent.id, 'last_announcement', {
  message: 'Holiday hours: Dec 24-25 closed',
  expires: '2024-12-26',
});
```

## Multi-Agent Patterns

### Routing Agent

Route queries to specialized agents:

```typescript
const routerAgent = await synkora.agents.create({
  name: 'Router',
  systemPrompt: `Route user queries to the appropriate agent:
  - Sales questions → sales-agent
  - Support issues → support-agent
  - Billing → billing-agent`,
  tools: ['route_to_agent'],
});
```

### Supervisor Agent

Orchestrate multiple agents:

```typescript
const supervisorAgent = await synkora.agents.create({
  name: 'Supervisor',
  systemPrompt: 'Coordinate between research and writing agents.',
  tools: ['call_agent'],
});
```

## Best Practices

### System Prompt Design

1. **Be specific** about the agent's role
2. **Set clear boundaries** on capabilities
3. **Provide examples** of good responses
4. **Define escalation paths** for edge cases
5. **Include error handling** instructions

### Model Selection

- **gpt-4o/claude-3-5-sonnet**: Complex reasoning, nuanced responses
- **gpt-3.5-turbo/claude-3-haiku**: Fast, cost-effective for simple tasks
- **gpt-4o-mini**: Balance of capability and cost

### Performance Optimization

1. **Use appropriate context lengths** - Don't include unnecessary history
2. **Optimize RAG retrieval** - Tune chunk size and top-k
3. **Cache common queries** - Reduce LLM calls
4. **Stream responses** - Better user experience

## Related Concepts

- [Knowledge Bases](/docs/concepts/knowledge-bases) - RAG and document retrieval
- [Tools](/docs/concepts/tools) - Extending agent capabilities
- [Conversations](/docs/concepts/conversations) - Managing chat sessions
