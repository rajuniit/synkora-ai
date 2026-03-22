---
sidebar_position: 3
---

# API Key Management

Create and manage API keys for server-to-server authentication.

## Creating API Keys

### Via Dashboard

1. Go to Settings > API Keys
2. Click "Create API Key"
3. Set name and scopes
4. Copy the key (shown only once)

### Via API

```typescript
const key = await synkora.apiKeys.create({
  name: 'Production Server',
  scopes: ['agents:read', 'agents:write', 'chat:write'],
  expiresAt: '2025-01-01',
});

console.log('API Key:', key.key); // sk_live_xxx
```

## Available Scopes

| Scope | Description |
|-------|-------------|
| `agents:read` | Read agent configurations |
| `agents:write` | Create/update/delete agents |
| `chat:write` | Send chat messages |
| `knowledge_bases:read` | Read knowledge bases |
| `knowledge_bases:write` | Manage knowledge bases |
| `billing:read` | View billing info |
| `admin` | Full access |

## Key Rotation

```typescript
// Create new key
const newKey = await synkora.apiKeys.create({
  name: 'Production Server v2',
  scopes: ['agents:read', 'chat:write'],
});

// Update your application

// Revoke old key
await synkora.apiKeys.revoke(oldKeyId);
```

## Best Practices

- Use minimal required scopes
- Rotate keys every 90 days
- Never commit keys to version control
- Monitor key usage for anomalies
