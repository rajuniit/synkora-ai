---
sidebar_position: 5
---

# Authentication

Synkora supports multiple authentication methods for both users and API access.

## Authentication Methods

| Method | Use Case | Description |
|--------|----------|-------------|
| **JWT Tokens** | Web dashboard, SDK | Short-lived access tokens with refresh |
| **API Keys** | Server-to-server | Long-lived keys for backend integrations |
| **OAuth/SSO** | Enterprise | Google, GitHub, Microsoft, Okta, etc. |

## User Authentication

### Email/Password

Standard email and password authentication for the dashboard:

```typescript
// Sign up
const response = await fetch('/api/v1/auth/signup', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'secure-password',
    name: 'John Doe',
  }),
});

// Sign in
const { access_token, refresh_token } = await fetch('/api/v1/auth/signin', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'secure-password',
  }),
}).then(r => r.json());
```

### JWT Tokens

Access tokens are short-lived (default: 30 minutes):

```typescript
// Using the access token
const response = await fetch('/api/v1/agents', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
  },
});

// Refresh when expired
const { access_token: newToken } = await fetch('/api/v1/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    refresh_token: refresh_token,
  }),
}).then(r => r.json());
```

### OAuth/SSO

Enable single sign-on with external providers:

#### Google OAuth

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

```typescript
// Redirect to Google OAuth
window.location.href = '/api/v1/auth/oauth/google';

// Handle callback
// The backend handles the callback and redirects with tokens
```

#### GitHub OAuth

```env
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
```

#### Microsoft/Azure AD

```env
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_TENANT_ID=your-tenant-id
```

## API Authentication

### API Keys

For server-to-server integrations, use API keys:

#### Creating an API Key

1. Go to **Settings** > **API Keys** in the dashboard
2. Click **Create API Key**
3. Copy the key (it won't be shown again)

Or via API:

```bash
curl -X POST http://localhost:5001/api/v1/api-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Server",
    "scopes": ["agents:read", "agents:write", "chat:write"]
  }'
```

#### Using API Keys

```bash
# Include in Authorization header
curl http://localhost:5001/api/v1/agents \
  -H "Authorization: Bearer sk_your_api_key"

# Or as X-API-Key header
curl http://localhost:5001/api/v1/agents \
  -H "X-API-Key: sk_your_api_key"
```

```typescript
const headers = { 'Authorization': 'Bearer sk_your_api_key' };
```

### API Key Scopes

| Scope | Description |
|-------|-------------|
| `agents:read` | Read agent configurations |
| `agents:write` | Create/update/delete agents |
| `chat:write` | Send chat messages |
| `knowledge-bases:read` | Read knowledge bases |
| `knowledge-bases:write` | Manage knowledge bases |
| `billing:read` | View billing information |
| `admin` | Full administrative access |

### Key Rotation

Regularly rotate API keys for security:

```bash
# Create new key
curl -X POST http://localhost:5001/api/v1/api-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"name": "Production Server v2"}'

# Update your applications

# Revoke old key
curl -X DELETE http://localhost:5001/api/v1/api-keys/OLD_KEY_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Multi-Tenancy

Synkora supports multi-tenant authentication:

### Tenant Context

Each user belongs to one or more tenants:

```typescript
// JWT token contains tenant_id
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "tenant_id": "tenant-uuid",
  "exp": 1234567890
}
```

### Switching Tenants

```typescript
// List user's tenants
const tenants = await fetch('/api/v1/auth/tenants', {
  headers: { 'Authorization': `Bearer ${token}` },
}).then(r => r.json());

// Switch tenant (get new token for different tenant)
const { access_token } = await fetch('/api/v1/auth/switch-tenant', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: JSON.stringify({ tenant_id: 'other-tenant-id' }),
}).then(r => r.json());
```

## Public Agent Access

For public-facing agents (chat widgets), use widget tokens:

```bash
# Generate a widget token (server-side, via API)
curl -X POST http://localhost:5001/api/v1/agents/YOUR_AGENT_ID/widget-token \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"allowed_origins": ["https://example.com"], "expires_in": "30d"}'

# Use in chat widget (client-side)
# See the embed widget guide for the self-hosted widget.js path
```

## Security Best Practices

### Token Security

1. **Store tokens securely**
   - Use `httpOnly` cookies for web apps
   - Use secure storage on mobile
   - Never expose tokens in URLs or logs

2. **Use short token lifetimes**
   - Access tokens: 15-30 minutes
   - Refresh tokens: 7-30 days

3. **Implement token refresh**
   - Refresh before expiration
   - Handle refresh failures gracefully

### API Key Security

1. **Never commit API keys** to version control
2. **Use environment variables** for configuration
3. **Scope keys appropriately** - least privilege principle
4. **Rotate keys regularly** (monthly recommended)
5. **Monitor key usage** for anomalies

### OAuth Security

1. **Validate redirect URIs** strictly
2. **Use state parameter** to prevent CSRF
3. **Verify token signatures**
4. **Handle token expiration**

## Troubleshooting

### "Invalid token" errors

- Check token hasn't expired
- Verify token format (Bearer prefix)
- Ensure correct API base URL

### "Unauthorized" errors

- Verify API key is valid
- Check required scopes
- Confirm tenant access

### OAuth issues

- Verify callback URLs match configuration
- Check OAuth provider credentials
- Review OAuth error responses

## Using API Keys in HTTP calls

Pass your API key in the `Authorization` header:

```bash
curl http://localhost:5001/api/v1/agents \
  -H "Authorization: Bearer sk_your_api_key"
```

```typescript
const res = await fetch('http://localhost:5001/api/v1/agents', {
  headers: { 'Authorization': `Bearer ${process.env.SYNKORA_API_KEY}` },
});
const agents = await res.json();
```
