#!/usr/bin/env python3
"""
Non-interactive super admin creation — driven entirely by environment variables.

Environment variables:
    ADMIN_EMAIL     (required) - Email address for the super admin
    ADMIN_PASSWORD  (required) - Password (min 8 chars)
    ADMIN_NAME      (optional) - Full name, default "Admin"
    TENANT_NAME     (optional) - Organisation name, default "My Organisation"

This script mirrors create_super_admin.py but reads from env vars instead of
interactive prompts, making it suitable for CI/CD and automated installers.
"""

import os
import re
import sys

# PYTHONPATH=/app/api is set in Dockerfile.dev — no manual path manipulation needed.
# Importing create_super_admin works because both files live in /app/api (WORKDIR).
from src.core.database import get_db
from create_super_admin import create_super_admin


def _require_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"[x] Environment variable {name} is required but not set.", flush=True)
        sys.exit(1)
    return val


def _validate_email(email: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email))


def main() -> None:
    admin_email = _require_env("ADMIN_EMAIL")
    admin_password = _require_env("ADMIN_PASSWORD")
    admin_name = os.environ.get("ADMIN_NAME", "Admin").strip() or "Admin"
    tenant_name = os.environ.get("TENANT_NAME", "My Organisation").strip() or "My Organisation"

    if not _validate_email(admin_email):
        print(f"[x] Invalid email address: {admin_email}", flush=True)
        sys.exit(1)

    if len(admin_password) < 8:
        print("[x] ADMIN_PASSWORD must be at least 8 characters.", flush=True)
        sys.exit(1)

    print(f"[*] Creating super admin: {admin_email} / tenant: {tenant_name}", flush=True)

    db = next(get_db())
    try:
        success, message = create_super_admin(
            email=admin_email,
            password=admin_password,
            name=admin_name,
            tenant_name=tenant_name,
            db=db,
        )
        if success:
            print(f"[+] {message}", flush=True)
            sys.exit(0)
        else:
            print(f"[x] {message}", flush=True)
            sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
