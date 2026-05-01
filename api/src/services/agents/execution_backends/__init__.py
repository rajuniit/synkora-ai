"""Execution backend factory."""

from .base import BaseExecutionBackend
from .celery_backend import CeleryBackend
from .cloud_run_backend import CloudRunBackend
from .do_functions_backend import DOFunctionsBackend
from .lambda_backend import LambdaBackend

__all__ = [
    "BaseExecutionBackend",
    "CeleryBackend",
    "LambdaBackend",
    "CloudRunBackend",
    "DOFunctionsBackend",
    "get_execution_backend",
]

_VALID_BACKENDS = {"celery", "lambda", "cloud_run", "do_functions"}


def get_execution_backend(name: str) -> BaseExecutionBackend:
    """
    Return a configured execution backend instance.

    Credentials and endpoint config are read from platform-level environment
    variables (AWSConfig / GCPConfig / DOConfig in settings). No per-agent
    credentials are stored or used — operators configure the platform, tenants
    only choose which backend their agent uses.

    Args:
        name: Backend name — "celery", "lambda", "cloud_run", or "do_functions"

    Returns:
        Configured backend instance

    Raises:
        ValueError: Unknown backend name
    """
    name = name.lower()

    if name == "celery":
        return CeleryBackend()

    if name == "lambda":
        return LambdaBackend()

    if name == "cloud_run":
        return CloudRunBackend()

    if name == "do_functions":
        return DOFunctionsBackend()

    raise ValueError(f"Unknown execution backend: '{name}'. Valid values: {sorted(_VALID_BACKENDS)}")
