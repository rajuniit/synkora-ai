---
sidebar_position: 2
---

# OAuth Providers

Configure OAuth providers for user authentication.

## Google OAuth

### Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create OAuth 2.0 credentials
3. Set redirect URI: `https://api.synkora.io/auth/oauth/google/callback`

### Configuration

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

## GitHub OAuth

### Setup

1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Create new OAuth App
3. Set callback URL: `https://api.synkora.io/auth/oauth/github/callback`

### Configuration

```env
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
```

## Microsoft OAuth

### Setup

1. Go to Azure Portal > App registrations
2. Create new registration
3. Add redirect URI: `https://api.synkora.io/auth/oauth/microsoft/callback`

### Configuration

```env
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_TENANT_ID=your-tenant-id
```

## Custom OIDC Provider

```typescript
await synkora.tenants.configureOIDC({
  discoveryUrl: 'https://auth.example.com/.well-known/openid-configuration',
  clientId: 'your-client-id',
  clientSecret: 'your-client-secret',
  scopes: ['openid', 'email', 'profile'],
});
```
