"""
Base Pydantic models for request schema validation.
"""

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """
    Base model that rejects unknown fields (prevents mass-assignment attacks).

    Use this as the base class for all request schemas that write directly to
    the database (agent create/update, user update, role change, billing,
    database connection create, etc.).
    """

    model_config = ConfigDict(extra="forbid")
