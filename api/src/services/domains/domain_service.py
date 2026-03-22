"""
Domain Service

Service for managing agent domains, subdomains, and custom domain configurations.
"""

import os
import secrets
import string
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.models.agent_domain import AgentDomain


class DomainService:
    """Service for managing agent domains."""

    def __init__(self, db: AsyncSession):
        """
        Initialize domain service.

        Args:
            db: Async database session
        """
        self.db = db
        self.platform_domain = os.getenv("PLATFORM_DOMAIN", "localhost")

    async def create_domain(
        self,
        agent_id: UUID,
        tenant_id: UUID,
        subdomain: str | None = None,
        custom_domain: str | None = None,
        chat_page_config: dict | None = None,
    ) -> AgentDomain:
        """
        Create a new domain for an agent.

        Args:
            agent_id: Agent ID
            tenant_id: Tenant ID
            subdomain: Optional subdomain (auto-generated if not provided)
            custom_domain: Optional custom domain
            chat_page_config: Optional chat page configuration

        Returns:
            Created agent domain

        Raises:
            ValueError: If subdomain/domain already exists or is invalid
        """
        # Verify agent exists and belongs to tenant
        agent = await self._get_agent(agent_id, tenant_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # Generate subdomain if not provided
        if not subdomain:
            subdomain = await self._generate_subdomain(agent.agent_name)

        # Validate subdomain
        subdomain = self._validate_subdomain(subdomain)

        # Check if subdomain already exists
        if await self._subdomain_exists(subdomain):
            raise ValueError(f"Subdomain '{subdomain}' already exists")

        # Validate custom domain if provided
        if custom_domain:
            custom_domain = self._validate_custom_domain(custom_domain)
            if await self._custom_domain_exists(custom_domain):
                raise ValueError(f"Custom domain '{custom_domain}' already exists")

        # Create domain
        domain = AgentDomain(
            agent_id=agent_id,
            tenant_id=tenant_id,
            subdomain=subdomain,
            domain=custom_domain,
            is_custom_domain=bool(custom_domain),
            is_verified=False,  # Custom domains need verification
            verification_token=self._generate_verification_token() if custom_domain else None,
            verification_method="DNS" if custom_domain else None,
            ssl_enabled=True,
            status="pending" if custom_domain else "active",
            chat_page_config=chat_page_config or {},
        )

        self.db.add(domain)
        await self.db.commit()
        await self.db.refresh(domain)

        return domain

    async def get_domain(self, domain_id: UUID, tenant_id: UUID) -> AgentDomain | None:
        """
        Get domain by ID.

        Args:
            domain_id: Domain ID
            tenant_id: Tenant ID

        Returns:
            Agent domain or None
        """
        result = await self.db.execute(
            select(AgentDomain).where(AgentDomain.id == domain_id, AgentDomain.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_domain_by_agent(self, agent_id: UUID, tenant_id: UUID) -> AgentDomain | None:
        """
        Get domain by agent ID.

        Args:
            agent_id: Agent ID
            tenant_id: Tenant ID

        Returns:
            Agent domain or None
        """
        result = await self.db.execute(
            select(AgentDomain).where(AgentDomain.agent_id == agent_id, AgentDomain.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_domains(self, agent_id: UUID, tenant_id: UUID) -> list[AgentDomain]:
        """
        List all domains for an agent.

        Args:
            agent_id: Agent ID
            tenant_id: Tenant ID

        Returns:
            List of agent domains
        """
        result = await self.db.execute(
            select(AgentDomain)
            .where(AgentDomain.agent_id == agent_id, AgentDomain.tenant_id == tenant_id)
            .order_by(AgentDomain.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_domain_by_subdomain(self, subdomain: str) -> AgentDomain | None:
        """
        Get domain by subdomain.

        Args:
            subdomain: Subdomain

        Returns:
            Agent domain or None
        """
        result = await self.db.execute(select(AgentDomain).where(AgentDomain.subdomain == subdomain))
        return result.scalar_one_or_none()

    async def get_domain_by_custom_domain(self, custom_domain: str) -> AgentDomain | None:
        """
        Get domain by custom domain.

        Args:
            custom_domain: Custom domain

        Returns:
            Agent domain or None
        """
        result = await self.db.execute(select(AgentDomain).where(AgentDomain.domain == custom_domain))
        return result.scalar_one_or_none()

    async def update_domain(
        self,
        domain_id: UUID,
        tenant_id: UUID,
        subdomain: str | None = None,
        custom_domain: str | None = None,
        is_custom_domain: bool | None = None,
        chat_page_config: dict | None = None,
    ) -> AgentDomain:
        """
        Update domain configuration.

        Args:
            domain_id: Domain ID
            tenant_id: Tenant ID
            subdomain: Optional new subdomain
            custom_domain: Optional new custom domain
            is_custom_domain: Whether this is a custom domain
            chat_page_config: Optional chat page configuration

        Returns:
            Updated agent domain

        Raises:
            ValueError: If domain not found or custom domain already exists
        """
        domain = await self.get_domain(domain_id, tenant_id)
        if not domain:
            raise ValueError(f"Domain {domain_id} not found")

        # Track if DNS reconfiguration is needed
        needs_reverification = False

        # Update subdomain if provided
        if subdomain is not None:
            # Clean and validate subdomain
            new_subdomain = subdomain.strip() if subdomain else ""

            # Subdomain is required - cannot be empty
            if not new_subdomain:
                raise ValueError("Subdomain is required and cannot be empty")

            # Validate the new subdomain format
            new_subdomain = self._validate_subdomain(new_subdomain)

            # Check if different from current and not already taken by another domain
            if new_subdomain != domain.subdomain:
                if await self._subdomain_exists(new_subdomain):
                    raise ValueError(f"Subdomain '{new_subdomain}' already exists")
                domain.subdomain = new_subdomain
                needs_reverification = True

        # Update custom domain if provided
        if custom_domain is not None:
            custom_domain = self._validate_custom_domain(custom_domain) if custom_domain else None

            # Check if different from current and not already taken
            if custom_domain != domain.domain:
                if custom_domain and await self._custom_domain_exists(custom_domain):
                    raise ValueError(f"Custom domain '{custom_domain}' already exists")

                domain.domain = custom_domain
                needs_reverification = True

        # Update is_custom_domain flag if provided
        if is_custom_domain is not None:
            domain.is_custom_domain = is_custom_domain
            if is_custom_domain and not domain.verification_token:
                domain.verification_token = self._generate_verification_token()
                domain.verification_method = "DNS"

        # If domain/subdomain changed, reset verification
        if needs_reverification:
            domain.is_verified = False
            if domain.is_custom_domain:
                domain.verification_token = self._generate_verification_token()
                domain.verification_method = "DNS"
                domain.status = "pending"

        # Update chat page config if provided
        if chat_page_config is not None:
            domain.chat_page_config = chat_page_config

        domain.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(domain)

        return domain

    async def delete_domain(self, domain_id: UUID, tenant_id: UUID) -> bool:
        """
        Delete domain.

        Args:
            domain_id: Domain ID
            tenant_id: Tenant ID

        Returns:
            True if deleted, False if not found
        """
        domain = await self.get_domain(domain_id, tenant_id)
        if not domain:
            return False

        await self.db.delete(domain)
        await self.db.commit()

        return True

    async def verify_domain(self, domain_id: UUID, tenant_id: UUID) -> AgentDomain:
        """
        Mark domain as verified.

        Args:
            domain_id: Domain ID
            tenant_id: Tenant ID

        Returns:
            Updated agent domain

        Raises:
            ValueError: If domain not found
        """
        domain = await self.get_domain(domain_id, tenant_id)
        if not domain:
            raise ValueError(f"Domain {domain_id} not found")

        domain.is_verified = True
        domain.status = "active"
        domain.last_verified_at = datetime.now(UTC)
        domain.error_message = None

        await self.db.commit()
        await self.db.refresh(domain)

        return domain

    async def mark_verification_failed(self, domain_id: UUID, tenant_id: UUID, error_message: str) -> AgentDomain:
        """
        Mark domain verification as failed.

        Args:
            domain_id: Domain ID
            tenant_id: Tenant ID
            error_message: Error message

        Returns:
            Updated agent domain

        Raises:
            ValueError: If domain not found
        """
        domain = await self.get_domain(domain_id, tenant_id)
        if not domain:
            raise ValueError(f"Domain {domain_id} not found")

        domain.status = "failed"
        domain.error_message = error_message

        await self.db.commit()
        await self.db.refresh(domain)

        return domain

    # Private helper methods

    async def _get_agent(self, agent_id: UUID, tenant_id: UUID) -> Agent | None:
        """Get agent by ID and tenant."""
        result = await self.db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def _generate_subdomain(self, agent_name: str) -> str:
        """
        Generate a unique subdomain from agent name.

        Args:
            agent_name: Agent name

        Returns:
            Generated subdomain
        """
        # Convert to lowercase and replace spaces/special chars with hyphens
        base = agent_name.lower()
        base = "".join(c if c.isalnum() else "-" for c in base)
        base = "-".join(filter(None, base.split("-")))  # Remove consecutive hyphens

        # Ensure it starts with alphanumeric
        if base and not base[0].isalnum():
            base = "agent-" + base

        # Limit length
        base = base[:50]

        # Check if exists, add random suffix if needed
        subdomain = base
        attempts = 0
        while await self._subdomain_exists(subdomain) and attempts < 10:
            suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
            subdomain = f"{base}-{suffix}"
            attempts += 1

        return subdomain

    def _validate_subdomain(self, subdomain: str) -> str:
        """
        Validate and normalize subdomain.

        Args:
            subdomain: Subdomain to validate

        Returns:
            Normalized subdomain

        Raises:
            ValueError: If subdomain is invalid
        """
        subdomain = subdomain.lower().strip()

        # Check length
        if len(subdomain) < 3 or len(subdomain) > 63:
            raise ValueError("Subdomain must be between 3 and 63 characters")

        # Check format (alphanumeric and hyphens, must start/end with alphanumeric)
        if not subdomain[0].isalnum() or not subdomain[-1].isalnum():
            raise ValueError("Subdomain must start and end with alphanumeric character")

        for char in subdomain:
            if not (char.isalnum() or char == "-"):
                raise ValueError("Subdomain can only contain alphanumeric characters and hyphens")

        # Check for reserved subdomains
        reserved = ["www", "api", "admin", "app", "mail", "ftp", "localhost", "staging", "dev"]
        if subdomain in reserved:
            raise ValueError(f"Subdomain '{subdomain}' is reserved")

        return subdomain

    def _validate_custom_domain(self, domain: str) -> str:
        """
        Validate custom domain.

        Args:
            domain: Domain to validate

        Returns:
            Normalized domain

        Raises:
            ValueError: If domain is invalid
        """
        domain = domain.lower().strip()

        # Basic domain validation
        if len(domain) < 4 or len(domain) > 253:
            raise ValueError("Domain must be between 4 and 253 characters")

        # Check for valid domain format
        parts = domain.split(".")
        if len(parts) < 2:
            raise ValueError("Domain must have at least two parts (e.g., example.com)")

        for part in parts:
            if not part or len(part) > 63:
                raise ValueError("Each domain part must be between 1 and 63 characters")

            if not part[0].isalnum() or not part[-1].isalnum():
                raise ValueError("Each domain part must start and end with alphanumeric character")

        return domain

    async def _subdomain_exists(self, subdomain: str) -> bool:
        """Check if subdomain already exists."""
        result = await self.db.execute(select(AgentDomain).where(AgentDomain.subdomain == subdomain))
        return result.scalar_one_or_none() is not None

    async def _custom_domain_exists(self, domain: str) -> bool:
        """Check if custom domain already exists."""
        result = await self.db.execute(select(AgentDomain).where(AgentDomain.domain == domain))
        return result.scalar_one_or_none() is not None

    def _generate_verification_token(self) -> str:
        """Generate a verification token for domain ownership."""
        return secrets.token_urlsafe(32)
