---
sidebar_position: 1
---

# Python SDK

> **Note:** A `synkora` PyPI package is not yet published. Use the REST API directly with `httpx` or `requests`.

## Calling the API from Python

```bash
export SYNKORA_API_URL=http://localhost:5001
export SYNKORA_API_KEY=sk_your_api_key
```

```python
import os
import httpx

BASE_URL = os.environ["SYNKORA_API_URL"]
HEADERS = {
    "Authorization": f"Bearer {os.environ['SYNKORA_API_KEY']}",
    "Content-Type": "application/json",
}

# List agents
with httpx.Client() as client:
    r = client.get(f"{BASE_URL}/api/v1/agents", headers=HEADERS)
    agents = r.json()

# Create an agent
with httpx.Client() as client:
    r = client.post(
        f"{BASE_URL}/api/v1/agents",
        headers=HEADERS,
        json={
            "name": "Support Bot",
            "model_name": "gpt-4o",
            "system_prompt": "You are a helpful support assistant.",
        },
    )
    agent = r.json()
```

## Next Steps

- [API Reference](http://localhost:5001/api/v1/docs) (live Swagger UI on your instance)
- [Authentication](/docs/getting-started/authentication)
