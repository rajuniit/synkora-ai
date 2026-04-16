"""
RemoteSSHComputeSession — executes compute operations on a remote server via SSH.

Requires the optional ``asyncssh`` package (``pip install asyncssh``).
If asyncssh is not installed the class is still importable but any method
call raises ``RuntimeError`` with a clear install message.

The SSH connection is lazily established on the first operation and cached
for the lifetime of the session object. Call ``close()`` when done.

Security notes:
  - ``known_hosts_content=None`` accepts any host key (development default).
    Platform admins can set SSH known_hosts content in Platform Settings (DB) to
    enable strict host-key verification in production.
  - Credentials (private key or password) are decrypted from the DB at
    session construction time and held in memory only for the session lifetime.
"""

import logging
import os
import shlex
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import flag
_ASYNCSSH_AVAILABLE: bool | None = None


def _ensure_asyncssh() -> None:
    """Raise RuntimeError if asyncssh is not installed."""
    global _ASYNCSSH_AVAILABLE
    if _ASYNCSSH_AVAILABLE is None:
        try:
            import asyncssh  # noqa: F401

            _ASYNCSSH_AVAILABLE = True
        except ImportError:
            _ASYNCSSH_AVAILABLE = False
    if not _ASYNCSSH_AVAILABLE:
        raise RuntimeError("asyncssh is not installed. Install it with: pip install asyncssh>=2.14.0")


class RemoteSSHComputeSession:
    """
    SSH-based compute session for remote servers or containers.

    All command and file-system operations are proxied over an SSH connection.
    Files are transferred using SFTP; commands run via SSH exec.
    """

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = "root",
        auth_type: str = "key",
        credentials: str | None = None,
        base_path: str = "/tmp/agent_workspace",
        timeout: int = 300,
        max_output_chars: int = 8000,
        known_hosts_content: str | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._auth_type = auth_type
        self._credentials = credentials
        self._base_path = base_path
        self._timeout = timeout
        self._max_output_chars = max_output_chars
        self._known_hosts_content = known_hosts_content
        self._conn: Any = None  # asyncssh.SSHClientConnection

    @property
    def base_path(self) -> str | None:
        return self._base_path

    @property
    def is_remote(self) -> bool:
        return True

    async def _get_conn(self) -> Any:
        """Lazily open and cache the SSH connection."""
        _ensure_asyncssh()
        import asyncssh

        if self._conn is None or self._conn.is_closed():
            # Parse known_hosts content stored in DB, or disable checking (dev default).
            known_hosts: Any = None
            if self._known_hosts_content:
                known_hosts = asyncssh.import_known_hosts(self._known_hosts_content)

            kwargs: dict[str, Any] = {
                "host": self._host,
                "port": self._port,
                "username": self._username,
                "connect_timeout": 30,
                "known_hosts": known_hosts,
            }

            if self._auth_type == "key" and self._credentials:
                kwargs["client_keys"] = [asyncssh.import_private_key(self._credentials)]
                kwargs["password"] = None
            elif self._auth_type == "password" and self._credentials:
                kwargs["password"] = self._credentials
                kwargs["client_keys"] = []

            self._conn = await asyncssh.connect(**kwargs)
            logger.info(f"SSH connection established to {self._username}@{self._host}:{self._port}")

        return self._conn

    async def close(self) -> None:
        """Close the underlying SSH connection."""
        if self._conn and not self._conn.is_closed():
            self._conn.close()
            self._conn = None
            logger.debug(f"SSH connection closed to {self._host}")

    # ------------------------------------------------------------------
    # ComputeSession interface
    # ------------------------------------------------------------------

    async def exec_command(
        self,
        command: list[str],
        cwd: str | None = None,
        timeout: int | None = None,
        input_text: str | None = None,
    ) -> dict[str, Any]:
        """Execute a command on the remote host."""
        timeout = timeout or self._timeout
        cwd = cwd or self._base_path

        # Build a shell string: cd to cwd, then run the command.
        # We quote each argument to handle spaces/special chars.
        cmd_str = "cd {} && {}".format(
            shlex.quote(cwd),
            " ".join(shlex.quote(c) for c in command),
        )

        try:
            conn = await self._get_conn()
            result = await conn.run(cmd_str, input=input_text, timeout=timeout)
            stdout = result.stdout or ""
            if len(stdout) > self._max_output_chars:
                stdout = stdout[: self._max_output_chars] + "\n[OUTPUT TRUNCATED]"
            exit_code = result.exit_status if result.exit_status is not None else 0
            return {
                "success": exit_code == 0,
                "output": stdout,
                "error": (result.stderr or "") if exit_code != 0 else "",
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
            logger.error(f"SSH exec_command error on {self._host}: {e}")
            return {"success": False, "output": "", "error": str(e), "return_code": -1}

    async def read_file(
        self,
        path: str,
        start_line: int = 1,
        max_lines: int = 200,
    ) -> dict[str, Any]:
        """Read a range of lines from a remote file using sed + wc."""
        end_line = start_line + max_lines - 1
        try:
            conn = await self._get_conn()
            # Get total line count and selected lines in a single SSH round-trip.
            cmd = "wc -l {p} && sed -n '{s},{e}p' {p}".format(
                p=shlex.quote(path),
                s=start_line,
                e=end_line,
            )
            result = await conn.run(cmd, timeout=self._timeout)
            if result.exit_status != 0:
                return {
                    "success": False,
                    "content": "",
                    "total_lines": 0,
                    "error": result.stderr or f"Cannot read {path}",
                }
            raw = result.stdout or ""
            # First line of output is "  N  /path/to/file", rest is file content.
            first_newline = raw.index("\n") if "\n" in raw else len(raw)
            header = raw[:first_newline]
            content = raw[first_newline + 1 :] if first_newline < len(raw) else ""
            total_lines = 0
            try:
                total_lines = int(header.strip().split()[0])
            except (ValueError, IndexError):
                pass
            return {
                "success": True,
                "content": content,
                "total_lines": total_lines,
                "error": "",
            }
        except Exception as e:
            return {"success": False, "content": "", "total_lines": 0, "error": str(e)}

    async def write_file(self, path: str, content: str) -> dict[str, Any]:
        """Write content to a remote file using SFTP."""
        try:
            conn = await self._get_conn()
            # Ensure parent directory exists
            parent = os.path.dirname(path)
            if parent:
                await conn.run(f"mkdir -p {shlex.quote(parent)}", timeout=30)
            async with conn.start_sftp_client() as sftp, await sftp.open(path, "w") as fh:
                await fh.write(content)
            return {"success": True, "error": ""}
        except Exception as e:
            logger.error(f"SSH write_file error on {self._host}: {e}")
            return {"success": False, "error": str(e)}

    async def list_dir(self, path: str) -> dict[str, Any]:
        """List a remote directory using SFTP readdir."""
        try:
            _ensure_asyncssh()
            import asyncssh

            conn = await self._get_conn()
            async with conn.start_sftp_client() as sftp:
                raw_entries = await sftp.readdir(path)
            entries = []
            for entry in raw_entries:
                if entry.filename in (".", ".."):
                    continue
                entries.append(
                    {
                        "name": entry.filename,
                        "is_dir": (entry.attrs.type == asyncssh.FILEXFER_TYPE_DIRECTORY),
                        "size": entry.attrs.size or 0,
                    }
                )
            return {"success": True, "entries": entries, "error": ""}
        except Exception as e:
            return {"success": False, "entries": [], "error": str(e)}

    async def create_dir(self, path: str) -> dict[str, Any]:
        """Create a remote directory."""
        result = await self.exec_command(["mkdir", "-p", path], timeout=30)
        return {"success": result["success"], "error": result["error"]}

    async def file_exists(self, path: str) -> bool:
        """Check if a path exists on the remote host using SFTP stat."""
        try:
            conn = await self._get_conn()
            async with conn.start_sftp_client() as sftp:
                await sftp.stat(path)
            return True
        except Exception:
            return False
