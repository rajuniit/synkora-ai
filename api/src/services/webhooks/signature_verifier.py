"""Webhook signature verification for different providers."""

import hashlib
import hmac

from fastapi import HTTPException, status


class SignatureVerifier:
    """Verifies webhook signatures from different providers."""

    @staticmethod
    def verify_github(payload: bytes, signature_header: str, secret: str) -> bool:
        """
        Verify GitHub webhook signature.

        Args:
            payload: Raw request body
            signature_header: X-Hub-Signature-256 header value
            secret: Webhook secret

        Returns:
            bool: True if signature is valid
        """
        import logging

        logger = logging.getLogger(__name__)

        if not signature_header:
            logger.warning("GitHub webhook: no signature header provided")
            return False

        # GitHub sends signature as 'sha256=<signature>'
        if not signature_header.startswith("sha256="):
            logger.warning("GitHub webhook: invalid signature format")
            return False

        signature = signature_header.split("=")[1]

        # Calculate expected signature
        mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
        expected_signature = mac.hexdigest()

        # SECURITY: Never log secrets, signatures, or payload contents
        # Only log the verification result

        # Constant-time comparison to prevent timing attacks
        result = hmac.compare_digest(signature, expected_signature)
        if not result:
            logger.warning("GitHub webhook signature verification failed")
        return result

    @staticmethod
    def verify_clickup(payload: bytes, signature_header: str, secret: str) -> bool:
        """
        Verify ClickUp webhook signature.

        Args:
            payload: Raw request body
            signature_header: X-Signature header value
            secret: Webhook secret

        Returns:
            bool: True if signature is valid
        """
        if not signature_header:
            return False

        # ClickUp uses HMAC-SHA256
        mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
        expected_signature = mac.hexdigest()

        return hmac.compare_digest(signature_header, expected_signature)

    @staticmethod
    def verify_jira(payload: bytes, token_header: str, secret: str) -> bool:
        """
        Verify Jira webhook token.

        Args:
            payload: Raw request body
            token_header: Authorization or custom header value
            secret: Webhook secret/token

        Returns:
            bool: True if token is valid
        """
        if not token_header:
            return False

        # Jira typically uses a bearer token or custom token
        # Remove 'Bearer ' prefix if present
        token = token_header.replace("Bearer ", "")

        return hmac.compare_digest(token, secret)

    @staticmethod
    def verify_slack(timestamp: str, signature_header: str, payload: bytes, secret: str) -> bool:
        """
        Verify Slack webhook signature.

        Args:
            timestamp: X-Slack-Request-Timestamp header
            signature_header: X-Slack-Signature header value
            payload: Raw request body
            secret: Signing secret

        Returns:
            bool: True if signature is valid
        """
        if not signature_header or not timestamp:
            return False

        # Check if timestamp is recent (within 5 minutes) to prevent replay attacks
        import time

        try:
            current_timestamp = int(time.time())
            request_timestamp = int(timestamp)
        except (ValueError, OverflowError):
            return False

        if abs(current_timestamp - request_timestamp) > 60 * 5:
            return False

        # Slack sends signature as 'v0=<signature>'
        if not signature_header.startswith("v0="):
            return False

        signature = signature_header.split("=")[1]

        # Create base string
        sig_basestring = f"v0:{timestamp}:".encode() + payload

        # Calculate expected signature
        mac = hmac.new(secret.encode("utf-8"), msg=sig_basestring, digestmod=hashlib.sha256)
        expected_signature = mac.hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    @staticmethod
    def verify_gitlab(token_header: str, secret: str) -> bool:
        """
        Verify GitLab webhook token.

        GitLab uses a simple token comparison via the X-Gitlab-Token header.

        Args:
            token_header: X-Gitlab-Token header value
            secret: Webhook secret/token

        Returns:
            bool: True if token is valid
        """
        if not token_header:
            return False

        # GitLab uses constant-time comparison for the token
        return hmac.compare_digest(token_header, secret)

    @staticmethod
    def verify_custom(payload: bytes, signature_header: str, secret: str, algorithm: str = "sha256") -> bool:
        """
        Verify custom webhook signature with configurable algorithm.

        Args:
            payload: Raw request body
            signature_header: Signature header value
            secret: Webhook secret
            algorithm: Hash algorithm (sha256, sha512, etc.)

        Returns:
            bool: True if signature is valid
        """
        if not signature_header:
            return False

        # SECURITY: Only allow known safe hash algorithms — no user-controlled getattr
        ALLOWED_ALGORITHMS = {"sha256": hashlib.sha256, "sha512": hashlib.sha512, "sha1": hashlib.sha1}
        hash_func = ALLOWED_ALGORITHMS.get(algorithm)
        if not hash_func:
            return False

        try:
            # Calculate expected signature
            mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hash_func)
            expected_signature = mac.hexdigest()

            # Remove common prefixes
            signature = signature_header
            for prefix in [f"{algorithm}=", "sha256=", "sha512="]:
                if signature.startswith(prefix):
                    signature = signature.split("=", 1)[1]
                    break

            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False

    @classmethod
    def verify(
        cls, provider: str, payload: bytes, headers: dict[str, str], secret: str, config: dict | None = None
    ) -> bool:
        """
        Verify webhook signature based on provider.

        Args:
            provider: Provider name (github, clickup, jira, slack, custom)
            payload: Raw request body
            headers: Request headers
            secret: Webhook secret
            config: Additional configuration for custom providers

        Returns:
            bool: True if signature is valid

        Raises:
            HTTPException: If signature verification fails
        """
        config = config or {}

        try:
            if provider == "github":
                signature = headers.get("x-hub-signature-256", "")
                return cls.verify_github(payload, signature, secret)

            elif provider == "clickup":
                signature = headers.get("x-signature", "")
                return cls.verify_clickup(payload, signature, secret)

            elif provider == "jira":
                token = headers.get("authorization", "") or headers.get("x-jira-webhook-token", "")
                return cls.verify_jira(payload, token, secret)

            elif provider == "slack":
                timestamp = headers.get("x-slack-request-timestamp", "")
                signature = headers.get("x-slack-signature", "")
                return cls.verify_slack(timestamp, signature, payload, secret)

            elif provider == "gitlab":
                token = headers.get("x-gitlab-token", "")
                return cls.verify_gitlab(token, secret)

            elif provider == "sentry":
                # Sentry sends HMAC-SHA256 in the sentry-hook-signature header
                signature = headers.get("sentry-hook-signature", "")
                if not signature:
                    return False
                mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
                return hmac.compare_digest(signature, mac.hexdigest())

            elif provider == "custom":
                signature_header = config.get("signature_header", "x-signature")
                algorithm = config.get("algorithm", "sha256")
                signature = headers.get(signature_header.lower(), "")
                return cls.verify_custom(payload, signature, secret, algorithm)

            else:
                # Unknown provider — reject rather than silently bypass verification
                import logging

                logging.getLogger(__name__).warning(f"Signature verification skipped: unknown provider '{provider}'")
                return False

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Signature verification failed: {str(e)}"
            )
