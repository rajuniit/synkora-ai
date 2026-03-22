---
sidebar_position: 2
---

# Knowledge Bases

Knowledge bases enable Retrieval Augmented Generation (RAG), allowing your agents to answer questions based on your documents and data.

## What is RAG?

RAG (Retrieval Augmented Generation) combines:

1. **Retrieval**: Find relevant information from your documents
2. **Augmentation**: Add retrieved context to the LLM prompt
3. **Generation**: LLM generates response using the context

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  User Query │───▶│   Search    │───▶│  Retrieved  │
│             │    │  Vector DB  │    │   Context   │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                             │
                                             ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Response   │◀───│     LLM     │◀───│   Prompt +  │
│             │    │             │    │   Context   │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Creating a Knowledge Base

### Using the Dashboard

1. Navigate to **Knowledge Bases**
2. Click **Create Knowledge Base**
3. Configure settings:
   - **Name**: Descriptive name
   - **Description**: What it contains
   - **Embedding Model**: Model for vectorization
   - **Vector Store**: Qdrant or Pinecone

### Using the API

```bash
curl -X POST http://localhost:5001/api/v1/knowledge-bases \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Product Documentation",
    "description": "Product guides and FAQs",
    "embedding_model": "text-embedding-3-small",
    "vector_store": "qdrant"
  }'
```

### Using the SDK

```typescript
const kb = await synkora.knowledgeBases.create({
  name: 'Product Documentation',
  description: 'Product guides and FAQs',
  embeddingModel: 'text-embedding-3-small',
  vectorStore: 'qdrant',
});
```

## Adding Documents

### Supported Formats

| Format | Extensions | Notes |
|--------|------------|-------|
| PDF | `.pdf` | Text extraction with OCR support |
| Word | `.docx`, `.doc` | Full formatting preserved |
| Markdown | `.md` | Code blocks preserved |
| Text | `.txt` | Plain text |
| HTML | `.html` | Tags stripped |
| CSV | `.csv` | Row-based chunking |
| JSON | `.json` | Structured data |
| Web Pages | URL | Crawled and extracted |

### Upload Files

```typescript
// Single file
await synkora.knowledgeBases.uploadDocument(kb.id, {
  file: fs.createReadStream('guide.pdf'),
  metadata: { category: 'user-guide' },
});

// Multiple files
await synkora.knowledgeBases.uploadDocuments(kb.id, {
  files: [
    fs.createReadStream('faq.pdf'),
    fs.createReadStream('manual.pdf'),
  ],
});
```

### Add Web Pages

```typescript
// Single URL
await synkora.knowledgeBases.addUrl(kb.id, {
  url: 'https://docs.example.com/guide',
});

// Crawl entire site
await synkora.knowledgeBases.crawlWebsite(kb.id, {
  startUrl: 'https://docs.example.com',
  maxPages: 100,
  includePatterns: ['/docs/*'],
});
```

### Add Text Content

```typescript
await synkora.knowledgeBases.addText(kb.id, {
  title: 'Return Policy',
  content: 'Our return policy allows returns within 30 days...',
  metadata: { type: 'policy', version: '2024' },
});
```

## Document Processing

### Chunking

Documents are split into chunks for embedding:

```typescript
const kb = await synkora.knowledgeBases.create({
  name: 'Documentation',
  chunkingConfig: {
    strategy: 'recursive',  // or 'fixed', 'semantic'
    chunkSize: 1000,        // characters per chunk
    chunkOverlap: 200,      // overlap between chunks
  },
});
```

#### Chunking Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `recursive` | Splits by paragraphs, then sentences | General documents |
| `fixed` | Fixed character count | Uniform content |
| `semantic` | Splits by meaning | Technical docs |
| `markdown` | Respects markdown structure | Documentation |

### Embedding

Text chunks are converted to vectors:

| Model | Dimensions | Quality | Speed |
|-------|------------|---------|-------|
| `text-embedding-3-large` | 3072 | Highest | Slower |
| `text-embedding-3-small` | 1536 | High | Fast |
| `text-embedding-ada-002` | 1536 | Good | Fast |

## Searching

### Semantic Search

```typescript
const results = await synkora.knowledgeBases.search(kb.id, {
  query: 'How do I reset my password?',
  topK: 5,
  threshold: 0.7,
});

// Results include:
// - content: Chunk text
// - score: Similarity score
// - metadata: Document metadata
// - documentId: Source document
```

### Hybrid Search

Combine semantic and keyword search:

```typescript
const results = await synkora.knowledgeBases.search(kb.id, {
  query: 'password reset',
  searchType: 'hybrid',
  semanticWeight: 0.7,
  keywordWeight: 0.3,
});
```

### Filtered Search

```typescript
const results = await synkora.knowledgeBases.search(kb.id, {
  query: 'installation guide',
  filters: {
    category: 'user-guide',
    version: { $gte: '2.0' },
  },
});
```

## Advanced RAG

### Reranking

Improve result quality with a reranker:

```typescript
const kb = await synkora.knowledgeBases.create({
  name: 'Documentation',
  rerankingConfig: {
    enabled: true,
    model: 'cohere-rerank-v3',
    topN: 5,
  },
});
```

### Query Expansion

Expand queries for better recall:

```typescript
const kb = await synkora.knowledgeBases.create({
  name: 'Documentation',
  queryExpansion: {
    enabled: true,
    model: 'gpt-3.5-turbo',
    variants: 3,
  },
});
```

### Multi-Query RAG

Generate multiple search queries:

```typescript
// Agent configuration
const agent = await synkora.agents.create({
  name: 'Research Assistant',
  ragConfig: {
    multiQuery: true,
    queryCount: 3,
    fusionMethod: 'reciprocal_rank',
  },
});
```

## Connecting to Agents

```typescript
// Connect knowledge base to agent
await synkora.agents.addKnowledgeBase(agent.id, kb.id, {
  searchConfig: {
    topK: 5,
    threshold: 0.7,
    searchType: 'hybrid',
  },
});

// Agent automatically searches KB for relevant context
const response = await synkora.agents.chat(agent.id, {
  message: 'How do I install the product?',
});
```

## Vector Databases

### Qdrant

Self-hosted or cloud vector database:

```typescript
// Configuration
const kb = await synkora.knowledgeBases.create({
  name: 'Documentation',
  vectorStore: 'qdrant',
  vectorStoreConfig: {
    collectionName: 'docs',
    distance: 'cosine',
  },
});
```

### Pinecone

Managed cloud vector database:

```typescript
const kb = await synkora.knowledgeBases.create({
  name: 'Documentation',
  vectorStore: 'pinecone',
  vectorStoreConfig: {
    indexName: 'docs-index',
    namespace: 'production',
  },
});
```

## Best Practices

### Document Preparation

1. **Clean your data** - Remove duplicates, fix formatting
2. **Add metadata** - Categories, versions, dates
3. **Structure content** - Use headings, lists
4. **Keep chunks coherent** - Meaningful units of information

### Search Optimization

1. **Tune chunk size** - 500-1500 characters typically
2. **Use overlap** - 10-20% of chunk size
3. **Set appropriate thresholds** - 0.7-0.8 for precision
4. **Enable reranking** - For better relevance

### Maintenance

1. **Update regularly** - Keep content fresh
2. **Monitor quality** - Check retrieval accuracy
3. **Track usage** - Identify missing information
4. **Version documents** - Manage updates

## Related Concepts

- [Agents](/docs/concepts/agents) - Connecting KB to agents
- [Tools](/docs/concepts/tools) - KB search as a tool
