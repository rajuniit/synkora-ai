"""
TenantComputeConfig — per-tenant S3 workspace overrides.

The compute container is a shared platform resource (COMPUTE_CONTAINER_ID).
Per-tenant config only covers which S3 bucket stores their agent workspaces.
If s3_bucket / s3_region are not set, the platform defaults
(COMPUTE_S3_BUCKET / COMPUTE_S3_REGION) are used.
"""

from sqlalchemy import Column, String, UniqueConstraint

from src.models.base import BaseModel, TenantMixin


class TenantComputeConfig(BaseModel, TenantMixin):
    __tablename__ = "tenant_compute_configs"

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tenant_compute_configs_tenant_id"),)

    # S3 workspace — falls back to platform COMPUTE_S3_BUCKET / COMPUTE_S3_REGION if null
    s3_bucket = Column(String(300), nullable=True, comment="S3 bucket for this tenant's agent workspaces")
    s3_region = Column(String(50), nullable=True, comment="AWS region for the S3 bucket")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "s3_bucket": self.s3_bucket,
            "s3_region": self.s3_region,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<TenantComputeConfig(tenant={self.tenant_id})>"
