---
sidebar_position: 2
---

# Quick Start

Get started with the Synkora Python SDK.

## Create an Agent

```python
from synkora import Synkora

synkora = Synkora(api_key="sk_xxx")

# Create agent
agent = synkora.agents.create(
    name="Support Bot",
    model_name="gpt-4o",
    system_prompt="You are a helpful assistant.",
)

print(f"Created agent: {agent.id}")
```

## Chat with Agent

```python
# Simple chat
response = synkora.agents.chat(
    agent.id,
    message="Hello! How can you help me?",
)

print(response.content)
```

## Streaming Chat

```python
stream = synkora.agents.chat_stream(
    agent.id,
    message="Tell me about your features",
)

for chunk in stream:
    if chunk.content:
        print(chunk.content, end="", flush=True)
```

## Async Support

```python
import asyncio
from synkora import AsyncSynkora

async def main():
    synkora = AsyncSynkora(api_key="sk_xxx")

    response = await synkora.agents.chat(
        agent_id,
        message="Hello!",
    )

    print(response.content)

asyncio.run(main())
```

## Knowledge Base

```python
# Create knowledge base
kb = synkora.knowledge_bases.create(name="Docs")

# Upload document
with open("guide.pdf", "rb") as f:
    synkora.knowledge_bases.upload_document(kb.id, file=f)

# Connect to agent
synkora.agents.add_knowledge_base(agent.id, kb.id)
```

## Error Handling

```python
from synkora import SynkoraError

try:
    agent = synkora.agents.get("invalid-id")
except SynkoraError as e:
    print(f"Error {e.code}: {e.message}")
```
