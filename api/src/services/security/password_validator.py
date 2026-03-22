"""
Password validation service.

Provides secure password policy enforcement.
"""

import re
from typing import ClassVar


class PasswordValidator:
    """
    Validates passwords against security requirements.

    SECURITY: Enforces strong password policy:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """

    MIN_LENGTH: ClassVar[int] = 12
    MAX_LENGTH: ClassVar[int] = 128

    # Common passwords that should be rejected
    COMMON_PASSWORDS: ClassVar[set[str]] = {
        "password123",
        "password1234",
        "qwerty123456",
        "123456789012",
        "admin123456",
        "letmein12345",
        "welcome12345",
        "changeme1234",
    }

    @classmethod
    def validate(cls, password: str, email: str | None = None) -> tuple[bool, str | None]:
        """
        Validate a password against security requirements.

        Args:
            password: The password to validate
            email: Optional email to check password doesn't contain it

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check length
        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters long"

        if len(password) > cls.MAX_LENGTH:
            return False, f"Password must be at most {cls.MAX_LENGTH} characters long"

        # Check for uppercase letter
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        # Check for lowercase letter
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        # Check for digit
        if not re.search(r"\d", password):
            return False, "Password must contain at least one number"

        # Check for special character
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\[\]\\;'`~_+=\-/]", password):
            return False, "Password must contain at least one special character"

        # Check against common passwords
        if password.lower() in cls.COMMON_PASSWORDS:
            return False, "This password is too common. Please choose a more unique password"

        # Check if password contains email parts
        if email:
            email_parts = email.lower().split("@")
            username = email_parts[0]
            if len(username) >= 4 and username in password.lower():
                return False, "Password should not contain your email address"

        return True, None

    @classmethod
    def get_requirements_text(cls) -> str:
        """Get human-readable password requirements."""
        return (
            f"Password must be at least {cls.MIN_LENGTH} characters and include: "
            "uppercase letter, lowercase letter, number, and special character."
        )


def validate_password(password: str, email: str | None = None) -> tuple[bool, str | None]:
    """Convenience function to validate a password."""
    return PasswordValidator.validate(password, email)
