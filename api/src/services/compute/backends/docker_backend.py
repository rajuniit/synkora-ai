"""
DockerComputeBackend — single persistent platform container, S3 workspace.

Design:
  - One container runs permanently on the platform (COMPUTE_CONTAINER_ID env var).
  - All tenants and agents share the same container.
  - Each agent gets its own isolated directory inside the container:
      /workspace/{tenant_id}/{agent_id}/
  - Workspace files are persisted in S3 between conversations:
      s3://{bucket}/{tenant_id}/{agent_id}/{file}
  - On checkout: download S3 files → inject into container directory.
  - On return:   extract container directory → upload to S3 → remove the directory.
"""

import asyncio
import io
import logging
import tarfile
from typing import Any

from src.services.compute.backends.base import ComputeBackend

logger = logging.getLogger(__name__)


class DockerComputeBackend(ComputeBackend):

    def __init__(
        self,
        tenant_id: str,
        s3_bucket: str | None = None,
        s3_region: str | None = None,
    ) -> None:
        self._tenant_id = str(tenant_id)
        self._s3_bucket = s3_bucket
        self._s3_region = s3_region

    @property
    def backend_type(self) -> str:
        return "docker"

    def _container_id(self) -> str:
        from src.config.settings import settings
        cid = settings.compute_container_id
        if not cid:
            raise RuntimeError(
                "COMPUTE_CONTAINER_ID is not set. "
                "Start the platform container and set this env var."
            )
        return cid

    def _agent_path(self, agent_id: str) -> str:
        return f"/workspace/{self._tenant_id}/{agent_id}"

    # ──────────────────────────────────────────────────────────────────────────

    async def checkout_session(
        self,
        agent_id: str,
        tenant_id: str,
        conversation_id: str,
    ) -> "DockerManagedSession":
        loop = asyncio.get_event_loop()
        container_id = self._container_id()
        agent_path = self._agent_path(agent_id)

        # Create the per-agent directory and sync workspace from S3
        await loop.run_in_executor(None, self._prepare_agent_dir, container_id, agent_path)
        await loop.run_in_executor(None, self._sync_from_s3, container_id, agent_id, agent_path)

        logger.info(
            f"Compute checkout: tenant={self._tenant_id[:8]} "
            f"agent={agent_id[:8]} path={agent_path}"
        )

        from src.services.compute.docker_backend import DockerComputeSession

        return DockerManagedSession(
            container_id=container_id,
            agent_id=str(agent_id),
            tenant_id=self._tenant_id,
            agent_path=agent_path,
            base_session=DockerComputeSession(
                container_id=container_id,
                base_path=agent_path,
                max_output_chars=8000,
            ),
            backend=self,
        )

    async def return_session(self, session: "DockerManagedSession") -> None:
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(
                None, self._sync_to_s3, session.container_id, session.agent_id, session.agent_path
            )
        except Exception as e:
            logger.error(f"S3 sync-out failed for agent {session.agent_id[:8]}: {e}")

        # Clean up agent directory from shared container
        await loop.run_in_executor(None, self._remove_agent_dir, session.container_id, session.agent_path)
        logger.info(f"Compute return: cleaned {session.agent_path}")

    # ──────────────────────────────────────────────────────────────────────────
    # Container helpers (sync — run in executor)
    # ──────────────────────────────────────────────────────────────────────────

    def _prepare_agent_dir(self, container_id: str, agent_path: str) -> None:
        import docker  # type: ignore[import-untyped]
        client = docker.from_env()
        container = client.containers.get(container_id)
        container.exec_run(["mkdir", "-p", agent_path])

    def _remove_agent_dir(self, container_id: str, agent_path: str) -> None:
        try:
            import docker  # type: ignore[import-untyped]
            client = docker.from_env()
            container = client.containers.get(container_id)
            container.exec_run(["rm", "-rf", agent_path])
        except Exception as e:
            logger.debug(f"_remove_agent_dir {agent_path}: {e}")

    def _sync_from_s3(self, container_id: str, agent_id: str, agent_path: str) -> None:
        if not self._s3_bucket:
            return
        import boto3  # type: ignore[import-untyped]

        import docker  # type: ignore[import-untyped]

        s3 = boto3.client("s3", region_name=self._s3_region)
        prefix = f"{self._tenant_id}/{agent_id}/"
        response = s3.list_objects_v2(Bucket=self._s3_bucket, Prefix=prefix)
        objects = response.get("Contents", [])
        if not objects:
            return

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for obj in objects:
                rel_path = obj["Key"][len(prefix):]
                if not rel_path or rel_path.endswith("/"):
                    continue
                data = s3.get_object(Bucket=self._s3_bucket, Key=obj["Key"])["Body"].read()
                info = tarfile.TarInfo(name=rel_path)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        buf.seek(0)

        client = docker.from_env()
        container = client.containers.get(container_id)
        container.put_archive(agent_path, buf.getvalue())
        logger.debug(f"Synced {len(objects)} files from S3 → {agent_path}")

    def _sync_to_s3(self, container_id: str, agent_id: str, agent_path: str) -> None:
        if not self._s3_bucket:
            return
        import boto3  # type: ignore[import-untyped]
        import docker.errors  # type: ignore[import-untyped]

        import docker  # type: ignore[import-untyped]

        client = docker.from_env()
        try:
            container = client.containers.get(container_id)
            stream, _ = container.get_archive(agent_path)
        except docker.errors.NotFound:
            logger.warning(f"Container {container_id[:12]} not found during S3 sync-out")
            return
        except Exception as e:
            logger.warning(f"get_archive failed for {agent_path}: {e}")
            return

        raw = io.BytesIO()
        for chunk in stream:
            raw.write(chunk)
        raw.seek(0)

        s3 = boto3.client("s3", region_name=self._s3_region)
        prefix = f"{self._tenant_id}/{agent_id}/"
        # Strip the last path component (agent_id dir name) from tar member names
        dir_name = agent_path.rstrip("/").split("/")[-1]
        uploaded = 0

        with tarfile.open(fileobj=raw) as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                rel = member.name
                if rel.startswith(f"{dir_name}/"):
                    rel = rel[len(dir_name) + 1:]
                elif rel.startswith("./"):
                    rel = rel[2:]
                if not rel or rel.startswith("/"):
                    continue
                fh = tar.extractfile(member)
                if fh:
                    s3.put_object(Bucket=self._s3_bucket, Key=f"{prefix}{rel}", Body=fh.read())
                    uploaded += 1

        logger.debug(f"Synced {uploaded} files from {agent_path} → S3")


# ──────────────────────────────────────────────────────────────────────────────


class DockerManagedSession:
    def __init__(
        self,
        container_id: str,
        agent_id: str,
        tenant_id: str,
        agent_path: str,
        base_session: Any,
        backend: DockerComputeBackend,
    ) -> None:
        self.container_id = container_id
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.agent_path = agent_path
        self._base_session = base_session
        self._backend = backend

    @property
    def base_path(self) -> str | None:
        return self.agent_path

    @property
    def is_remote(self) -> bool:
        return False

    async def exec_command(self, *args, **kwargs) -> dict[str, Any]:
        return await self._base_session.exec_command(*args, **kwargs)

    async def read_file(self, *args, **kwargs) -> dict[str, Any]:
        return await self._base_session.read_file(*args, **kwargs)

    async def write_file(self, *args, **kwargs) -> dict[str, Any]:
        return await self._base_session.write_file(*args, **kwargs)

    async def list_dir(self, *args, **kwargs) -> dict[str, Any]:
        return await self._base_session.list_dir(*args, **kwargs)

    async def create_dir(self, *args, **kwargs) -> dict[str, Any]:
        return await self._base_session.create_dir(*args, **kwargs)

    async def file_exists(self, *args, **kwargs) -> bool:
        return await self._base_session.file_exists(*args, **kwargs)

    async def close(self) -> None:
        try:
            await self._backend.return_session(self)
        except Exception as e:
            logger.error(f"DockerManagedSession.close error: {e}")
