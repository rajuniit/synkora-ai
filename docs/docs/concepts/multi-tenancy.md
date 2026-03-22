---
sidebar_position: 5
---

# Multi-Tenancy

Synkora is built with multi-tenancy at its core, enabling complete data isolation between organizations while sharing the same infrastructure.

## What is Multi-Tenancy?

Multi-tenancy allows multiple organizations (tenants) to use Synkora while ensuring:

- **Data Isolation**: Each tenant's data is completely separate
- **Resource Isolation**: Configurable resource limits per tenant
- **Customization**: Per-tenant settings and branding
- **Billing**: Separate billing and usage tracking

```
┌─────────────────────────────────────────────────────────┐
│                    Synkora Platform                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Tenant A   │  │  Tenant B   │  │  Tenant C   │     │
│  │ ─────────── │  │ ─────────── │  │ ─────────── │     │
│  │ • Agents    │  │ • Agents    │  │ • Agents    │     │
│  │ • KBs       │  │ • KBs       │  │ • KBs       │     │
│  │ • Users     │  │ • Users     │  │ • Users     │     │
│  │ • Data      │  │ • Data      │  │ • Data      │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Shared Infrastructure               │    │
│  │  PostgreSQL  │  Redis  │  Qdrant  │  API        │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Tenant Structure

### Tenant Model

```typescript
interface Tenant {
  id: string;
  name: string;
  slug: string;           // URL-friendly identifier
  plan: 'free' | 'pro' | 'enterprise';
  settings: TenantSettings;
  createdAt: Date;
}

interface TenantSettings {
  maxAgents: number;
  maxKnowledgeBases: number;
  maxUsersperTenant: number;
  features: string[];
  customDomain?: string;
  branding?: {
    logo: string;
    primaryColor: string;
  };
}
```

### User-Tenant Relationship

Users can belong to multiple tenants:

```
┌──────────────┐     ┌────────────────────┐     ┌──────────────┐
│    User A    │─────│ TenantAccountJoin  │─────│   Tenant 1   │
│              │     │  • role: admin     │     │              │
└──────────────┘     └────────────────────┘     └──────────────┘
       │
       │             ┌────────────────────┐     ┌──────────────┐
       └─────────────│ TenantAccountJoin  │─────│   Tenant 2   │
                     │  • role: member    │     │              │
                     └────────────────────┘     └──────────────┘
```

## Data Isolation

### Database-Level Isolation

All data models include a `tenant_id`:

```python
class Agent(BaseModel):
    __tablename__ = "agents"

    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    name = Column(String)
    # ...

    __table_args__ = (
        Index("ix_agents_tenant_id", "tenant_id"),
    )
```

### Query Filtering

All queries are automatically filtered by tenant:

```python
# Service layer automatically adds tenant filter
async def get_agents(tenant_id: str) -> List[Agent]:
    return await db.execute(
        select(Agent).where(Agent.tenant_id == tenant_id)
    )
```

### API-Level Enforcement

Tenant context is extracted from authentication:

```python
@router.get("/agents")
async def list_agents(
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    # tenant_id is automatically extracted from JWT
    return await agent_service.list(tenant_id)
```

## Creating and Managing Tenants

### Create a Tenant

```typescript
// Admin API
const tenant = await synkora.admin.tenants.create({
  name: 'Acme Corporation',
  slug: 'acme',
  plan: 'pro',
  settings: {
    maxAgents: 10,
    maxKnowledgeBases: 5,
  },
});
```

### Invite Users

```typescript
await synkora.tenants.inviteUser(tenant.id, {
  email: 'user@acme.com',
  role: 'member',
});
```

### Update Settings

```typescript
await synkora.tenants.update(tenant.id, {
  settings: {
    maxAgents: 20,
    features: ['advanced_rag', 'custom_tools'],
  },
});
```

## User Roles

### Built-in Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `owner` | Tenant owner | Full access, billing, delete tenant |
| `admin` | Administrator | Manage users, agents, settings |
| `member` | Team member | Create/manage own agents |
| `viewer` | Read-only | View agents and analytics |

### Custom Roles

```typescript
// Create custom role
await synkora.tenants.createRole(tenant.id, {
  name: 'content_manager',
  permissions: [
    'knowledge_bases:read',
    'knowledge_bases:write',
    'documents:read',
    'documents:write',
  ],
});

// Assign to user
await synkora.tenants.updateUserRole(tenant.id, userId, {
  role: 'content_manager',
});
```

## Resource Limits

### Plan-Based Limits

| Resource | Free | Pro | Enterprise |
|----------|------|-----|------------|
| Agents | 3 | 20 | Unlimited |
| Knowledge Bases | 1 | 10 | Unlimited |
| Documents | 100 | 1000 | Unlimited |
| API Calls/month | 1000 | 50000 | Custom |
| Users | 3 | 20 | Unlimited |

### Enforcement

```typescript
// Limits are enforced at the service level
async function createAgent(tenantId: string, data: CreateAgentRequest) {
  const limits = await getTenantLimits(tenantId);
  const currentCount = await getAgentCount(tenantId);

  if (currentCount >= limits.maxAgents) {
    throw new ResourceLimitExceededError(
      'Agent limit reached. Upgrade your plan for more agents.'
    );
  }

  return await agentRepository.create(tenantId, data);
}
```

## Tenant Switching

### For Users with Multiple Tenants

```typescript
// List user's tenants
const tenants = await synkora.auth.getTenants();

// Switch to a different tenant
const { accessToken } = await synkora.auth.switchTenant({
  tenantId: 'other-tenant-id',
});

// SDK is now authenticated for the new tenant
```

### In the Dashboard

Users can switch tenants via the tenant selector in the navigation.

## Custom Domains

Enterprise tenants can use custom domains:

```typescript
await synkora.tenants.update(tenant.id, {
  settings: {
    customDomain: 'ai.acme.com',
  },
});
```

### DNS Configuration

```
Type: CNAME
Name: ai
Value: custom.synkora.io
```

## Branding

### Custom Branding

```typescript
await synkora.tenants.update(tenant.id, {
  settings: {
    branding: {
      logo: 'https://example.com/logo.png',
      favicon: 'https://example.com/favicon.ico',
      primaryColor: '#0066cc',
      accentColor: '#ff6600',
    },
  },
});
```

### Widget Customization

```typescript
await synkora.agents.updateWidget(agentId, {
  theme: {
    primaryColor: tenant.branding.primaryColor,
    logo: tenant.branding.logo,
  },
});
```

## Tenant Analytics

```typescript
const analytics = await synkora.tenants.getAnalytics(tenant.id, {
  startDate: '2024-01-01',
  endDate: '2024-01-31',
});

console.log(analytics);
// {
//   totalConversations: 5000,
//   totalMessages: 25000,
//   activeAgents: 8,
//   apiCalls: 15000,
//   tokensUsed: 2500000,
//   credits: {
//     used: 500,
//     remaining: 1500,
//   },
// }
```

## Best Practices

### Data Management

1. **Never hardcode tenant IDs** - Always use context
2. **Test isolation** - Verify data cannot leak between tenants
3. **Audit access** - Log all cross-tenant admin actions
4. **Backup per-tenant** - Consider tenant-specific backups

### Performance

1. **Index tenant_id** - All tables should have tenant index
2. **Partition large tables** - By tenant for scale
3. **Cache per-tenant** - Tenant-aware caching
4. **Rate limit per-tenant** - Prevent noisy neighbors

### Security

1. **Validate tenant context** - On every request
2. **Encrypt sensitive data** - Per-tenant encryption keys
3. **Audit logs** - Per-tenant audit trails
4. **Compliance** - Tenant-specific compliance settings

## Related Concepts

- [Security](/docs/concepts/security) - Security and access control
- [Billing](/docs/concepts/billing) - Per-tenant billing
