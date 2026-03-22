# Claude Skills for Synkora API

This document captures patterns, conventions, and lessons learned to prevent common mistakes.

## 1. RuntimeContext Attributes

**ALWAYS check before using:**

```python
@dataclass
class RuntimeContext:
    tenant_id: uuid.UUID
    agent_id: uuid.UUID
    db_session: Session          # NOT 'db'
    llm_client: Any | None
    conversation_id: uuid.UUID | None
    message_id: uuid.UUID | None
    user_id: uuid.UUID | None    # Authenticated user (from chat controller)
    shared_state: dict[str, Any] | None
```

**Common mistakes:**
- `runtime_context.db` → WRONG, use `runtime_context.db_session`
- `runtime_context.account` → DOESN'T EXIST, use `runtime_context.user_id`

**Before fixing RuntimeContext errors, check ALL internal tools:**
```bash
# Find all files using wrong attribute
grep -r "runtime_context\.db[^_]" src/services/agents/internal_tools/
```

---

## 2. Tool Wrapper Pattern

**Standard pattern for tool wrappers:**

```python
async def internal_tool_wrapper(config: dict[str, Any] | None = None, **kwargs):
    runtime_context = config.get("_runtime_context") if config else None
    return await internal_tool_function(
        db=runtime_context.db_session if runtime_context else None,
        tenant_id=str(runtime_context.tenant_id) if runtime_context else None,
        # Get LLM parameters from kwargs
        param1=kwargs.get("param1"),
        param2=kwargs.get("param2", default_value),
    )
```

**Critical rules:**
1. First parameter MUST be `config: dict[str, Any] | None = None`
2. Use `**kwargs` for all LLM-provided parameters
3. If tool schema has a parameter named `config`, rename it to `task_config` in the schema to avoid conflict
4. Access LLM parameters via `kwargs.get("param_name")`

---

## 3. Model Locations

**Common models and their locations:**

| Model | Import Path |
|-------|-------------|
| Account | `from src.models.tenant import Account` |
| Agent | `from src.models.agent import Agent` |
| AgentTool | `from src.models.agent_tool import AgentTool` |
| ScheduledTask | `from src.models.scheduled_task import ScheduledTask` |
| Tenant | `from src.models.tenant import Tenant` |

**Rule:** Always verify import paths with `grep "class ModelName" src/models/`

---

## 4. Service Method Names

**SchedulerService methods:**

| Method | Purpose |
|--------|---------|
| `create_task()` | Create cron-based scheduled task |
| `create_agent_task()` | Create interval-based scheduled task |
| `update_task()` | Update existing task |
| `delete_task()` | Delete task |
| `toggle_task()` | Toggle active status |
| `list_tasks()` | List tasks for tenant |
| `get_task()` | Get single task by ID |

**Rule:** Always verify method names with `grep "def " path/to/service.py`

---

## 5. Authentication Flow

**How user identity flows through the system:**

1. **Controller** gets `current_account` via `Depends(get_current_account)`
2. **Controller** passes `user_id=str(current_account.id)` to service
3. **Service** sets `user_id` in `RuntimeContext`
4. **Tool wrapper** reads `runtime_context.user_id`

**Auth middleware imports:**
```python
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id
from src.models.tenant import Account
```

---

## 6. Tool Registration Checklist

Before creating a new tool:

- [ ] Check existing similar tools for patterns
- [ ] Verify all RuntimeContext attributes you'll use exist
- [ ] Verify all service methods you'll call exist
- [ ] If schema has `config` parameter, rename to `task_config`
- [ ] Test with actual tool execution, not just registration

---

## 7. AgentTool Assignment

**Tools must be explicitly assigned to agents:**

1. Tools are registered globally in `adk_tools.py`
2. Agents get tools via `AgentTool` records in database
3. Enable tools via capabilities: `POST /agents/{id}/capabilities/{capability_id}`
4. Or individually: `POST /agents/{id}/tools`

**Discovery tools are auto-included** via `ALWAYS_INCLUDE_TOOLS` in `tool_filter.py`

---

## 8. Pre-Change Verification Commands

**Before modifying any code, run these:**

```bash
# Check class/dataclass attributes
grep -A 20 "class ClassName" path/to/file.py

# Check method names in a service
grep "def " path/to/service.py

# Find model location
grep -r "class ModelName" src/models/

# Check existing tool wrapper patterns
grep -A 10 "async def internal_.*_wrapper" src/services/agents/tool_registrations/

# Check imports in similar files
head -30 path/to/similar_file.py
```

---

## 9. Common Capability IDs

| Capability ID | Tools Included |
|---------------|----------------|
| `email` | `internal_send_email`, `internal_gmail_*` |
| `scheduling` | `internal_create_scheduled_task`, `internal_create_cron_scheduled_task`, etc. |
| `communication` | `internal_slack_*` |
| `social-media` | `internal_youtube_*`, `internal_hackernews_*` |
| `code-github` | `internal_git_*`, `internal_pr_review_*` |

---

## 10. Debugging Tool Execution

**Key log patterns to watch:**

```
# Tool execution started
🔧 [execute_tool] Tool 'tool_name' - runtime_context provided

# Success
Function tool_name completed successfully

# Errors
ERROR in scheduler_tools: Error creating...
❌ TypeError in tool execution
```

**Common errors:**
- `'RuntimeContext' object has no attribute 'X'` → Wrong attribute name
- `got multiple values for keyword argument 'config'` → Schema param conflicts with wrapper param
- `'Service' object has no attribute 'method'` → Wrong method name

---

## 11. Scheduled Agent Tasks

**How scheduled agent tasks work:**

1. **LLM calls** `internal_create_cron_scheduled_task` with:
   - `name`: Task name
   - `cron_expression`: When to run (e.g., "0 7 * * *" for 7 AM daily)
   - `prompt`: Instructions for the agent when task runs

2. **Wrapper auto-injects** into `task_config`:
   - `agent_id` from `runtime_context.agent_id`
   - `prompt` from LLM-provided parameter

3. **Task stored** in `scheduled_tasks` table with `task_type="agent_task"`

4. **Celery Beat** triggers task → Celery Worker executes → `scheduled_tasks.py:execute_scheduled_task()`

5. **Execution flow** in `scheduled_tasks.py`:
   - Loads `agent_id` from `task.config`
   - Loads `prompt` from `task.config`
   - Calls agent via `ChatStreamService.stream_agent_response()`
   - Agent executes prompt using its tools

**Required task_config fields for agent_task:**
```python
task.config = {
    "agent_id": "uuid-string",  # Auto-injected by wrapper
    "prompt": "Search YouTube for AI news and summarize"  # From LLM
}
```

**File locations:**
- Tool wrappers: `src/services/agents/tool_registrations/scheduler_tools_registry.py`
- Task execution: `src/tasks/scheduled_tasks.py`
- Scheduler service: `src/services/scheduler/scheduler_service.py`
