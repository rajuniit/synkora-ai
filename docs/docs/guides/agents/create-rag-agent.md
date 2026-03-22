---
sidebar_position: 1
---

# Create a RAG-Enabled Agent

This guide walks you through creating an AI agent that can answer questions using your own documents and knowledge base.

## What is RAG?

RAG (Retrieval Augmented Generation) enhances your agent with the ability to:

- Search through your documents
- Find relevant information
- Generate accurate responses based on your content

## Prerequisites

- A running Synkora instance
- API access or dashboard access
- Documents to upload (PDFs, markdown, etc.)

## Step 1: Create a Knowledge Base

First, create a knowledge base to store your documents.

### Using the Dashboard

1. Navigate to **Knowledge Bases**
2. Click **Create Knowledge Base**
3. Enter:
   - **Name**: Product Documentation
   - **Description**: Product guides and FAQs
   - **Embedding Model**: text-embedding-3-small

### Using the API

```bash
curl -X POST "https://api.synkora.io/api/v1/knowledge-bases" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Product Documentation",
    "description": "Product guides and FAQs",
    "embedding_model": "text-embedding-3-small"
  }'
```

### Using the SDK

```typescript
const kb = await synkora.knowledgeBases.create({
  name: 'Product Documentation',
  description: 'Product guides and FAQs',
  embeddingModel: 'text-embedding-3-small',
});

console.log('Knowledge Base ID:', kb.id);
```

## Step 2: Upload Documents

Add documents to your knowledge base.

### Supported Formats

- PDF files
- Word documents (.docx)
- Markdown files (.md)
- Plain text (.txt)
- Web pages (via URL)

### Upload via Dashboard

1. Go to your knowledge base
2. Click **Upload Documents**
3. Drag and drop or select files

### Upload via API

```bash
curl -X POST "https://api.synkora.io/api/v1/knowledge-bases/KB_ID/documents" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@user-guide.pdf" \
  -F 'metadata={"category": "guides"}'
```

### Upload via SDK

```typescript
import fs from 'fs';

await synkora.knowledgeBases.uploadDocument(kb.id, {
  file: fs.createReadStream('user-guide.pdf'),
  metadata: { category: 'guides' },
});
```

### Add Web Pages

```typescript
await synkora.knowledgeBases.addUrl(kb.id, {
  url: 'https://docs.example.com/getting-started',
});
```

## Step 3: Wait for Processing

Documents are processed asynchronously:

1. **Parsing**: Extract text from documents
2. **Chunking**: Split into smaller segments
3. **Embedding**: Generate vector embeddings
4. **Indexing**: Store in vector database

Check processing status:

```typescript
const status = await synkora.knowledgeBases.getDocument(kb.id, docId);
console.log('Status:', status.status); // 'processing' or 'ready'
```

## Step 4: Create the Agent

Create an agent and connect it to the knowledge base.

### Using the Dashboard

1. Navigate to **Agents**
2. Click **Create Agent**
3. Configure:
   - **Name**: Documentation Assistant
   - **Model**: GPT-4o
   - **System Prompt**: (see below)
4. In the **Knowledge Bases** section, add your KB
5. Click **Create**

### System Prompt for RAG Agent

```text
You are a helpful documentation assistant for our product.

Your role:
- Answer questions based on the documentation
- Provide accurate, helpful responses
- Cite relevant documentation when answering
- Admit when information is not in the documentation

Guidelines:
- Always search the knowledge base before answering
- Be concise but thorough
- If you're unsure, say so
- Suggest related topics when relevant
```

### Using the SDK

```typescript
const agent = await synkora.agents.create({
  name: 'Documentation Assistant',
  modelName: 'gpt-4o',
  systemPrompt: `You are a helpful documentation assistant...`,
  temperature: 0.7,
});

// Connect knowledge base
await synkora.agents.addKnowledgeBase(agent.id, kb.id, {
  searchConfig: {
    topK: 5,
    threshold: 0.7,
    searchType: 'hybrid',
  },
});

console.log('Agent created:', agent.id);
```

## Step 5: Test Your Agent

### Via Dashboard

1. Go to your agent's page
2. Click the **Chat** tab
3. Ask questions about your documents

### Via API

```bash
curl -X POST "https://api.synkora.io/api/v1/agents/AGENT_ID/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I reset my password?"
  }'
```

### Via SDK

```typescript
const response = await synkora.agents.chat(agent.id, {
  message: 'How do I reset my password?',
});

console.log(response.content);
console.log('Citations:', response.citations);
```

## Step 6: Tune and Optimize

### Adjust Search Settings

```typescript
await synkora.agents.updateKnowledgeBase(agent.id, kb.id, {
  searchConfig: {
    topK: 10,              // More results
    threshold: 0.6,         // Lower threshold
    searchType: 'hybrid',   // Semantic + keyword
    reranking: true,        // Enable reranking
  },
});
```

### Improve Chunking

Reprocess documents with different settings:

```typescript
await synkora.knowledgeBases.update(kb.id, {
  chunkingConfig: {
    strategy: 'semantic',
    chunkSize: 800,
    chunkOverlap: 150,
  },
});

await synkora.knowledgeBases.reindex(kb.id);
```

## Best Practices

### Document Quality

- Clean, well-formatted documents work best
- Remove headers/footers that repeat
- Use headings and structure
- Include relevant metadata

### Chunking Strategy

| Content Type | Recommended Size | Strategy |
|--------------|------------------|----------|
| Technical docs | 800-1200 | `markdown` |
| FAQs | 500-800 | `semantic` |
| Long-form | 1000-1500 | `recursive` |

### System Prompt Tips

- Be explicit about using the knowledge base
- Guide citation behavior
- Handle edge cases (no results found)
- Set the right tone

## Troubleshooting

### Agent not finding relevant content

- Lower the similarity threshold
- Increase topK results
- Try hybrid search
- Check document processing status

### Responses not citing sources

- Update system prompt to request citations
- Ensure KB is properly connected
- Check if documents contain relevant content

### Slow responses

- Reduce topK value
- Disable reranking for speed
- Use faster embedding model

## Next Steps

- [Add custom tools](/docs/guides/agents/add-tools) to your agent
- [Deploy to Slack](/docs/guides/integrations/slack-bot)
- Learn about [advanced RAG](/docs/guides/knowledge-base/advanced-rag)
