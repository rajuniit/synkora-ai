---
sidebar_position: 2
---

# Chat API

Send messages to agents and receive responses, including streaming support.

## Chat (Non-Streaming)

```http
POST /api/v1/agents/{agent_id}/chat
```

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `agent_id` | string | Agent ID or slug |

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | User message |
| `conversation_id` | string | No | Continue existing conversation |
| `context` | object | No | Additional context to inject |
| `attachments` | array | No | File or image attachments |

### Request

```json
{
  "message": "What is your return policy?",
  "conversation_id": "conv-123",
  "context": {
    "user_name": "John",
    "account_type": "premium"
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "msg-456",
    "conversation_id": "conv-123",
    "role": "assistant",
    "content": "Our return policy allows you to return items within 30 days of purchase...",
    "citations": [
      {
        "text": "30-day return policy",
        "document_id": "doc-789",
        "chunk_id": "chunk-101"
      }
    ],
    "tool_calls": [],
    "usage": {
      "prompt_tokens": 150,
      "completion_tokens": 75,
      "total_tokens": 225
    },
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Example

```bash
curl -X POST "https://api.synkora.io/api/v1/agents/support-bot/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is your return policy?"
  }'
```

---

## Chat (Streaming)

```http
POST /api/v1/agents/{agent_id}/chat/stream
```

Returns a Server-Sent Events (SSE) stream.

### Request

Same as non-streaming chat.

### Response (SSE Stream)

```
event: start
data: {"conversation_id": "conv-123", "message_id": "msg-456"}

event: content
data: {"content": "Our "}

event: content
data: {"content": "return policy "}

event: content
data: {"content": "allows..."}

event: citations
data: {"citations": [{"text": "30-day return", "document_id": "doc-789"}]}

event: usage
data: {"prompt_tokens": 150, "completion_tokens": 75}

event: end
data: {"message_id": "msg-456"}
```

### Event Types

| Event | Description |
|-------|-------------|
| `start` | Stream started, includes IDs |
| `content` | Content chunk |
| `tool_call` | Tool invocation |
| `tool_result` | Tool execution result |
| `citations` | RAG citations |
| `usage` | Token usage |
| `error` | Error occurred |
| `end` | Stream completed |

### Example (JavaScript)

```javascript
const response = await fetch('https://api.synkora.io/api/v1/agents/support-bot/chat/stream', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'Tell me about your products',
  }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  const lines = text.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (data.content) {
        process.stdout.write(data.content);
      }
    }
  }
}
```

### Example (Python)

```python
import requests

response = requests.post(
    'https://api.synkora.io/api/v1/agents/support-bot/chat/stream',
    headers={
        'Authorization': 'Bearer YOUR_TOKEN',
        'Content-Type': 'application/json',
    },
    json={'message': 'Tell me about your products'},
    stream=True,
)

for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data: '):
            import json
            data = json.loads(line[6:])
            if 'content' in data:
                print(data['content'], end='', flush=True)
```

---

## With Attachments

### Image Attachment

```json
{
  "message": "What do you see in this image?",
  "attachments": [
    {
      "type": "image",
      "url": "https://example.com/image.png"
    }
  ]
}
```

### File Attachment

```json
{
  "message": "Analyze this document",
  "attachments": [
    {
      "type": "file",
      "file_id": "file-123"
    }
  ]
}
```

---

## With Context

Inject dynamic context into the conversation:

```json
{
  "message": "What's my order status?",
  "context": {
    "user": {
      "name": "John Doe",
      "email": "john@example.com",
      "account_type": "premium"
    },
    "recent_orders": [
      {
        "id": "order-123",
        "status": "shipped",
        "tracking": "1Z999AA10123456784"
      }
    ]
  }
}
```

The context is available to the agent for generating personalized responses.

---

## Tool Calls

When the agent uses tools, the response includes tool calls:

```json
{
  "success": true,
  "data": {
    "id": "msg-456",
    "content": "I found the weather information for Tokyo...",
    "tool_calls": [
      {
        "id": "call-789",
        "tool": "get_weather",
        "arguments": {
          "location": "Tokyo"
        },
        "result": {
          "temperature": 22,
          "conditions": "sunny"
        }
      }
    ]
  }
}
```

---

## Error Handling

### Rate Limited

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Please try again later.",
    "retry_after": 60
  }
}
```

### Insufficient Credits

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_CREDITS",
    "message": "Not enough credits to process this request.",
    "credits_required": 10,
    "credits_available": 5
  }
}
```

### Context Too Long

```json
{
  "success": false,
  "error": {
    "code": "CONTEXT_TOO_LONG",
    "message": "The conversation context exceeds the model's limit.",
    "max_tokens": 128000,
    "current_tokens": 135000
  }
}
```
