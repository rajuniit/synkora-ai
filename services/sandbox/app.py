"""
synkora-sandbox — secure code execution microservice.

All agents share this service. Each agent gets an isolated workspace directory:
    /workspaces/{tenant_id}/{agent_id}/

Workspaces are ephemeral — no persistence, no S3. If the service restarts, workspaces
are gone. That is intentional.

Endpoints:
  POST   /v1/exec     — execute a command in agent workspace
  GET    /v1/files    — read a file
  PUT    /v1/files    — write a file
  GET    /v1/dir      — list a directory
  POST   /v1/dir      — create a directory
  GET    /v1/exists   — check file/dir existence
  DELETE /v1/workspace — remove workspace directory (called on session close)
  GET    /health      — liveness check

Auth: X-Sandbox-Key header must match SANDBOX_API_KEY env var (if set).
"""

import asyncio
import logging
import os
import shutil
import subprocess
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="synkora-sandbox", version="1.0.0")

WORKSPACES_BASE = Path(os.getenv("WORKSPACES_BASE", "/workspaces"))
SANDBOX_API_KEY = os.getenv("SANDBOX_API_KEY")


def _check_auth(key: str | None) -> None:
    if SANDBOX_API_KEY and key != SANDBOX_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid sandbox key")


def _workspace(tenant_id: str, agent_id: str) -> Path:
    return WORKSPACES_BASE / tenant_id / agent_id


def _safe_path(workspace: Path, rel: str) -> Path:
    """Resolve path, ensuring it stays inside the workspace directory."""
    if os.path.isabs(rel):
        try:
            rel = str(Path(rel).relative_to(workspace))
        except ValueError:
            rel = rel.lstrip("/")
    target = (workspace / rel).resolve()
    if not str(target).startswith(str(workspace.resolve())):
        raise HTTPException(status_code=400, detail="Path escapes workspace")
    return target


# ─────────────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────────────

class ExecRequest(BaseModel):
    tenant_id: str
    agent_id: str
    command: list[str]
    cwd: str | None = None
    timeout: int = 300
    env: dict[str, str] | None = None

class FileWriteRequest(BaseModel):
    tenant_id: str
    agent_id: str
    path: str
    content: str

class DirRequest(BaseModel):
    tenant_id: str
    agent_id: str
    path: str = "."


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/exec")
async def exec_command(
    req: ExecRequest,
    x_sandbox_key: str | None = Header(default=None),
):
    _check_auth(x_sandbox_key)
    workspace = _workspace(req.tenant_id, req.agent_id)
    workspace.mkdir(parents=True, exist_ok=True)

    cwd = str(_safe_path(workspace, req.cwd)) if req.cwd else str(workspace)
    env = {**os.environ, **(req.env or {})}

    try:
        proc = await asyncio.create_subprocess_exec(
            *req.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            env=env,
        )
        raw, _ = await asyncio.wait_for(proc.communicate(), timeout=req.timeout)
        output = raw.decode("utf-8", errors="replace")
        if len(output) > 8000:
            output = output[:8000] + "\n[OUTPUT TRUNCATED]"
        return_code = proc.returncode or 0
        return {
            "success": return_code == 0,
            "output": output if return_code == 0 else "",
            "error": output if return_code != 0 else "",
            "return_code": return_code,
        }
    except asyncio.TimeoutError:
        return {"success": False, "output": "", "error": f"Command timed out after {req.timeout}s", "return_code": -1}
    except Exception as e:
        logger.error(f"exec error: {e}")
        return {"success": False, "output": "", "error": str(e), "return_code": -1}


@app.get("/v1/files")
async def read_file(
    tenant_id: str,
    agent_id: str,
    path: str,
    start_line: int = 1,
    max_lines: int = 200,
    x_sandbox_key: str | None = Header(default=None),
):
    _check_auth(x_sandbox_key)
    workspace = _workspace(tenant_id, agent_id)
    target = _safe_path(workspace, path)
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines(keepends=True)
        selected = lines[start_line - 1: start_line - 1 + max_lines]
        return {"success": True, "content": "".join(selected), "total_lines": len(lines), "error": ""}
    except Exception as e:
        return {"success": False, "content": "", "total_lines": 0, "error": str(e)}


@app.put("/v1/files")
async def write_file(
    req: FileWriteRequest,
    x_sandbox_key: str | None = Header(default=None),
):
    _check_auth(x_sandbox_key)
    workspace = _workspace(req.tenant_id, req.agent_id)
    target = _safe_path(workspace, req.path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(req.content, encoding="utf-8")
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/v1/dir")
async def list_dir(
    tenant_id: str,
    agent_id: str,
    path: str = ".",
    x_sandbox_key: str | None = Header(default=None),
):
    _check_auth(x_sandbox_key)
    workspace = _workspace(tenant_id, agent_id)
    target = _safe_path(workspace, path)
    try:
        entries = [
            {"name": item.name, "is_dir": item.is_dir(), "size": item.stat().st_size if item.is_file() else 0}
            for item in sorted(target.iterdir())
        ]
        return {"success": True, "entries": entries, "error": ""}
    except Exception as e:
        return {"success": False, "entries": [], "error": str(e)}


@app.post("/v1/dir")
async def create_dir(
    req: DirRequest,
    x_sandbox_key: str | None = Header(default=None),
):
    _check_auth(x_sandbox_key)
    workspace = _workspace(req.tenant_id, req.agent_id)
    target = _safe_path(workspace, req.path)
    try:
        target.mkdir(parents=True, exist_ok=True)
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/v1/exists")
async def file_exists(
    tenant_id: str,
    agent_id: str,
    path: str,
    x_sandbox_key: str | None = Header(default=None),
):
    _check_auth(x_sandbox_key)
    workspace = _workspace(tenant_id, agent_id)
    target = _safe_path(workspace, path)
    return {"exists": target.exists()}


@app.delete("/v1/workspace")
async def workspace_delete(
    tenant_id: str,
    agent_id: str,
    x_sandbox_key: str | None = Header(default=None),
):
    """Remove agent workspace directory. Called on session close."""
    _check_auth(x_sandbox_key)
    workspace = _workspace(tenant_id, agent_id)
    try:
        if workspace.exists():
            shutil.rmtree(workspace)
        return {"success": True}
    except Exception as e:
        logger.error(f"workspace_delete error: {e}")
        return {"success": False, "error": str(e)}
