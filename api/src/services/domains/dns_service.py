"""
DNS Service

Service for DNS verification and record management.
"""

from uuid import UUID

import dns.exception
import dns.resolver
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings

from .domain_service import DomainService


class DNSService:
    """Service for DNS verification and management."""

    def __init__(self, db: AsyncSession):
        """
        Initialize DNS service.

        Args:
            db: Async database session
        """
        self.db = db
        self.domain_service = DomainService(db)
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = 5
        self.resolver.lifetime = 10

    async def verify_custom_domain(self, domain_id: UUID, tenant_id: UUID) -> tuple[bool, str | None]:
        """
        Verify custom domain DNS configuration using TXT + CNAME verification.

        This implements the industry-standard two-step verification:
        1. TXT record proves domain ownership
        2. CNAME record routes traffic to platform

        Args:
            domain_id: Domain ID
            tenant_id: Tenant ID

        Returns:
            Tuple of (is_verified, error_message)
        """
        domain = await self.domain_service.get_domain(domain_id, tenant_id)
        if not domain:
            return False, "Domain not found"

        if not domain.is_custom_domain or not domain.domain:
            return False, "Not a custom domain"

        # The custom domain is what the user owns (e.g., rajumazumder.com)
        custom_domain = domain.domain

        # The platform target is where the agent lives (e.g., test.synkora.ai)
        platform_target = (
            f"{domain.subdomain}.{settings.platform_domain}" if domain.subdomain else settings.platform_domain
        )

        # Step 1: Verify TXT record for ownership at custom domain
        txt_verified, txt_error = self._verify_dns_txt_record(custom_domain, domain.verification_token)
        if not txt_verified:
            return False, f"TXT verification failed: {txt_error}"

        # Step 2: Verify CNAME record routes custom domain to platform subdomain
        cname_verified, cname_error = self._verify_cname_record(custom_domain, platform_target)
        if not cname_verified:
            return False, f"CNAME verification failed: {cname_error}"

        # Both verifications passed
        return True, None

    def get_dns_records(self, domain: str) -> dict[str, list[str]]:
        """
        Get DNS records for a domain.

        Args:
            domain: Domain name

        Returns:
            Dictionary of record types and their values
        """
        records = {"A": [], "AAAA": [], "CNAME": [], "TXT": [], "MX": []}

        for record_type in records.keys():
            try:
                answers = self.resolver.resolve(domain, record_type)
                records[record_type] = [str(rdata) for rdata in answers]
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
                pass
            except Exception:
                pass

        return records

    def get_required_dns_records(
        self, custom_domain: str, subdomain: str | None, verification_token: str, platform_domain: str | None = None
    ) -> list[dict[str, str]]:
        """
        Get required DNS records for custom domain setup.

        Returns both TXT and CNAME records needed for verification:
        1. TXT record: _synkora-verification.<custom-domain> with verification token
        2. CNAME record: <custom-domain> pointing to <platform-subdomain>.<platform-domain>

        Args:
            custom_domain: Custom domain user owns (e.g., 'rajumazumder.com')
            subdomain: Platform subdomain where agent is hosted (e.g., 'test' for 'test.synkora.ai')
            verification_token: Verification token
            platform_domain: Platform domain (defaults to settings)

        Returns:
            List of required DNS records
        """
        if platform_domain is None:
            platform_domain = settings.platform_domain

        # Build the platform target: subdomain.platform_domain
        # e.g., test.synkora.ai (where the agent actually lives)
        platform_target = f"{subdomain}.{platform_domain}" if subdomain else platform_domain

        records = []

        # TXT record for ownership verification at custom domain
        records.append(
            {
                "type": "TXT",
                "name": f"_synkora-verification.{custom_domain}",
                "value": verification_token,
                "ttl": "3600",
                "purpose": "Domain ownership verification",
            }
        )

        # CNAME record to route custom domain traffic to platform subdomain
        # This maps: rajumazumder.com -> test.synkora.ai
        records.append(
            {
                "type": "CNAME",
                "name": custom_domain,
                "value": platform_target,
                "ttl": "3600",
                "purpose": "Route traffic to platform",
            }
        )

        return records

    def check_dns_propagation(self, domain: str, record_type: str, expected_value: str) -> tuple[bool, str | None]:
        """
        Check if DNS record has propagated.

        Args:
            domain: Domain name
            record_type: Record type (A, CNAME, TXT, etc.)
            expected_value: Expected record value

        Returns:
            Tuple of (is_propagated, current_value)
        """
        try:
            answers = self.resolver.resolve(domain, record_type)
            current_values = [str(rdata) for rdata in answers]

            # Check if expected value is in current values
            for value in current_values:
                if expected_value in value or value in expected_value:
                    return True, value

            return False, ", ".join(current_values)
        except dns.resolver.NXDOMAIN:
            return False, "Domain does not exist"
        except dns.resolver.NoAnswer:
            return False, f"No {record_type} records found"
        except dns.exception.Timeout:
            return False, "DNS query timed out"
        except Exception as e:
            return False, f"DNS error: {str(e)}"

    # Private helper methods

    def _verify_dns_txt_record(self, domain: str, verification_token: str) -> tuple[bool, str | None]:
        """
        Verify DNS TXT record for domain ownership.

        Args:
            domain: Domain to verify
            verification_token: Expected verification token

        Returns:
            Tuple of (is_verified, error_message)
        """
        verification_domain = f"_synkora-verification.{domain}"

        try:
            answers = self.resolver.resolve(verification_domain, "TXT")

            for rdata in answers:
                txt_value = str(rdata).strip('"')
                if txt_value == verification_token:
                    return True, None

            return False, f"TXT record found but token mismatch. Expected: {verification_token}"
        except dns.resolver.NXDOMAIN:
            return False, f"TXT record not found at {verification_domain}"
        except dns.resolver.NoAnswer:
            return False, f"No TXT records found at {verification_domain}"
        except dns.exception.Timeout:
            return False, "DNS query timed out. Please try again."
        except Exception as e:
            return False, f"DNS verification error: {str(e)}"

    def _verify_cname_record(self, domain: str, expected_target: str) -> tuple[bool, str | None]:
        """
        Verify CNAME record points to platform subdomain.

        Args:
            domain: Domain to verify
            expected_target: Expected CNAME target

        Returns:
            Tuple of (is_verified, error_message)
        """
        try:
            answers = self.resolver.resolve(domain, "CNAME")

            for rdata in answers:
                cname_value = str(rdata).rstrip(".")
                expected = expected_target.rstrip(".")

                if cname_value == expected or cname_value.endswith(f".{expected}"):
                    return True, None

            return False, f"CNAME record found but target mismatch. Expected: {expected_target}"
        except dns.resolver.NXDOMAIN:
            return False, f"CNAME record not found for {domain}"
        except dns.resolver.NoAnswer:
            return False, f"No CNAME records found for {domain}"
        except dns.exception.Timeout:
            return False, "DNS query timed out. Please try again."
        except Exception:
            return False, "DNS query timed out. Please try again."
