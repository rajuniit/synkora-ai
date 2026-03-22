---
sidebar_position: 2
---

# Backend Architecture

The Synkora backend is built with FastAPI and follows clean architecture principles.

## Directory Structure

```
api/src/
├── app.py                 # FastAPI application entry
├── celery_app.py          # Celery configuration
├── config/
│   └── settings.py        # Application settings
├── core/
│   ├── database.py        # Database connections
│   ├── cache.py           # Redis caching
│   ├── websocket.py       # WebSocket handling
│   └── exceptions.py      # Custom exceptions
├── models/
│   ├── base.py            # Base model
│   ├── agent.py           # Agent models
│   ├── knowledge_base.py  # KB models
│   └── ...
├── schemas/
│   ├── agent.py           # Pydantic schemas
│   └── ...
├── controllers/
│   ├── agents/            # Agent endpoints
│   ├── knowledge_bases/   # KB endpoints
│   └── ...
├── services/
│   ├── agents/
│   │   ├── agent_manager.py
│   │   ├── chat_stream_service.py
│   │   └── llm_client.py
│   ├── knowledge_base/
│   │   ├── rag_service.py
│   │   └── ...
│   └── ...
├── middleware/
│   ├── auth.py            # JWT/API key auth
│   ├── rate_limit.py      # Rate limiting
│   └── ...
└── tasks/
    └── ...                # Celery tasks
```

## Key Services

### Agent Manager

Orchestrates agent lifecycle:

```python
class AgentManager:
    async def create(self, data: CreateAgentRequest) -> Agent
    async def chat(self, agent_id: str, message: str) -> ChatResponse
    async def chat_stream(self, agent_id: str, message: str) -> AsyncIterator
```

### Chat Stream Service

Handles SSE streaming:

```python
class ChatStreamService:
    async def stream_response(
        self,
        agent: Agent,
        messages: List[Message],
        context: Dict,
    ) -> AsyncIterator[StreamChunk]
```

### LLM Client

Unified interface to LLM providers via LiteLLM:

```python
class LLMClient:
    async def chat(
        self,
        model: str,
        messages: List[Dict],
        **kwargs,
    ) -> ChatResponse

    async def chat_stream(
        self,
        model: str,
        messages: List[Dict],
        **kwargs,
    ) -> AsyncIterator
```

### RAG Service

Handles retrieval augmented generation:

```python
class RAGService:
    async def search(
        self,
        kb_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[SearchResult]

    async def get_context(
        self,
        agent: Agent,
        query: str,
    ) -> str
```

## Middleware

### Authentication

```python
@router.get("/agents")
async def list_agents(
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    return await agent_service.list(tenant_id)
```

### Rate Limiting

```python
@router.post("/chat")
@rate_limit(requests=60, window=60)
async def chat(request: ChatRequest):
    ...
```

## Database Patterns

### Repository Pattern

```python
class AgentRepository:
    async def create(self, data: CreateAgentRequest) -> Agent
    async def get(self, id: str) -> Optional[Agent]
    async def update(self, id: str, data: UpdateAgentRequest) -> Agent
    async def delete(self, id: str) -> None
    async def list(self, tenant_id: str, **filters) -> List[Agent]
```

### Multi-Tenancy

```python
class TenantMixin:
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)

class Agent(BaseModel, TenantMixin):
    __tablename__ = "agents"
    # ...
```

## Error Handling

```python
@app.exception_handler(SynkoraException)
async def synkora_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )
```
