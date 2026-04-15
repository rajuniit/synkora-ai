"""
ComputeBackend — abstract interface for compute backend providers.

A backend manages the lifecycle of compute sessions:
  checkout_session() → allocates a session (start container, invoke Lambda, etc.)
  return_session()   → releases it (stop container, clean up, return to pool)

All backends produce a ComputeSession that command/file tools use uniformly.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.services.compute.session import ComputeSession


class ComputeBackend(ABC):
    """
    Abstract compute backend.

    Implementations: DockerComputeBackend, LambdaComputeBackend,
    FargateComputeBackend, GCPCloudRunComputeBackend, K8sJobComputeBackend.
    """

    @abstractmethod
    async def checkout_session(
        self,
        agent_id: str,
        tenant_id: str,
        conversation_id: str,
    ) -> "ComputeSession":
        """
        Allocate a compute session for a conversation.

        Called once at conversation start. The returned session is stored
        on RuntimeContext and reused for all tool calls in that conversation.
        """

    @abstractmethod
    async def return_session(self, session: "ComputeSession") -> None:
        """
        Release a compute session after the conversation ends.

        Called in the finally block of the streaming generator so cleanup
        always happens even if the conversation errors out mid-stream.
        """

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Backend identifier string (e.g. 'docker', 'aws_lambda')."""
