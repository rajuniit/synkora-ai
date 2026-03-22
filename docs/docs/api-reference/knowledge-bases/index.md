---
sidebar_position: 1
---

# Knowledge Bases API

Manage knowledge bases for RAG-enabled agents.

## List Knowledge Bases

```http
GET /api/v1/knowledge-bases
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number |
| `limit` | integer | Items per page |
| `search` | string | Search by name |

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "kb-123",
      "name": "Product Documentation",
      "description": "Product guides and FAQs",
      "document_count": 50,
      "total_chunks": 1500,
      "embedding_model": "text-embedding-3-small",
      "vector_store": "qdrant",
      "status": "ready",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5
  }
}
```

---

## Create Knowledge Base

```http
POST /api/v1/knowledge-bases
```

### Request Body

```json
{
  "name": "Product Documentation",
  "description": "Product guides and FAQs",
  "embedding_model": "text-embedding-3-small",
  "vector_store": "qdrant",
  "chunking_config": {
    "strategy": "recursive",
    "chunk_size": 1000,
    "chunk_overlap": 200
  }
}
```

### Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | Required | Knowledge base name |
| `description` | string | - | Description |
| `embedding_model` | string | `text-embedding-3-small` | Embedding model |
| `vector_store` | string | `qdrant` | Vector database |
| `chunking_config` | object | - | Chunking configuration |

### Chunking Strategies

| Strategy | Description |
|----------|-------------|
| `recursive` | Split by paragraphs, then sentences |
| `fixed` | Fixed character count |
| `semantic` | Split by meaning |
| `markdown` | Respects markdown structure |

### Response

```json
{
  "success": true,
  "data": {
    "id": "kb-123",
    "name": "Product Documentation",
    "status": "ready",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Get Knowledge Base

```http
GET /api/v1/knowledge-bases/{kb_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "kb-123",
    "name": "Product Documentation",
    "description": "Product guides and FAQs",
    "document_count": 50,
    "total_chunks": 1500,
    "embedding_model": "text-embedding-3-small",
    "vector_store": "qdrant",
    "chunking_config": {
      "strategy": "recursive",
      "chunk_size": 1000,
      "chunk_overlap": 200
    },
    "status": "ready",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Update Knowledge Base

```http
PATCH /api/v1/knowledge-bases/{kb_id}
```

### Request Body

```json
{
  "name": "Updated Name",
  "description": "Updated description"
}
```

---

## Delete Knowledge Base

```http
DELETE /api/v1/knowledge-bases/{kb_id}
```

Deletes the knowledge base and all associated documents.

### Response

```json
{
  "success": true,
  "data": {
    "message": "Knowledge base deleted successfully"
  }
}
```

---

## Knowledge Base Stats

```http
GET /api/v1/knowledge-bases/{kb_id}/stats
```

### Response

```json
{
  "success": true,
  "data": {
    "document_count": 50,
    "total_chunks": 1500,
    "total_tokens": 750000,
    "storage_bytes": 15000000,
    "last_indexed_at": "2024-01-15T10:30:00Z",
    "by_type": {
      "pdf": 30,
      "docx": 15,
      "md": 5
    }
  }
}
```

---

## Reindex Knowledge Base

```http
POST /api/v1/knowledge-bases/{kb_id}/reindex
```

Reprocesses all documents with current settings.

### Response

```json
{
  "success": true,
  "data": {
    "job_id": "job-456",
    "status": "processing",
    "message": "Reindexing started"
  }
}
```
