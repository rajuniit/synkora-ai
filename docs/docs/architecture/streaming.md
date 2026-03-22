---
sidebar_position: 7
---

# SSE Streaming

Server-Sent Events for real-time chat responses.

## How It Works

```
Client        Server         LLM Provider
  │              │                │
  │──POST /chat──▶               │
  │              │──Request──────▶
  │◀─SSE Stream──│◀─Stream───────│
  │◀─────────────│◀───────────────│
  │◀─────────────│◀───────────────│
  │◀──[END]──────│◀───[DONE]──────│
```

## Server Implementation

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

@router.post("/agents/{agent_id}/chat/stream")
async def chat_stream(agent_id: str, request: ChatRequest):
    async def event_stream():
        async for chunk in chat_service.stream(agent_id, request):
            yield f"event: {chunk.type}\n"
            yield f"data: {chunk.json()}\n\n"

        yield "event: end\n"
        yield "data: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

## Chat Stream Service

```python
class ChatStreamService:
    async def stream(
        self,
        agent_id: str,
        request: ChatRequest,
    ) -> AsyncIterator[StreamChunk]:
        agent = await self.get_agent(agent_id)
        messages = await self.build_messages(agent, request)

        # Start event
        yield StreamChunk(
            type="start",
            conversation_id=request.conversation_id,
        )

        # Stream LLM response
        async for chunk in self.llm_client.stream(agent.model_name, messages):
            if chunk.content:
                yield StreamChunk(type="content", content=chunk.content)

            if chunk.tool_calls:
                for tool_call in chunk.tool_calls:
                    yield StreamChunk(type="tool_call", tool_call=tool_call)

                    # Execute tool
                    result = await self.execute_tool(tool_call)
                    yield StreamChunk(type="tool_result", result=result)

        # Citations (if RAG)
        if citations := await self.get_citations():
            yield StreamChunk(type="citations", citations=citations)

        # Usage stats
        yield StreamChunk(type="usage", usage=self.get_usage())
```

## Client Implementation

### JavaScript

```javascript
const response = await fetch('/api/agents/123/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: 'Hello' }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  for (const line of text.split('\n')) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (data.content) {
        console.log(data.content);
      }
    }
  }
}
```

### Python

```python
import httpx

async with httpx.AsyncClient() as client:
    async with client.stream('POST', url, json=payload) as response:
        async for line in response.aiter_lines():
            if line.startswith('data: '):
                data = json.loads(line[6:])
                print(data.get('content', ''), end='')
```

## Event Types

| Event | Description |
|-------|-------------|
| `start` | Stream started |
| `content` | Text content chunk |
| `tool_call` | Tool invocation |
| `tool_result` | Tool execution result |
| `citations` | RAG citations |
| `usage` | Token usage |
| `error` | Error occurred |
| `end` | Stream completed |
