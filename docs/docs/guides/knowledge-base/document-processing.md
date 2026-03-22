---
sidebar_position: 3
---

# Document Processing

Learn how to optimize document processing for your knowledge base.

## Chunking Strategies

### Recursive (Default)

Best for general documents:

```typescript
chunkingConfig: {
  strategy: 'recursive',
  chunkSize: 1000,
  chunkOverlap: 200,
}
```

### Semantic

Best for technical documentation:

```typescript
chunkingConfig: {
  strategy: 'semantic',
  chunkSize: 800,
  chunkOverlap: 100,
}
```

### Markdown

Preserves document structure:

```typescript
chunkingConfig: {
  strategy: 'markdown',
  preserveHeaders: true,
}
```

## Metadata Extraction

Add metadata for better filtering:

```typescript
await synkora.knowledgeBases.uploadDocument(kbId, {
  file: fileStream,
  metadata: {
    category: 'user-guide',
    version: '2.0',
    language: 'en',
    author: 'Documentation Team',
  },
});
```

## Processing Pipeline

1. **Parse**: Extract text from files
2. **Clean**: Remove boilerplate, fix encoding
3. **Chunk**: Split into segments
4. **Embed**: Generate vector embeddings
5. **Index**: Store in vector database

## Best Practices

- Clean documents before upload
- Use consistent metadata schema
- Monitor processing status
- Reindex after configuration changes

## Troubleshooting

### Slow Processing

- Reduce chunk overlap
- Use smaller embedding model
- Check document size

### Poor Search Results

- Increase chunk overlap
- Try different chunking strategy
- Lower similarity threshold
