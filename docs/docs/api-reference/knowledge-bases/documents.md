---
sidebar_position: 2
---

# Documents API

Manage documents within knowledge bases.

## List Documents

```http
GET /api/v1/knowledge-bases/{kb_id}/documents
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number |
| `limit` | integer | Items per page |
| `status` | string | `processing`, `ready`, `failed` |
| `type` | string | File type filter |

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "doc-123",
      "name": "user-guide.pdf",
      "type": "pdf",
      "size_bytes": 1500000,
      "chunk_count": 45,
      "status": "ready",
      "metadata": {
        "author": "John Doe",
        "version": "2.0"
      },
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 50
  }
}
```

---

## Upload Document

```http
POST /api/v1/knowledge-bases/{kb_id}/documents
Content-Type: multipart/form-data
```

### Form Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | Document file |
| `metadata` | JSON string | No | Additional metadata |

### Supported Formats

- PDF (`.pdf`)
- Word (`.docx`, `.doc`)
- Markdown (`.md`)
- Text (`.txt`)
- HTML (`.html`)
- CSV (`.csv`)
- JSON (`.json`)

### Example (cURL)

```bash
curl -X POST "https://api.synkora.io/api/v1/knowledge-bases/kb-123/documents" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@user-guide.pdf" \
  -F 'metadata={"category": "guides", "version": "2.0"}'
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "doc-123",
    "name": "user-guide.pdf",
    "status": "processing",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Upload Multiple Documents

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/batch
Content-Type: multipart/form-data
```

### Form Fields

| Field | Type | Description |
|-------|------|-------------|
| `files` | file[] | Multiple document files |
| `metadata` | JSON string | Metadata applied to all |

### Response

```json
{
  "success": true,
  "data": {
    "job_id": "job-456",
    "documents": [
      { "id": "doc-123", "name": "file1.pdf", "status": "processing" },
      { "id": "doc-124", "name": "file2.pdf", "status": "processing" }
    ]
  }
}
```

---

## Add URL

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/url
```

### Request Body

```json
{
  "url": "https://docs.example.com/guide",
  "metadata": {
    "source": "website"
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "doc-125",
    "name": "https://docs.example.com/guide",
    "type": "url",
    "status": "processing",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Crawl Website

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/crawl
```

### Request Body

```json
{
  "start_url": "https://docs.example.com",
  "max_pages": 100,
  "include_patterns": ["/docs/*", "/guides/*"],
  "exclude_patterns": ["/api/*"],
  "depth": 3
}
```

### Response

```json
{
  "success": true,
  "data": {
    "job_id": "job-789",
    "status": "crawling",
    "pages_found": 0,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Add Text Content

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/text
```

### Request Body

```json
{
  "title": "Return Policy",
  "content": "Our return policy allows customers to return items within 30 days...",
  "metadata": {
    "type": "policy",
    "version": "2024"
  }
}
```

---

## Get Document

```http
GET /api/v1/knowledge-bases/{kb_id}/documents/{doc_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": "doc-123",
    "name": "user-guide.pdf",
    "type": "pdf",
    "size_bytes": 1500000,
    "chunk_count": 45,
    "status": "ready",
    "metadata": {
      "author": "John Doe",
      "pages": 25
    },
    "processing_info": {
      "started_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:31:00Z",
      "duration_ms": 60000
    },
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Get Document Chunks

```http
GET /api/v1/knowledge-bases/{kb_id}/documents/{doc_id}/chunks
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "chunk-001",
      "content": "Chapter 1: Getting Started...",
      "metadata": {
        "page": 1,
        "section": "Introduction"
      },
      "token_count": 150
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 45
  }
}
```

---

## Update Document Metadata

```http
PATCH /api/v1/knowledge-bases/{kb_id}/documents/{doc_id}
```

### Request Body

```json
{
  "metadata": {
    "category": "updated-category",
    "version": "3.0"
  }
}
```

---

## Delete Document

```http
DELETE /api/v1/knowledge-bases/{kb_id}/documents/{doc_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "message": "Document deleted successfully"
  }
}
```

---

## Reprocess Document

```http
POST /api/v1/knowledge-bases/{kb_id}/documents/{doc_id}/reprocess
```

Reprocesses the document with current chunking settings.

### Response

```json
{
  "success": true,
  "data": {
    "status": "processing",
    "message": "Document reprocessing started"
  }
}
```

---

## Document Processing Status

| Status | Description |
|--------|-------------|
| `pending` | Queued for processing |
| `processing` | Being processed |
| `ready` | Successfully processed |
| `failed` | Processing failed |

### Check Processing Status

```http
GET /api/v1/knowledge-bases/{kb_id}/documents/{doc_id}/status
```

```json
{
  "success": true,
  "data": {
    "status": "processing",
    "progress": 75,
    "current_step": "embedding",
    "started_at": "2024-01-15T10:30:00Z"
  }
}
```
