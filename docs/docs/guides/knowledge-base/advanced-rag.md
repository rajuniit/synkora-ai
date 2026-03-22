---
sidebar_position: 4
---

# Advanced RAG

Optimize retrieval quality with advanced RAG techniques.

## Hybrid Search

Combine semantic and keyword search:

```typescript
await synkora.agents.updateKnowledgeBase(agentId, kbId, {
  searchConfig: {
    searchType: 'hybrid',
    semanticWeight: 0.7,
    keywordWeight: 0.3,
  },
});
```

## Reranking

Improve result relevance with a reranker:

```typescript
searchConfig: {
  topK: 20,              // Retrieve more candidates
  reranking: true,
  rerankTopN: 5,         // Keep top 5 after reranking
  rerankModel: 'cohere-rerank-v3',
}
```

## Multi-Query RAG

Generate multiple search queries:

```typescript
ragConfig: {
  multiQuery: true,
  queryCount: 3,
  fusionMethod: 'reciprocal_rank',
}
```

## Query Expansion

Expand queries for better recall:

```typescript
ragConfig: {
  queryExpansion: true,
  expansionModel: 'gpt-3.5-turbo',
}
```

## Contextual Compression

Compress retrieved context:

```typescript
ragConfig: {
  contextCompression: true,
  maxContextTokens: 4000,
}
```

## Evaluation

Track RAG quality metrics:

```typescript
const metrics = await synkora.knowledgeBases.getMetrics(kbId);
// { avgRelevanceScore: 0.85, hitRate: 0.92, mrr: 0.78 }
```
