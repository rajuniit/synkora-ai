#!/usr/bin/env python3
"""
Script to promote a user to Platform Owner role.

Usage:
    python promote_to_platform_owner.py <email>

Example:
    python promote_to_platform_owner.py admin@example.com
"""

import os
import sys
from uuid import UUID

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models import Account, Role, TenantAccountJoin


def promote_to_platform_owner(email: str):
    """
    Promote a user to Platform Owner role.

    Args:
        email: Email address of the user to promote
    """
    db: Session = next(get_db())

    try:
        # Find the user by email
        account = db.query(Account).filter(Account.email == email).first()

        if not account:
            print(f"❌ Error: User with email '{email}' not found")
            return False

        print(f"✓ Found user: {account.name} ({account.email})")
        print(f"  Account ID: {account.id}")

        # Find the Platform Owner role
        platform_owner_role = (
            db.query(Role)
            .filter(Role.name == "Platform Owner", Role.is_system.is_(True), Role.tenant_id.is_(None))
            .first()
        )

        if not platform_owner_role:
            print("❌ Error: Platform Owner role not found in database")
            print("   Please run the seed_roles_permissions script first")
            return False

        print(f"✓ Found Platform Owner role (ID: {platform_owner_role.id})")

        # Get all tenant associations for this user
        tenant_joins = db.query(TenantAccountJoin).filter(TenantAccountJoin.account_id == account.id).all()

        if not tenant_joins:
            print("❌ Error: User is not associated with any tenant")
            return False

        print(f"✓ Found {len(tenant_joins)} tenant association(s)")

        # Update all tenant associations to Platform Owner role
        updated_count = 0
        for join in tenant_joins:
            old_role_id = join.role_id
            join.role_id = platform_owner_role.id
            updated_count += 1
            print(f"  - Updated tenant {join.tenant_id}: role_id {old_role_id} → {platform_owner_role.id}")

        # Set is_platform_admin flag on the account
        account.is_platform_admin = "true"
        print("  - Set is_platform_admin flag to true")

        # Commit the changes
        db.commit()

        print(f"\n✅ Success! User '{email}' has been promoted to Platform Owner")
        print(f"   Updated {updated_count} tenant association(s)")

        return True

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python promote_to_platform_owner.py <email>")
        print("\nExample:")
        print("  python promote_to_platform_owner.py admin@example.com")
        sys.exit(1)

    email = sys.argv[1]

    print(f"\n🔄 Promoting user '{email}' to Platform Owner...\n")

    success = promote_to_platform_owner(email)

    if success:
        print("\n" + "=" * 60)
        print("IMPORTANT: The user needs to log out and log back in")
        print("for the role change to take effect.")
        print("=" * 60 + "\n")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
