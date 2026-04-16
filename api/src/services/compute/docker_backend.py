"""
DockerComputeSession — runs agent commands inside a platform-managed Docker container.

The platform provisions one container per agent (named synkora-agent-<agent_id>).
Users need zero configuration — no SSH, no credentials, no host key setup.
The container is kept alive with `sleep infinity` and reused across conversations.

All Docker SDK calls are blocking; they run in a thread pool via asyncio.get_event_loop().run_in_executor
so the async event loop is never blocked.
"""

import asyncio
import io
import logging
import os
import tarfile
from typing import Any

logger = logging.getLogger(__name__)

_WORKSPACE = "/workspace"


class DockerComputeSession:
    """
    ComputeSession backed by a platform-managed Docker container.

    The caller is responsible for ensuring the container is running
    before creating this session (handled by the resolver).
    """

    def __init__(
        self,
        container_id: str,
        base_path: str = _WORKSPACE,
        max_output_chars: int = 8000,
    ) -> None:
        self._container_id = container_id
        self._base_path = base_path
        self._max_output_chars = max_output_chars
        self._client: Any = None  # docker.DockerClient, lazy-init

    # ------------------------------------------------------------------
    # ComputeSession interface
    # ------------------------------------------------------------------

    @property
    def base_path(self) -> str | None:
        return self._base_path

    @property
    def is_remote(self) -> bool:
        return False  # Runs on the same host as the API

    async def exec_command(
        self,
        command: list[str],
        cwd: str | None = None,
        timeout: int = 300,
        input_text: str | None = None,
    ) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        try:
            container = await self._get_container(loop)
            workdir = cwd or self._base_path

            def _run() -> tuple[int, bytes]:
                result = container.exec_run(
                    cmd=command,
                    workdir=workdir,
                    demux=False,
                )
                return result.exit_code, result.output or b""

            exit_code, raw_output = await asyncio.wait_for(
                loop.run_in_executor(None, _run),
                timeout=timeout,
            )
            stdout = raw_output.decode("utf-8", errors="replace")
            if len(stdout) > self._max_output_chars:
                stdout = stdout[: self._max_output_chars] + "\n[OUTPUT TRUNCATED]"
            return {
                "success": exit_code == 0,
                "output": stdout if exit_code == 0 else "",
                "error": stdout if exit_code != 0 else "",
                "return_code": exit_code,
            }
        except TimeoutError:
            return {
                "success": False,
                "output": "",
                "error": f"Command timed out after {timeout}s",
                "return_code": -1,
            }
        except Exception as e:
            logger.error(f"DockerComputeSession.exec_command error: {e}")
            return {"success": False, "output": "", "error": str(e), "return_code": -1}

    async def read_file(
        self,
        path: str,
        start_line: int = 1,
        max_lines: int = 200,
    ) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        try:
            container = await self._get_container(loop)

            def _read() -> bytes:
                stream, _ = container.get_archive(path)
                buf = io.BytesIO()
                for chunk in stream:
                    buf.write(chunk)
                buf.seek(0)
                with tarfile.open(fileobj=buf) as tar:
                    member = tar.getmembers()[0]
                    fh = tar.extractfile(member)
                    return fh.read() if fh else b""

            raw = await loop.run_in_executor(None, _read)
            content = raw.decode("utf-8", errors="replace")
            all_lines = content.splitlines(keepends=True)
            selected = all_lines[start_line - 1 : start_line - 1 + max_lines]
            return {
                "success": True,
                "content": "".join(selected),
                "total_lines": len(all_lines),
                "error": "",
            }
        except Exception as e:
            logger.debug(f"DockerComputeSession.read_file error for {path}: {e}")
            return {"success": False, "content": "", "total_lines": 0, "error": str(e)}

    async def write_file(self, path: str, content: str) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        try:
            container = await self._get_container(loop)
            encoded = content.encode("utf-8")
            parent = os.path.dirname(path) or "/"
            filename = os.path.basename(path)

            def _write() -> None:
                # Ensure parent directory exists
                container.exec_run(["mkdir", "-p", parent])
                # Build a tar archive containing just the file
                buf = io.BytesIO()
                with tarfile.open(fileobj=buf, mode="w") as tar:
                    info = tarfile.TarInfo(name=filename)
                    info.size = len(encoded)
                    tar.addfile(info, io.BytesIO(encoded))
                buf.seek(0)
                container.put_archive(parent, buf.getvalue())

            await loop.run_in_executor(None, _write)
            return {"success": True, "error": ""}
        except Exception as e:
            logger.error(f"DockerComputeSession.write_file error for {path}: {e}")
            return {"success": False, "error": str(e)}

    async def list_dir(self, path: str) -> dict[str, Any]:
        result = await self.exec_command(["ls", "-la", "--time-style=long-iso", path])
        if not result["success"]:
            return {"success": False, "entries": [], "error": result["error"]}
        entries = []
        for line in result["output"].splitlines():
            parts = line.split()
            if len(parts) < 9 or line.startswith("total"):
                continue
            name = parts[-1]
            if name in (".", ".."):
                continue
            is_dir = parts[0].startswith("d")
            try:
                size = int(parts[4])
            except (ValueError, IndexError):
                size = 0
            entries.append({"name": name, "is_dir": is_dir, "size": size})
        return {"success": True, "entries": entries, "error": ""}

    async def create_dir(self, path: str) -> dict[str, Any]:
        result = await self.exec_command(["mkdir", "-p", path])
        return {"success": result["success"], "error": result.get("error", "")}

    async def file_exists(self, path: str) -> bool:
        result = await self.exec_command(["test", "-e", path])
        return result["return_code"] == 0

    async def close(self) -> None:
        """Release the Docker client connection (container lifecycle managed by DockerEphemeralSession)."""
        if self._client:
            loop = asyncio.get_event_loop()
            try:
                await loop.run_in_executor(None, self._client.close)
            except Exception:
                pass
            self._client = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_container(self, loop: asyncio.AbstractEventLoop) -> Any:
        """Return the docker container object, initialising the client lazily."""
        import docker  # type: ignore[import-untyped]

        if self._client is None:
            self._client = await loop.run_in_executor(None, docker.from_env)
        return await loop.run_in_executor(None, self._client.containers.get, self._container_id)
