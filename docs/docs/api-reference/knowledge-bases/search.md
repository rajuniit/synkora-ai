---
sidebar_position: 3
---

# Search API

Search documents within knowledge bases.

## Search Knowledge Base

```http
POST /api/v1/knowledge-bases/{kb_id}/search
```

### Request Body

```json
{
  "query": "How do I reset my password?",
  "top_k": 5,
  "threshold": 0.7,
  "search_type": "hybrid",
  "filters": {
    "category": "user-guide"
  }
}
```

### Search Parameters

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string | Required | Search query |
| `top_k` | integer | 5 | Number of results |
| `threshold` | number | 0.7 | Minimum similarity score |
| `search_type` | string | `semantic` | `semantic`, `keyword`, `hybrid` |
| `filters` | object | - | Metadata filters |
| `reranking` | boolean | false | Enable reranking |

### Response

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "content": "To reset your password, click on 'Forgot Password' on the login page...",
        "score": 0.92,
        "document_id": "doc-123",
        "document_name": "user-guide.pdf",
        "chunk_id": "chunk-456",
        "metadata": {
          "page": 15,
          "section": "Account Settings",
          "category": "user-guide"
        }
      },
      {
        "content": "Password requirements: at least 8 characters, one uppercase...",
        "score": 0.85,
        "document_id": "doc-123",
        "document_name": "user-guide.pdf",
        "chunk_id": "chunk-789"
      }
    ],
    "query_time_ms": 45
  }
}
```

---

## Search Types

### Semantic Search

Vector similarity search using embeddings:

```json
{
  "query": "reset my account credentials",
  "search_type": "semantic"
}
```

Best for: Conceptual queries, natural language questions

### Keyword Search

Traditional text matching:

```json
{
  "query": "password reset",
  "search_type": "keyword"
}
```

Best for: Exact term matching, technical queries

### Hybrid Search

Combines semantic and keyword search:

```json
{
  "query": "how to reset password",
  "search_type": "hybrid",
  "semantic_weight": 0.7,
  "keyword_weight": 0.3
}
```

Best for: General queries, best of both worlds

---

## Filtering

### Equality Filter

```json
{
  "filters": {
    "category": "user-guide"
  }
}
```

### Comparison Filters

```json
{
  "filters": {
    "version": { "$gte": "2.0" },
    "pages": { "$lte": 100 }
  }
}
```

### Array Filters

```json
{
  "filters": {
    "tags": { "$in": ["important", "featured"] }
  }
}
```

### Logical Operators

```json
{
  "filters": {
    "$and": [
      { "category": "guides" },
      { "version": { "$gte": "2.0" } }
    ]
  }
}
```

---

## Reranking

Enable semantic reranking for better results:

```json
{
  "query": "password reset instructions",
  "top_k": 10,
  "reranking": true,
  "rerank_top_n": 5
}
```

### Reranking Models

| Model | Description |
|-------|-------------|
| `cohere-rerank-v3` | Cohere Rerank v3 |
| `jina-reranker-v2` | Jina Reranker v2 |

---

## Multi-Query Search

Search with multiple query variants:

```http
POST /api/v1/knowledge-bases/{kb_id}/search/multi
```

### Request Body

```json
{
  "queries": [
    "How to reset password",
    "Forgot password recovery",
    "Account credential reset"
  ],
  "fusion_method": "reciprocal_rank",
  "top_k": 5
}
```

### Fusion Methods

| Method | Description |
|--------|-------------|
| `reciprocal_rank` | RRF fusion |
| `weighted` | Weighted score fusion |
| `max` | Take max score per document |

---

## Cross-Knowledge-Base Search

Search across multiple knowledge bases:

```http
POST /api/v1/search
```

### Request Body

```json
{
  "query": "pricing information",
  "knowledge_base_ids": ["kb-123", "kb-456"],
  "top_k": 10
}
```

### Response

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "content": "Our pricing starts at $10/month...",
        "knowledge_base_id": "kb-123",
        "knowledge_base_name": "Sales Documentation"
      },
      {
        "content": "Enterprise pricing is available...",
        "knowledge_base_id": "kb-456",
        "knowledge_base_name": "Enterprise Docs"
      }
    ]
  }
}
```

---

## Debugging Search

Get detailed search analytics:

```json
{
  "query": "password reset",
  "debug": true
}
```

### Debug Response

```json
{
  "success": true,
  "data": {
    "results": [...],
    "debug": {
      "query_embedding_time_ms": 15,
      "vector_search_time_ms": 25,
      "reranking_time_ms": 30,
      "total_time_ms": 70,
      "candidates_before_filtering": 100,
      "candidates_after_filtering": 45
    }
  }
}
```
