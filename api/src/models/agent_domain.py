"""
Agent Domain Model

Database model for storing custom domain configurations for agents.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel, TenantMixin


class AgentDomain(BaseModel, TenantMixin):
    """
    Agent Domain model for storing custom domain configurations.

    Attributes:
        agent_id: Reference to the agent
        domain: Custom domain name (e.g., support.example.com)
        subdomain: Subdomain on platform (e.g., myagent.synkora.ai)
        is_custom_domain: Whether using custom domain or subdomain
        is_verified: Whether domain ownership is verified
        verification_token: Token for domain verification
        verification_method: Method used for verification (DNS, file, etc.)
        ssl_enabled: Whether SSL is enabled for the domain
        ssl_certificate: SSL certificate details
        dns_records: Required DNS records for setup
        status: Domain status (pending, active, failed, etc.)
        last_verified_at: Last verification timestamp
        error_message: Error message if verification failed
    """

    __tablename__ = "agent_domains"

    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True, comment="Agent ID"
    )

    domain = Column(String(255), nullable=True, unique=True, index=True, comment="Custom domain name")

    subdomain = Column(
        String(255), nullable=False, unique=True, index=True, comment="Subdomain on platform (e.g., myagent.synkora.ai)"
    )

    is_custom_domain = Column(Boolean, nullable=False, default=False, comment="Whether using custom domain")

    is_verified = Column(Boolean, nullable=False, default=False, comment="Whether domain is verified")

    verification_token = Column(String(255), nullable=True, comment="Token for domain verification")

    verification_method = Column(String(50), nullable=True, comment="Verification method (DNS, file, etc.)")

    ssl_enabled = Column(Boolean, nullable=False, default=True, comment="Whether SSL is enabled")

    ssl_certificate = Column(Text, nullable=True, comment="SSL certificate details (JSON)")

    dns_records = Column(Text, nullable=True, comment="Required DNS records (JSON)")

    status = Column(
        String(50), nullable=False, default="pending", comment="Domain status (pending, active, failed, etc.)"
    )

    last_verified_at = Column(DateTime, nullable=True, comment="Last verification timestamp")

    error_message = Column(Text, nullable=True, comment="Error message if verification failed")

    chat_page_config = Column(JSONB, nullable=True, comment="Chat page customization configuration")

    # Relationships
    agent = relationship("Agent", back_populates="domains", lazy="selectin")

    def __repr__(self) -> str:
        """String representation of agent domain."""
        domain_name = self.domain if self.is_custom_domain else self.subdomain
        return f"<AgentDomain(id={self.id}, domain='{domain_name}', verified={self.is_verified})>"

    @property
    def public_url(self) -> str:
        """Get the public URL for this domain."""
        if self.is_custom_domain and self.is_verified and self.domain:
            protocol = "https" if self.ssl_enabled else "http"
            return f"{protocol}://{self.domain}"
        else:
            # Default to subdomain
            return f"https://{self.subdomain}"

    def to_dict(self, exclude: set[str] | None = None) -> dict:
        """
        Convert to dictionary.

        Args:
            exclude: Fields to exclude

        Returns:
            Dictionary representation
        """
        exclude = exclude or set()
        data = super().to_dict(exclude=exclude)

        # Add computed fields
        data["public_url"] = self.public_url

        return data
