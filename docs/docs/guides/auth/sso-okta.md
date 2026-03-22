---
sidebar_position: 1
---

# Okta SSO Setup

Configure Okta for enterprise single sign-on.

## Prerequisites

- Okta admin access
- Synkora Enterprise plan

## Step 1: Create Okta Application

1. Go to Okta Admin Console
2. Applications > Create App Integration
3. Select SAML 2.0

## Step 2: Configure SAML Settings

| Setting | Value |
|---------|-------|
| Single Sign On URL | `https://api.synkora.io/auth/saml/callback` |
| Audience URI | `synkora` |
| Name ID Format | EmailAddress |

### Attribute Statements

| Name | Value |
|------|-------|
| email | user.email |
| firstName | user.firstName |
| lastName | user.lastName |

## Step 3: Configure Synkora

```typescript
await synkora.tenants.configureSAML({
  provider: 'okta',
  ssoUrl: 'https://your-org.okta.com/app/xxx/sso/saml',
  certificate: '-----BEGIN CERTIFICATE-----...',
  entityId: 'http://www.okta.com/xxx',
});
```

## Step 4: Test SSO

Visit: `https://app.synkora.io/auth/sso?tenant=your-tenant`

## Next Steps

- [Configure other OAuth providers](/docs/guides/auth/oauth-providers)
- [Manage API keys](/docs/guides/auth/api-keys)
