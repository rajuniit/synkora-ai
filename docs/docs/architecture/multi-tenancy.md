---
sidebar_position: 8
---

# Multi-Tenancy Design

Data isolation and tenant management architecture.

## Isolation Strategy

Synkora uses **shared database, shared schema** with **row-level isolation**:

```
┌──────────────────────────────────────────────────────┐
│                   PostgreSQL                          │
│  ┌─────────────────────────────────────────────────┐ │
│  │                   agents                         │ │
│  │  tenant_id │ id │ name │ ...                    │ │
│  │  ──────────┼────┼──────┼────                    │ │
│  │  tenant-1  │ a1 │ Bot  │ ...                    │ │
│  │  tenant-2  │ a2 │ Bot  │ ...                    │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

## Implementation

### Base Model

```python
class TenantMixin:
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False, index=True)

class Agent(BaseModel, TenantMixin):
    __tablename__ = "agents"
    id = Column(UUID, primary_key=True)
    name = Column(String)
    # ...
```

### Query Filtering

```python
class TenantAwareRepository:
    def __init__(self, session: Session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def list(self) -> List[Model]:
        return await self.session.execute(
            select(self.model).where(self.model.tenant_id == self.tenant_id)
        )

    async def get(self, id: str) -> Optional[Model]:
        result = await self.session.execute(
            select(self.model)
            .where(self.model.id == id)
            .where(self.model.tenant_id == self.tenant_id)
        )
        return result.scalar_one_or_none()
```

### Middleware

```python
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    # Extract tenant from JWT or API key
    token = request.headers.get("Authorization")
    tenant_id = extract_tenant_id(token)

    # Store in request state
    request.state.tenant_id = tenant_id

    return await call_next(request)

def get_tenant_id(request: Request) -> str:
    return request.state.tenant_id
```

### Controller Usage

```python
@router.get("/agents")
async def list_agents(
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    repo = AgentRepository(db, tenant_id)
    return await repo.list()
```

## Tenant Context

### JWT Token

```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "roles": ["admin"],
  "exp": 1234567890
}
```

### API Key

```python
# API keys are scoped to a tenant
class APIKey(BaseModel):
    tenant_id = Column(UUID, ForeignKey("tenants.id"))
    scopes = Column(ARRAY(String))
```

## Cross-Tenant Operations

For admin operations:

```python
@router.get("/admin/agents")
async def list_all_agents(
    current_user: User = Depends(require_super_admin),
):
    # Super admin can access all tenants
    return await agent_repo.list_all()
```

## Best Practices

1. **Always filter by tenant_id** in queries
2. **Index tenant_id** on all tenant-scoped tables
3. **Validate tenant access** in every endpoint
4. **Audit cross-tenant** admin operations
5. **Test isolation** thoroughly
