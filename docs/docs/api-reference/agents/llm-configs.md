---
sidebar_position: 6
---

# LLM Configuration API

Manage LLM settings and provider configurations for agents.

## Get LLM Configuration

```http
GET /api/v1/agents/{agent_id}/llm-config
```

### Response

```json
{
  "success": true,
  "data": {
    "provider": "openai",
    "model_name": "gpt-4o",
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 1.0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "stop_sequences": [],
    "response_format": null
  }
}
```

---

## Update LLM Configuration

```http
PATCH /api/v1/agents/{agent_id}/llm-config
```

### Request Body

```json
{
  "model_name": "gpt-4o-mini",
  "temperature": 0.5,
  "max_tokens": 2000,
  "top_p": 0.9
}
```

### Configuration Options

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `model_name` | string | - | LLM model identifier |
| `temperature` | number | 0.0-2.0 | Response randomness |
| `max_tokens` | integer | 1-model max | Max response length |
| `top_p` | number | 0.0-1.0 | Nucleus sampling |
| `presence_penalty` | number | -2.0-2.0 | Topic diversity |
| `frequency_penalty` | number | -2.0-2.0 | Word repetition penalty |
| `stop_sequences` | array | - | Stop generation sequences |
| `response_format` | object | - | JSON mode configuration |

### Response

```json
{
  "success": true,
  "data": {
    "provider": "openai",
    "model_name": "gpt-4o-mini",
    "temperature": 0.5,
    "max_tokens": 2000,
    "top_p": 0.9,
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## JSON Mode

Enable JSON response format:

```json
{
  "response_format": {
    "type": "json_object",
    "schema": {
      "type": "object",
      "properties": {
        "answer": { "type": "string" },
        "confidence": { "type": "number" }
      }
    }
  }
}
```

---

## Provider-Specific Configuration

### OpenAI

```json
{
  "provider": "openai",
  "model_name": "gpt-4o",
  "provider_config": {
    "organization_id": "org-xxx",
    "seed": 42
  }
}
```

### Anthropic

```json
{
  "provider": "anthropic",
  "model_name": "claude-3-5-sonnet-20241022",
  "provider_config": {}
}
```

### Azure OpenAI

```json
{
  "provider": "azure",
  "model_name": "gpt-4",
  "provider_config": {
    "deployment_name": "my-gpt4-deployment",
    "api_version": "2024-02-15-preview"
  }
}
```

### Google

```json
{
  "provider": "google",
  "model_name": "gemini-1.5-pro",
  "provider_config": {
    "safety_settings": {
      "harassment": "block_only_high"
    }
  }
}
```

---

## List Available Models

```http
GET /api/v1/models
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "gpt-4o",
      "provider": "openai",
      "name": "GPT-4o",
      "context_window": 128000,
      "max_output_tokens": 16384,
      "supports_vision": true,
      "supports_tools": true,
      "cost_per_1k_input": 0.005,
      "cost_per_1k_output": 0.015
    },
    {
      "id": "claude-3-5-sonnet-20241022",
      "provider": "anthropic",
      "name": "Claude 3.5 Sonnet",
      "context_window": 200000,
      "max_output_tokens": 8192,
      "supports_vision": true,
      "supports_tools": true,
      "cost_per_1k_input": 0.003,
      "cost_per_1k_output": 0.015
    }
  ]
}
```

---

## Fallback Configuration

Configure model fallbacks:

```json
{
  "model_name": "gpt-4o",
  "fallback_models": [
    "gpt-4o-mini",
    "gpt-3.5-turbo"
  ],
  "fallback_on": [
    "rate_limit",
    "timeout",
    "service_unavailable"
  ]
}
```
