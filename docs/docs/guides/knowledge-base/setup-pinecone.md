---
sidebar_position: 2
---

# Set Up Pinecone

Configure Pinecone as your managed vector database.

## Create Pinecone Account

1. Sign up at [pinecone.io](https://www.pinecone.io)
2. Create a project
3. Create an index

## Configure Synkora

```env
PINECONE_API_KEY=your-api-key
PINECONE_ENVIRONMENT=us-east-1-aws
```

## Create Knowledge Base

```typescript
const kb = await synkora.knowledgeBases.create({
  name: 'Documentation',
  vectorStore: 'pinecone',
  vectorStoreConfig: {
    indexName: 'synkora-docs',
    namespace: 'production',
  },
});
```

## Index Configuration

Create index with these settings:

| Setting | Value |
|---------|-------|
| Dimensions | 1536 (text-embedding-3-small) or 3072 (text-embedding-3-large) |
| Metric | Cosine |
| Pod Type | p1 or s1 |

## Namespaces

Use namespaces for tenant isolation:

```typescript
vectorStoreConfig: {
  indexName: 'synkora-docs',
  namespace: `tenant-${tenantId}`,
}
```

## Next Steps

- [Document processing](/docs/guides/knowledge-base/document-processing)
- [Advanced RAG](/docs/guides/knowledge-base/advanced-rag)
