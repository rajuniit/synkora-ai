---
sidebar_position: 1
---

# Set Up Qdrant

Configure Qdrant as your vector database for knowledge bases.

## Self-Hosted Qdrant

### Docker

```bash
docker run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant
```

### Docker Compose

```yaml
services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  qdrant_data:
```

### Configure Synkora

```env
QDRANT_URL=http://localhost:6333
```

## Qdrant Cloud

1. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a cluster
3. Get your API key and URL

```env
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-api-key
```

## Create Knowledge Base with Qdrant

```typescript
const kb = await synkora.knowledgeBases.create({
  name: 'Documentation',
  vectorStore: 'qdrant',
  vectorStoreConfig: {
    collectionName: 'docs',
    distance: 'cosine',
  },
});
```

## Performance Tuning

### Index Settings

```typescript
vectorStoreConfig: {
  collectionName: 'docs',
  distance: 'cosine',
  hnsw: {
    m: 16,
    efConstruct: 100,
  },
}
```

### Hardware Recommendations

| Scale | RAM | Storage |
|-------|-----|---------|
| Small (under 100K vectors) | 2GB | 10GB |
| Medium (under 1M vectors) | 8GB | 50GB |
| Large (over 1M vectors) | 32GB+ | 200GB+ |

## Next Steps

- [Set up Pinecone](/docs/guides/knowledge-base/setup-pinecone) as alternative
- [Advanced RAG](/docs/guides/knowledge-base/advanced-rag)
