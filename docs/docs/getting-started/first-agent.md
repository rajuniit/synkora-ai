---
sidebar_position: 4
---

# Create Your First Agent

This guide walks you through creating and configuring your first AI agent with Synkora.

## What is an Agent?

An agent in Synkora is an AI-powered assistant that can:

- Respond to user messages using LLM models
- Access knowledge bases for contextual information
- Execute tools to perform actions
- Maintain conversation history
- Be deployed across multiple channels

## Creating an Agent

### Using the Dashboard

1. **Navigate to Agents**
   - Open the Synkora dashboard
   - Click **Agents** in the sidebar

2. **Create New Agent**
   - Click the **Create Agent** button
   - Fill in the basic information:

   | Field | Description | Example |
   |-------|-------------|---------|
   | Name | Agent's display name | Customer Support Bot |
   | Description | Brief description | Handles customer inquiries |
   | Slug | URL-friendly identifier | support-bot |

3. **Configure the Model**
   - Select your LLM provider (OpenAI, Anthropic, etc.)
   - Choose a model (e.g., GPT-4o, Claude 3.5 Sonnet)
   - Set parameters:
     - **Temperature**: 0.0-1.0 (lower = more focused)
     - **Max Tokens**: Maximum response length

4. **Write the System Prompt**

   The system prompt defines your agent's behavior:

   ```text
   You are a helpful customer support agent for Acme Corp.

   Your responsibilities:
   - Answer questions about our products
   - Help with order status and returns
   - Escalate complex issues to human support

   Guidelines:
   - Be friendly and professional
   - Keep responses concise
   - Ask clarifying questions when needed
   - Never make up information
   ```

5. **Save and Test**
   - Click **Create**
   - Use the built-in chat to test your agent

### Using the API

```bash
curl -X POST http://localhost:5001/api/v1/agents \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Support Bot",
    "description": "Handles customer inquiries",
    "slug": "support-bot",
    "model_name": "gpt-4o",
    "system_prompt": "You are a helpful customer support agent...",
    "temperature": 0.7,
    "max_tokens": 1000
  }'
```


## Testing Your Agent

### In the Dashboard

1. Navigate to your agent
2. Click the **Chat** tab
3. Send test messages

### Via API

```bash
# Start a conversation
curl -X POST http://localhost:5001/api/v1/agents/YOUR_AGENT_ID/chat \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hi, I need help with my order"
  }'
```


## Improving Your Agent

### Add a Knowledge Base

Connect your agent to documentation or FAQs via the dashboard (Agents → your agent → Knowledge Base tab) or the API:

```bash
# Create a knowledge base
curl -X POST http://localhost:5001/api/v1/knowledge-bases \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Product Documentation"}'

# Attach it to your agent
curl -X POST http://localhost:5001/api/v1/agents/YOUR_AGENT_ID/knowledge-bases \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"knowledge_base_id": "KB_ID"}'
```

### Add Tools

Enable built-in tools for your agent via the dashboard (Agents → your agent → Tools tab) or the API:

```bash
curl -X POST http://localhost:5001/api/v1/agents/YOUR_AGENT_ID/tools \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "web_search"}'
```

### Configure Personality

Fine-tune the system prompt:

```text
You are Alex, a friendly and knowledgeable support agent.

Personality traits:
- Warm and empathetic
- Patient with explanations
- Uses casual but professional language
- Occasionally uses appropriate emoji

Response style:
- Start with acknowledgment of the user's concern
- Provide clear, step-by-step solutions
- End with an offer to help further
```

## Agent Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `name` | Display name | Required |
| `slug` | URL identifier | Auto-generated |
| `model_name` | LLM model to use | Required |
| `system_prompt` | Behavior instructions | Required |
| `temperature` | Response randomness (0-1) | `0.7` |
| `max_tokens` | Max response length | `1000` |
| `top_p` | Nucleus sampling | `1.0` |
| `presence_penalty` | Repetition penalty | `0.0` |
| `frequency_penalty` | Word frequency penalty | `0.0` |

## Best Practices

### System Prompt Guidelines

1. **Be specific** about the agent's role and capabilities
2. **Set boundaries** on what the agent should/shouldn't do
3. **Provide examples** of good responses when helpful
4. **Include error handling** instructions
5. **Keep it focused** - avoid overly long prompts

### Testing Strategies

1. Test **edge cases** (unusual questions, errors)
2. Test **conversation flow** (multi-turn dialogues)
3. Test **knowledge retrieval** if using RAG
4. Test **tool usage** if tools are enabled
5. Monitor **token usage** to optimize costs

## Next Steps

- [Add a Knowledge Base](/docs/guides/agents/create-rag-agent) - Enable RAG for your agent
- [Add Tools](/docs/guides/agents/add-tools) - Give your agent capabilities
- [Deploy to Slack](/docs/guides/integrations/slack-bot) - Make your agent available in Slack
- [Embed on Website](/docs/guides/integrations/embed-widget) - Add a chat widget
