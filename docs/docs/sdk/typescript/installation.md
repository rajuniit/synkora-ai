---
sidebar_position: 1
---

# TypeScript SDK

> **Note:** A dedicated `@synkora/sdk` npm package is not yet published. Use the REST API directly — it is fully documented at `/api/v1/docs` on your running instance.

## Calling the API from TypeScript

Set your instance URL and API key as environment variables:

```env
SYNKORA_API_URL=http://localhost:5001
SYNKORA_API_KEY=sk_your_api_key
```

Then use `fetch` (or any HTTP client):

```typescript
const BASE_URL = process.env.SYNKORA_API_URL;
const API_KEY  = process.env.SYNKORA_API_KEY;

const headers = {
  'Authorization': `Bearer ${API_KEY}`,
  'Content-Type': 'application/json',
};

// List agents
const res = await fetch(`${BASE_URL}/api/v1/agents`, { headers });
const { data: agents } = await res.json();

// Create an agent
const create = await fetch(`${BASE_URL}/api/v1/agents`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    name: 'Support Bot',
    model_name: 'gpt-4o',
    system_prompt: 'You are a helpful support assistant.',
  }),
});
const agent = await create.json();
```

## Next Steps

- [Quick Start](/docs/getting-started/quick-start)
- [Authentication](/docs/getting-started/authentication)
- [API Reference](http://localhost:5001/api/v1/docs) (live Swagger UI on your instance)
