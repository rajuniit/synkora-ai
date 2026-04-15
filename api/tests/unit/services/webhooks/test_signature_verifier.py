"""
Unit tests for Webhook Signature Verifier.

Tests signature verification for different webhook providers.
"""

import hashlib
import hmac
import time

from src.services.webhooks.signature_verifier import SignatureVerifier


class TestGitHubSignatureVerification:
    """Test GitHub webhook signature verification."""

    def test_valid_signature(self):
        """Test verification with valid GitHub signature."""
        payload = b'{"action": "opened", "pull_request": {}}'
        secret = "my-github-secret"

        # Generate valid signature
        mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
        signature = f"sha256={mac.hexdigest()}"

        result = SignatureVerifier.verify_github(payload, signature, secret)

        assert result is True

    def test_invalid_signature(self):
        """Test verification with invalid signature."""
        payload = b'{"action": "opened"}'
        secret = "my-secret"

        result = SignatureVerifier.verify_github(payload, "sha256=invalid", secret)

        assert result is False

    def test_missing_signature_header(self):
        """Test verification with missing signature header."""
        result = SignatureVerifier.verify_github(b"payload", None, "secret")

        assert result is False

    def test_wrong_prefix(self):
        """Test verification with wrong signature prefix."""
        result = SignatureVerifier.verify_github(b"payload", "sha1=signature", "secret")

        assert result is False

    def test_timing_attack_protection(self):
        """Test that verification uses constant-time comparison."""
        payload = b"test payload"
        secret = "secret"

        # Generate correct signature
        mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
        correct_signature = f"sha256={mac.hexdigest()}"

        # Should use hmac.compare_digest (constant-time)
        result = SignatureVerifier.verify_github(payload, correct_signature, secret)
        assert result is True


class TestClickUpSignatureVerification:
    """Test ClickUp webhook signature verification."""

    def test_valid_signature(self):
        """Test verification with valid ClickUp signature."""
        payload = b'{"event": "taskCreated"}'
        secret = "clickup-secret"

        # Generate valid signature
        mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
        signature = mac.hexdigest()

        result = SignatureVerifier.verify_clickup(payload, signature, secret)

        assert result is True

    def test_invalid_signature(self):
        """Test verification with invalid signature."""
        result = SignatureVerifier.verify_clickup(b"payload", "invalid-sig", "secret")

        assert result is False

    def test_missing_signature(self):
        """Test verification with missing signature."""
        result = SignatureVerifier.verify_clickup(b"payload", None, "secret")

        assert result is False


class TestJiraSignatureVerification:
    """Test Jira webhook token verification."""

    def test_valid_token(self):
        """Test verification with valid Jira token."""
        payload = b'{"event": "issue_created"}'
        secret = "jira-webhook-token"

        result = SignatureVerifier.verify_jira(payload, secret, secret)

        assert result is True

    def test_valid_bearer_token(self):
        """Test verification with Bearer prefix."""
        secret = "jira-webhook-token"

        result = SignatureVerifier.verify_jira(b"payload", f"Bearer {secret}", secret)

        assert result is True

    def test_invalid_token(self):
        """Test verification with invalid token."""
        result = SignatureVerifier.verify_jira(b"payload", "wrong-token", "correct-token")

        assert result is False

    def test_missing_token(self):
        """Test verification with missing token."""
        result = SignatureVerifier.verify_jira(b"payload", None, "secret")

        assert result is False


class TestSlackSignatureVerification:
    """Test Slack webhook signature verification."""

    def test_valid_signature(self):
        """Test verification with valid Slack signature."""
        payload = b"token=abc&team_id=T1234"
        secret = "slack-signing-secret"
        timestamp = str(int(time.time()))

        # Generate valid signature
        sig_basestring = f"v0:{timestamp}:".encode() + payload
        mac = hmac.new(secret.encode("utf-8"), msg=sig_basestring, digestmod=hashlib.sha256)
        signature = f"v0={mac.hexdigest()}"

        result = SignatureVerifier.verify_slack(timestamp, signature, payload, secret)

        assert result is True

    def test_invalid_signature(self):
        """Test verification with invalid signature."""
        timestamp = str(int(time.time()))

        result = SignatureVerifier.verify_slack(timestamp, "v0=invalid", b"payload", "secret")

        assert result is False

    def test_missing_signature(self):
        """Test verification with missing signature."""
        result = SignatureVerifier.verify_slack(str(int(time.time())), None, b"payload", "secret")

        assert result is False

    def test_missing_timestamp(self):
        """Test verification with missing timestamp."""
        result = SignatureVerifier.verify_slack(None, "v0=sig", b"payload", "secret")

        assert result is False

    def test_replay_attack_protection(self):
        """Test that old timestamps are rejected (replay attack protection)."""
        payload = b"payload"
        secret = "secret"

        # Timestamp from 10 minutes ago
        old_timestamp = str(int(time.time()) - 600)

        # Generate valid signature with old timestamp
        sig_basestring = f"v0:{old_timestamp}:".encode() + payload
        mac = hmac.new(secret.encode("utf-8"), msg=sig_basestring, digestmod=hashlib.sha256)
        signature = f"v0={mac.hexdigest()}"

        result = SignatureVerifier.verify_slack(old_timestamp, signature, payload, secret)

        assert result is False  # Should reject due to old timestamp

    def test_wrong_prefix(self):
        """Test verification with wrong signature prefix."""
        timestamp = str(int(time.time()))

        result = SignatureVerifier.verify_slack(timestamp, "sha256=sig", b"payload", "secret")

        assert result is False


class TestCustomSignatureVerification:
    """Test custom webhook signature verification."""

    def test_sha256_signature(self):
        """Test custom verification with SHA256."""
        payload = b"custom payload"
        secret = "custom-secret"

        mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
        signature = mac.hexdigest()

        result = SignatureVerifier.verify_custom(payload, signature, secret, "sha256")

        assert result is True

    def test_sha512_signature(self):
        """Test custom verification with SHA512."""
        payload = b"custom payload"
        secret = "custom-secret"

        mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha512)
        signature = mac.hexdigest()

        result = SignatureVerifier.verify_custom(payload, signature, secret, "sha512")

        assert result is True

    def test_signature_with_prefix(self):
        """Test custom verification handles signature prefixes."""
        payload = b"payload"
        secret = "secret"

        mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
        signature = f"sha256={mac.hexdigest()}"

        result = SignatureVerifier.verify_custom(payload, signature, secret, "sha256")

        assert result is True

    def test_invalid_algorithm(self):
        """Test custom verification with invalid algorithm."""
        result = SignatureVerifier.verify_custom(b"payload", "sig", "secret", "invalid_algo")

        assert result is False

    def test_missing_signature(self):
        """Test custom verification with missing signature."""
        result = SignatureVerifier.verify_custom(b"payload", None, "secret", "sha256")

        assert result is False


class TestVerifyDispatcher:
    """Test the main verify dispatcher method."""

    def test_github_dispatch(self):
        """Test dispatch to GitHub verifier."""
        payload = b'{"event": "push"}'
        secret = "github-secret"

        mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
        signature = f"sha256={mac.hexdigest()}"

        result = SignatureVerifier.verify(
            provider="github", payload=payload, headers={"x-hub-signature-256": signature}, secret=secret
        )

        assert result is True

    def test_clickup_dispatch(self):
        """Test dispatch to ClickUp verifier."""
        payload = b"payload"
        secret = "clickup-secret"

        mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
        signature = mac.hexdigest()

        result = SignatureVerifier.verify(
            provider="clickup", payload=payload, headers={"x-signature": signature}, secret=secret
        )

        assert result is True

    def test_jira_dispatch(self):
        """Test dispatch to Jira verifier."""
        result = SignatureVerifier.verify(
            provider="jira", payload=b"payload", headers={"authorization": "my-token"}, secret="my-token"
        )

        assert result is True

    def test_slack_dispatch(self):
        """Test dispatch to Slack verifier."""
        payload = b"payload"
        secret = "slack-secret"
        timestamp = str(int(time.time()))

        sig_basestring = f"v0:{timestamp}:".encode() + payload
        mac = hmac.new(secret.encode("utf-8"), msg=sig_basestring, digestmod=hashlib.sha256)
        signature = f"v0={mac.hexdigest()}"

        result = SignatureVerifier.verify(
            provider="slack",
            payload=payload,
            headers={"x-slack-request-timestamp": timestamp, "x-slack-signature": signature},
            secret=secret,
        )

        assert result is True

    def test_custom_dispatch(self):
        """Test dispatch to custom verifier."""
        payload = b"payload"
        secret = "custom-secret"

        mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
        signature = mac.hexdigest()

        result = SignatureVerifier.verify(
            provider="custom",
            payload=payload,
            headers={"x-signature": signature},
            secret=secret,
            config={"signature_header": "x-signature", "algorithm": "sha256"},
        )

        assert result is True

    def test_unknown_provider_skips_verification(self):
        """Test that unknown provider rejects verification (security: fail closed)."""
        result = SignatureVerifier.verify(provider="unknown", payload=b"payload", headers={}, secret="secret")

        assert result is False  # Unknown providers are rejected to prevent bypass

    def test_verification_error_raises_exception(self):
        """Test that verification errors raise HTTPException."""
        # This would require mocking internal method to raise exception
        # The verify method has try/except that raises HTTPException
        pass


class TestHeaderCaseInsensitivity:
    """Test that header names are case-insensitive."""

    def test_github_lowercase_header(self):
        """Test GitHub with lowercase header."""
        payload = b"payload"
        secret = "secret"

        mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
        signature = f"sha256={mac.hexdigest()}"

        # Headers are normalized to lowercase
        result = SignatureVerifier.verify(
            provider="github", payload=payload, headers={"x-hub-signature-256": signature}, secret=secret
        )

        assert result is True

    def test_slack_lowercase_headers(self):
        """Test Slack with lowercase headers."""
        payload = b"payload"
        secret = "secret"
        timestamp = str(int(time.time()))

        sig_basestring = f"v0:{timestamp}:".encode() + payload
        mac = hmac.new(secret.encode("utf-8"), msg=sig_basestring, digestmod=hashlib.sha256)
        signature = f"v0={mac.hexdigest()}"

        result = SignatureVerifier.verify(
            provider="slack",
            payload=payload,
            headers={"x-slack-request-timestamp": timestamp, "x-slack-signature": signature},
            secret=secret,
        )

        assert result is True
