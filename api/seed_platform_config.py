#!/usr/bin/env python3
"""
Script to seed default platform integration configurations.

This script creates or updates platform-wide integration settings including:
- SMTP configuration for email notifications
- Stripe configuration for billing
- Storage configuration
- Application settings

These settings act as defaults when tenants don't have their own configuration.

Usage:
    python seed_platform_config.py

Interactive prompts will guide you through the configuration.
You can also run non-interactively:
    python seed_platform_config.py --non-interactive
"""

import getpass
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sqlalchemy.orm import Session

from src.core.database import get_db
from src.services.integrations.integration_config_service import IntegrationConfigService


def seed_smtp_config(
    config: dict, service: IntegrationConfigService, update_existing: bool = False
) -> tuple[bool, str]:
    """Seed SMTP email configuration."""
    if not config.get("smtp_host"):
        return True, "SMTP configuration skipped"

    config_data = {
        "host": config["smtp_host"],
        "port": int(config.get("smtp_port", 587)),
        "username": config.get("smtp_username"),
        "password": config.get("smtp_password"),
        "from_email": config.get("smtp_from_email"),
        "from_name": config.get("smtp_from_name", "Synkora"),
        "use_tls": True,
    }

    try:
        if update_existing:
            # Try to find and update existing config
            configs = service.list_configs(tenant_id=None, integration_type="email", provider="smtp")
            if configs and len(configs) > 0:
                print("📋 Updating existing SMTP configuration...")
                service.update_config(configs[0].id, config_data=config_data)
                print("✅ SMTP configuration updated successfully!")
                return True, "SMTP configuration updated"

        print("📋 Creating new SMTP configuration...")
        service.create_config(
            tenant_id=None,
            integration_type="email",
            provider="smtp",
            config_data=config_data,
            is_active=True,
            is_default=True,
        )
        print("✅ SMTP configuration created successfully!")
        return True, "SMTP configuration created"

    except ValueError as e:
        if "already exists" in str(e):
            return False, "SMTP configuration already exists. Use --update to modify."
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        return False, f"Error seeding SMTP config: {str(e)}"


def seed_stripe_config(
    config: dict, service: IntegrationConfigService, update_existing: bool = False
) -> tuple[bool, str]:
    """Seed Stripe payment configuration."""
    if not config.get("stripe_secret_key"):
        return True, "Stripe configuration skipped"

    config_data = {
        "secret_key": config.get("stripe_secret_key"),
        "publishable_key": config.get("stripe_publishable_key"),
        "webhook_secret": config.get("stripe_webhook_secret"),
    }

    try:
        if update_existing:
            configs = service.list_configs(tenant_id=None, integration_type="payment", provider="stripe")
            if configs and len(configs) > 0:
                print("📋 Updating existing Stripe configuration...")
                service.update_config(configs[0].id, config_data=config_data)
                print("✅ Stripe configuration updated successfully!")
                return True, "Stripe configuration updated"

        print("📋 Creating new Stripe configuration...")
        service.create_config(
            tenant_id=None,
            integration_type="payment",
            provider="stripe",
            config_data=config_data,
            is_active=True,
            is_default=True,
        )
        print("✅ Stripe configuration created successfully!")
        return True, "Stripe configuration created"

    except ValueError as e:
        if "already exists" in str(e):
            return False, "Stripe configuration already exists. Use --update to modify."
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        return False, f"Error seeding Stripe config: {str(e)}"


def seed_storage_config(
    config: dict, service: IntegrationConfigService, update_existing: bool = False
) -> tuple[bool, str]:
    """Seed storage configuration."""
    storage_provider = config.get("storage_provider", "s3")

    config_data = {
        "provider": storage_provider,
        "bucket": config.get("storage_bucket", "synkora-storage"),
        "region": config.get("storage_region", "us-east-1"),
    }

    # Add provider-specific configuration
    if storage_provider == "s3":
        if config.get("s3_access_key"):
            config_data["access_key_id"] = config["s3_access_key"]
            config_data["secret_access_key"] = config.get("s3_secret_key")
        if config.get("s3_endpoint"):
            config_data["endpoint_url"] = config["s3_endpoint"]

    try:
        if update_existing:
            configs = service.list_configs(tenant_id=None, integration_type="storage", provider=storage_provider)
            if configs and len(configs) > 0:
                print("📋 Updating existing storage configuration...")
                service.update_config(configs[0].id, config_data=config_data)
                print("✅ Storage configuration updated successfully!")
                return True, "Storage configuration updated"

        print("📋 Creating new storage configuration...")
        service.create_config(
            tenant_id=None,
            integration_type="storage",
            provider=storage_provider,
            config_data=config_data,
            is_active=True,
            is_default=True,
        )
        print("✅ Storage configuration created successfully!")
        return True, "Storage configuration created"

    except ValueError as e:
        if "already exists" in str(e):
            return False, "Storage configuration already exists. Use --update to modify."
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        return False, f"Error seeding storage config: {str(e)}"


def seed_app_config(config: dict, service: IntegrationConfigService, update_existing: bool = False) -> tuple[bool, str]:
    """Seed application configuration."""
    config_data = {
        "platform_name": config.get("platform_name", "Synkora"),
        "platform_logo_url": config.get("platform_logo_url"),
        "support_email": config.get("support_email"),
        "app_base_url": config.get("app_base_url"),
    }

    # Remove None values
    config_data = {k: v for k, v in config_data.items() if v is not None}

    try:
        if update_existing:
            configs = service.list_configs(tenant_id=None, integration_type="application", provider="synkora")
            if configs and len(configs) > 0:
                print("📋 Updating existing application configuration...")
                service.update_config(configs[0].id, config_data=config_data)
                print("✅ Application configuration updated successfully!")
                return True, "Application configuration updated"

        print("📋 Creating new application configuration...")
        service.create_config(
            tenant_id=None,
            integration_type="application",
            provider="synkora",
            config_data=config_data,
            is_active=True,
            is_default=True,
        )
        print("✅ Application configuration created successfully!")
        return True, "Application configuration created"

    except ValueError as e:
        if "already exists" in str(e):
            return False, "Application configuration already exists. Use --update to modify."
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        return False, f"Error seeding application config: {str(e)}"


# =============================================================================
# Platform OAuth App Seeding
# =============================================================================


def seed_oauth_app(
    db: Session,
    provider: str,
    app_name: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    scopes: list[str],
    update_existing: bool = False,
    description: str = None,
    config: dict = None,
) -> tuple[bool, str]:
    """
    Seed a platform OAuth app.

    Args:
        db: Database session
        provider: OAuth provider name (github, slack, gitlab, zoom, gmail)
        app_name: Display name for the app
        client_id: OAuth client ID
        client_secret: OAuth client secret
        redirect_uri: OAuth redirect URI
        scopes: List of OAuth scopes
        update_existing: Whether to update existing config
        description: Optional description
        config: Optional provider-specific config

    Returns:
        Tuple of (success, message)
    """
    from src.config.security import encrypt_value
    from src.models.oauth_app import OAuthApp

    provider = provider.lower()

    try:
        # Check if platform app already exists
        existing = (
            db.query(OAuthApp)
            .filter(
                OAuthApp.is_platform_app.is_(True),
                OAuthApp.tenant_id.is_(None),
                OAuthApp.provider == provider,
            )
            .first()
        )

        if existing:
            if update_existing:
                print(f"📋 Updating existing {provider.title()} platform OAuth app...")
                existing.app_name = app_name
                existing.client_id = client_id
                existing.client_secret = encrypt_value(client_secret)
                existing.redirect_uri = redirect_uri
                existing.scopes = scopes
                existing.description = description
                existing.config = config
                existing.is_active = True
                db.commit()
                print(f"✅ {provider.title()} platform OAuth app updated!")
                return True, f"{provider.title()} OAuth app updated"
            else:
                return False, f"{provider.title()} platform OAuth app already exists. Use --update to modify."

        # Create new platform OAuth app
        print(f"📋 Creating {provider.title()} platform OAuth app...")
        oauth_app = OAuthApp(
            tenant_id=None,
            provider=provider,
            app_name=app_name,
            is_platform_app=True,
            auth_method="oauth",
            client_id=client_id,
            client_secret=encrypt_value(client_secret),
            redirect_uri=redirect_uri,
            scopes=scopes,
            description=description,
            config=config,
            is_active=True,
            is_default=True,
        )
        db.add(oauth_app)
        db.commit()
        print(f"✅ {provider.title()} platform OAuth app created!")
        return True, f"{provider.title()} OAuth app created"

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False, f"Error seeding {provider} OAuth app: {str(e)}"


def seed_github_oauth(config: dict, db: Session, update_existing: bool = False) -> tuple[bool, str]:
    """Seed GitHub platform OAuth app."""
    client_id = config.get("github_client_id")
    client_secret = config.get("github_client_secret")

    if not client_id or not client_secret:
        return True, "GitHub OAuth skipped (no credentials provided)"

    base_url = config.get("app_base_url", "https://app.synkora.ai")
    redirect_uri = f"{base_url}/api/v1/oauth/github/callback"

    return seed_oauth_app(
        db=db,
        provider="github",
        app_name="Synkora GitHub",
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=["repo", "user", "read:org"],
        update_existing=update_existing,
        description="Synkora-provided GitHub integration for all tenants",
    )


def seed_slack_oauth(config: dict, db: Session, update_existing: bool = False) -> tuple[bool, str]:
    """Seed Slack platform OAuth app."""
    client_id = config.get("slack_client_id")
    client_secret = config.get("slack_client_secret")

    if not client_id or not client_secret:
        return True, "Slack OAuth skipped (no credentials provided)"

    base_url = config.get("app_base_url", "https://app.synkora.ai")
    redirect_uri = f"{base_url}/api/v1/oauth/slack/callback"

    return seed_oauth_app(
        db=db,
        provider="slack",
        app_name="Synkora Slack",
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=[
            "channels:history",
            "channels:read",
            "groups:history",
            "groups:read",
            "im:history",
            "im:read",
            "mpim:history",
            "mpim:read",
            "users:read",
            "team:read",
        ],
        update_existing=update_existing,
        description="Synkora-provided Slack integration for all tenants",
    )


def seed_gitlab_oauth(config: dict, db: Session, update_existing: bool = False) -> tuple[bool, str]:
    """Seed GitLab platform OAuth app (gitlab.com only)."""
    client_id = config.get("gitlab_client_id")
    client_secret = config.get("gitlab_client_secret")

    if not client_id or not client_secret:
        return True, "GitLab OAuth skipped (no credentials provided)"

    base_url = config.get("app_base_url", "https://app.synkora.ai")
    redirect_uri = f"{base_url}/api/v1/oauth/gitlab/callback"

    return seed_oauth_app(
        db=db,
        provider="gitlab",
        app_name="Synkora GitLab",
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=["api", "read_user", "read_repository", "write_repository"],
        update_existing=update_existing,
        description="Synkora-provided GitLab.com integration for all tenants",
        config={"base_url": "https://gitlab.com"},
    )


def seed_zoom_oauth(config: dict, db: Session, update_existing: bool = False) -> tuple[bool, str]:
    """Seed Zoom platform OAuth app."""
    client_id = config.get("zoom_client_id")
    client_secret = config.get("zoom_client_secret")

    if not client_id or not client_secret:
        return True, "Zoom OAuth skipped (no credentials provided)"

    base_url = config.get("app_base_url", "https://app.synkora.ai")
    redirect_uri = f"{base_url}/api/v1/oauth/zoom/callback"

    return seed_oauth_app(
        db=db,
        provider="zoom",
        app_name="Synkora Zoom",
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=["user:read", "meeting:read", "meeting:write"],
        update_existing=update_existing,
        description="Synkora-provided Zoom integration for all tenants",
    )


def seed_gmail_oauth(config: dict, db: Session, update_existing: bool = False) -> tuple[bool, str]:
    """Seed Gmail platform OAuth app."""
    client_id = config.get("gmail_client_id")
    client_secret = config.get("gmail_client_secret")

    if not client_id or not client_secret:
        return True, "Gmail OAuth skipped (no credentials provided)"

    base_url = config.get("app_base_url", "https://app.synkora.ai")
    redirect_uri = f"{base_url}/api/v1/oauth/gmail/callback"

    return seed_oauth_app(
        db=db,
        provider="gmail",
        app_name="Synkora Gmail",
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.compose",
        ],
        update_existing=update_existing,
        description="Synkora-provided Gmail integration for all tenants",
    )


def interactive_mode():
    """Interactive mode with prompts for configuration."""
    print("\n" + "=" * 60)
    print("SYNKORA - PLATFORM CONFIGURATION SETUP")
    print("=" * 60)
    print("\nThis script will set up default platform-wide configuration.")
    print("These settings will be used as defaults for all tenants.\n")
    print("Press Enter to skip optional fields.\n")

    config = {}

    # Platform Branding
    print("=" * 60)
    print("PLATFORM BRANDING")
    print("=" * 60)

    config["platform_name"] = input("Platform name [Synkora]: ").strip() or "Synkora"
    config["platform_logo_url"] = input("Platform logo URL (optional): ").strip() or None
    config["support_email"] = input("Support email (optional): ").strip() or None
    config["app_base_url"] = input("Application base URL (e.g., https://app.synkora.ai): ").strip() or None

    # SMTP Configuration
    print("\n" + "=" * 60)
    print("SMTP CONFIGURATION (for email notifications)")
    print("=" * 60)
    print("Skip if you don't want to configure email now.\n")

    smtp_host = input("SMTP host (e.g., smtp.gmail.com): ").strip()
    if smtp_host:
        config["smtp_host"] = smtp_host
        config["smtp_port"] = input("SMTP port [587]: ").strip() or "587"
        config["smtp_username"] = input("SMTP username: ").strip()
        config["smtp_password"] = getpass.getpass("SMTP password: ")
        config["smtp_from_email"] = input("From email address: ").strip()
        config["smtp_from_name"] = input("From name [Synkora]: ").strip() or "Synkora"

    # Stripe Configuration
    print("\n" + "=" * 60)
    print("STRIPE CONFIGURATION (for billing)")
    print("=" * 60)
    print("Skip if you don't want to configure Stripe now.\n")

    stripe_secret = getpass.getpass("Stripe secret key (starts with sk_): ")
    if stripe_secret:
        config["stripe_secret_key"] = stripe_secret
        config["stripe_publishable_key"] = input("Stripe publishable key (starts with pk_): ").strip()
        stripe_webhook = getpass.getpass("Stripe webhook secret (optional, starts with whsec_): ")
        if stripe_webhook:
            config["stripe_webhook_secret"] = stripe_webhook

    # Storage Configuration
    print("\n" + "=" * 60)
    print("STORAGE CONFIGURATION")
    print("=" * 60)

    storage_provider = input("Storage provider [s3]: ").strip() or "s3"
    config["storage_provider"] = storage_provider
    config["storage_bucket"] = input("Storage bucket name [synkora-storage]: ").strip() or "synkora-storage"
    config["storage_region"] = input("Storage region [us-east-1]: ").strip() or "us-east-1"

    if storage_provider == "s3":
        s3_access = input("S3 Access Key ID (optional, leave blank for IAM role): ").strip()
        if s3_access:
            config["s3_access_key"] = s3_access
            config["s3_secret_key"] = getpass.getpass("S3 Secret Access Key: ")
        s3_endpoint = input("S3 Endpoint URL (optional, for MinIO or custom S3): ").strip()
        if s3_endpoint:
            config["s3_endpoint"] = s3_endpoint

    # Confirm
    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"Platform Name:    {config.get('platform_name', 'Not set')}")
    print(f"Support Email:    {config.get('support_email', 'Not set')}")
    print(f"App Base URL:     {config.get('app_base_url', 'Not set')}")
    print(f"SMTP Configured:  {'Yes' if config.get('smtp_host') else 'No'}")
    print(f"Stripe Configured: {'Yes' if config.get('stripe_secret_key') else 'No'}")
    print(f"Storage Provider:  {config.get('storage_provider', 's3')}")
    print("=" * 60)

    confirm = input("\nProceed with configuration? (yes/no): ").strip().lower()
    if confirm not in ["yes", "y"]:
        print("\n❌ Cancelled by user")
        return None

    return config


def non_interactive_mode():
    """
    Non-interactive mode using environment variables.
    This is useful for automated deployments.
    """
    config = {}

    # Read from environment variables
    config["platform_name"] = os.getenv("PLATFORM_NAME", "Synkora")
    config["platform_logo_url"] = os.getenv("PLATFORM_LOGO_URL")
    config["support_email"] = os.getenv("SUPPORT_EMAIL")
    config["app_base_url"] = os.getenv("APP_BASE_URL")

    # SMTP
    config["smtp_host"] = os.getenv("SMTP_HOST")
    config["smtp_port"] = os.getenv("SMTP_PORT", "587")
    config["smtp_username"] = os.getenv("SMTP_USERNAME")
    config["smtp_password"] = os.getenv("SMTP_PASSWORD")
    config["smtp_from_email"] = os.getenv("SMTP_FROM_EMAIL")
    config["smtp_from_name"] = os.getenv("SMTP_FROM_NAME", "Synkora")

    # Stripe
    config["stripe_secret_key"] = os.getenv("STRIPE_SECRET_KEY")
    config["stripe_publishable_key"] = os.getenv("STRIPE_PUBLISHABLE_KEY")
    config["stripe_webhook_secret"] = os.getenv("STRIPE_WEBHOOK_SECRET")

    # Storage
    config["storage_provider"] = os.getenv("STORAGE_PROVIDER", "s3")
    config["storage_bucket"] = os.getenv("STORAGE_BUCKET", "synkora-storage")
    config["storage_region"] = os.getenv("STORAGE_REGION", "us-east-1")
    config["s3_access_key"] = os.getenv("S3_ACCESS_KEY_ID")
    config["s3_secret_key"] = os.getenv("S3_SECRET_ACCESS_KEY")
    config["s3_endpoint"] = os.getenv("S3_ENDPOINT_URL")

    # Platform OAuth Apps
    config["github_client_id"] = os.getenv("GITHUB_CLIENT_ID")
    config["github_client_secret"] = os.getenv("GITHUB_CLIENT_SECRET")
    config["slack_client_id"] = os.getenv("SLACK_CLIENT_ID")
    config["slack_client_secret"] = os.getenv("SLACK_CLIENT_SECRET")
    config["gitlab_client_id"] = os.getenv("GITLAB_CLIENT_ID")
    config["gitlab_client_secret"] = os.getenv("GITLAB_CLIENT_SECRET")
    config["zoom_client_id"] = os.getenv("ZOOM_CLIENT_ID")
    config["zoom_client_secret"] = os.getenv("ZOOM_CLIENT_SECRET")
    config["gmail_client_id"] = os.getenv("GMAIL_CLIENT_ID")
    config["gmail_client_secret"] = os.getenv("GMAIL_CLIENT_SECRET")

    # Remove None values
    config = {k: v for k, v in config.items() if v is not None}

    if not config:
        print("❌ No configuration found in environment variables")
        return None

    print("📋 Configuration loaded from environment variables")
    return config


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed platform integration configurations")
    parser.add_argument(
        "--non-interactive", action="store_true", help="Run in non-interactive mode using environment variables"
    )
    parser.add_argument("--update", action="store_true", help="Update existing configuration")

    args = parser.parse_args()

    if args.non_interactive:
        print("\n🤖 Running in non-interactive mode...")
        config = non_interactive_mode()
    else:
        config = interactive_mode()

    if not config:
        sys.exit(1)

    print("\n🔄 Saving platform configurations...\n")

    db: Session = next(get_db())
    try:
        # Initialize the service
        service = IntegrationConfigService(db)

        results = []

        # Seed application config
        success, message = seed_app_config(config, service, args.update)
        results.append((success, message))

        # Seed SMTP config
        success, message = seed_smtp_config(config, service, args.update)
        results.append((success, message))

        # Seed Stripe config
        success, message = seed_stripe_config(config, service, args.update)
        results.append((success, message))

        # Seed storage config
        success, message = seed_storage_config(config, service, args.update)
        results.append((success, message))

        # Seed platform OAuth apps
        print("\n" + "=" * 60)
        print("PLATFORM OAUTH APPS")
        print("=" * 60 + "\n")

        success, message = seed_github_oauth(config, db, args.update)
        results.append((success, message))

        success, message = seed_slack_oauth(config, db, args.update)
        results.append((success, message))

        success, message = seed_gitlab_oauth(config, db, args.update)
        results.append((success, message))

        success, message = seed_zoom_oauth(config, db, args.update)
        results.append((success, message))

        success, message = seed_gmail_oauth(config, db, args.update)
        results.append((success, message))

        # Check if all succeeded
        all_success = all(success for success, _ in results)

        if all_success:
            print("\n✅ All configurations saved successfully!")
            print("\n" + "=" * 60)
            print("NEXT STEPS")
            print("=" * 60)
            print("1. Platform integration configurations are now set up")
            print("2. Tenants without their own config will use these defaults")
            print("3. Platform OAuth apps are available to all tenants")
            print("4. You can update this configuration anytime with --update flag")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n⚠️ Some configurations failed:")
            for success, message in results:
                if not success:
                    print(f"  - {message}")
            sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
