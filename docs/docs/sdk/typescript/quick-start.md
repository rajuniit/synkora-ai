---
sidebar_position: 2
---

# Quick Start (REST API)

> **Note:** A dedicated `@synkora/sdk` npm package is not yet published. This guide shows equivalent REST API calls using `fetch`.

## Create an Agent

```typescript
const BASE_URL = process.env.SYNKORA_API_URL ?? 'http://localhost:5001';
const headers = {
  'Authorization': `Bearer ${process.env.SYNKORA_API_KEY}`,
  'Content-Type': 'application/json',
};

const res = await fetch(`${BASE_URL}/api/v1/agents`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    name: 'Support Bot',
    model_name: 'gpt-4o',
    system_prompt: 'You are a helpful support assistant.',
  }),
});
const agent = await res.json();
console.log('Created agent:', agent.id);
```

## Chat with an Agent

```typescript
const res = await fetch(`${BASE_URL}/api/v1/agents/${agent.id}/chat`, {
  method: 'POST',
  headers,
  body: JSON.stringify({ message: 'Hello! How can you help me?' }),
});
const { data } = await res.json();
console.log(data.content);
```

## Streaming Chat

```typescript
const res = await fetch(`${BASE_URL}/api/v1/agents/${agent.id}/chat/stream`, {
  method: 'POST',
  headers,
  body: JSON.stringify({ message: 'Tell me about your features' }),
});

const reader = res.body!.getReader();
const decoder = new TextDecoder();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  process.stdout.write(decoder.decode(value));
}
```

## Error Handling

```typescript
const res = await fetch(`${BASE_URL}/api/v1/agents/invalid-id`, { headers });
if (!res.ok) {
  const err = await res.json();
  console.error(`Error ${res.status}: ${err.message}`);
}
```

## Next Steps

- [API Reference](http://localhost:5001/api/v1/docs) (live Swagger UI on your instance)
- [Authentication](/docs/getting-started/authentication)
