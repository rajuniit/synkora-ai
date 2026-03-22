---
slug: why-we-built-synkora
title: "Why We Built Synkora: The Journey from Prototype to Production"
authors: [engineering]
tags: [engineering, architecture]
---

The gap between an AI prototype and a production system is larger than it appears. Here's how we approached building Synkora to bridge that gap.

<!-- truncate -->

## The Problem

Every AI project starts the same way:

1. Get API key from OpenAI/Anthropic
2. Write a few lines of code
3. Demo something impressive
4. Realize you need 10x more infrastructure for production

The "last mile" of AI development includes:

- **State management**: Conversation history, context windows
- **Retrieval**: Connecting LLMs to your data (RAG)
- **Tools**: Enabling LLMs to take actions
- **Deployment**: Slack, web widgets, APIs
- **Operations**: Monitoring, billing, access control

## Our Approach

### 1. Start with Multi-Tenancy

Instead of bolting on multi-tenancy later, we built it into the foundation:

```python
class Agent(BaseModel, TenantMixin):
    __tablename__ = "agents"
    # Every row is scoped to a tenant
```

This means Synkora can be used as a platform (SaaS) or self-hosted for a single organization.

### 2. Unified LLM Interface

Rather than coupling to a single provider, we use LiteLLM for a unified interface:

```python
# Same code works with any provider
response = await llm_client.chat(
    model="gpt-4o",  # or claude-3-5-sonnet, gemini-1.5-pro
    messages=messages,
)
```

### 3. Streaming First

All chat responses stream by default. This provides a better UX and handles long responses gracefully:

```python
async for chunk in chat_service.stream(agent_id, message):
    yield chunk  # Stream to client immediately
```

### 4. Tool Extensibility

Agents can be extended with:

- Built-in tools (web search, code execution)
- OAuth tools (Google Calendar, GitHub)
- Custom webhooks
- MCP servers

### 5. Production Observability

Every request is traced with Langfuse for:

- Token usage tracking
- Latency monitoring
- Cost attribution
- Quality evaluation

## Architecture Decisions

### PostgreSQL + pgvector

We chose PostgreSQL with pgvector over specialized vector databases for simpler operations. For larger deployments, Qdrant or Pinecone can be used.

### Redis for Everything

Redis serves multiple purposes:

- Caching (agent configs, sessions)
- Rate limiting
- Celery broker
- Pub/sub for real-time features

### Celery for Background Work

Document processing, embedding generation, and webhook delivery all happen asynchronously via Celery workers.

## What's Next

We're working on:

- Advanced RAG features (multi-query, query rewriting)
- Agent orchestration (multi-agent workflows)
- Evaluation frameworks
- More integrations

Stay tuned for more updates!
