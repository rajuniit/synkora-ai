---
sidebar_position: 1
---

# Quick Start

Get up and running with Synkora in 5 minutes. This guide will walk you through creating your first AI agent.

## Prerequisites

- Docker and Docker Compose installed
- Node.js 18+ (for SDK usage)
- An OpenAI API key (or other LLM provider key)

## Step 1: Start Synkora

Clone the repository and start the services:

```bash
git clone https://github.com/getsynkora/synkora-ai.git
cd synkora
cp .env.example .env
```

Edit `.env` and add your LLM provider API key:

```env
OPENAI_API_KEY=sk-your-openai-key
# Or for other providers:
# ANTHROPIC_API_KEY=sk-ant-your-key
# GOOGLE_API_KEY=your-google-key
```

Start all services:

```bash
docker-compose up -d
```

## Step 2: Create an Admin User

```bash
docker-compose exec api python create_super_admin.py
```

This creates a super admin account. Note the credentials displayed.

## Step 3: Access the Dashboard

Open your browser and navigate to:

- **Dashboard**: http://localhost:3005
- **API**: http://localhost:5001
- **API Docs**: http://localhost:5001/docs

Sign in with the admin credentials created in Step 2.

## Step 4: Create Your First Agent

### Using the Dashboard

1. Navigate to **Agents** in the sidebar
2. Click **Create Agent**
3. Fill in the details:
   - **Name**: My First Agent
   - **Model**: GPT-4o (or your preferred model)
   - **System Prompt**: "You are a helpful assistant."
4. Click **Create**

### Using the API

```bash
curl -X POST http://localhost:5001/api/v1/agents \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Agent",
    "model_name": "gpt-4o",
    "system_prompt": "You are a helpful assistant."
  }'
```


## Step 5: Chat with Your Agent

### Using the Dashboard

1. Go to your agent's page
2. Click the **Chat** tab
3. Start chatting!

### Using the API

```bash
curl -X POST http://localhost:5001/api/v1/agents/YOUR_AGENT_ID/chat \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! What can you help me with?"
  }'
```


## What's Next?

Now that you have your first agent running:

- **[Add a Knowledge Base](/docs/guides/agents/create-rag-agent)**: Make your agent smarter with RAG
- **[Add Tools](/docs/guides/agents/add-tools)**: Give your agent capabilities like web search
- **[Deploy to Slack](/docs/guides/integrations/slack-bot)**: Make your agent available in Slack
- **[Embed on Your Website](/docs/guides/integrations/embed-widget)**: Add a chat widget

## Troubleshooting

### Services won't start

Check that all required ports are available:
- 3005 (Frontend)
- 5001 (API)
- 5432 (PostgreSQL)
- 6379 (Redis)
- 6333 (Qdrant)

```bash
docker-compose logs -f
```

### API key not working

Ensure your API key is correctly set in `.env` and the service was restarted:

```bash
docker-compose restart api
```

### Database connection errors

Run migrations:

```bash
docker-compose exec api alembic upgrade head
```
