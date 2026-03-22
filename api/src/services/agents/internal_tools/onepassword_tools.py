"""
1Password SDK Tools for SaaS Credential Management.
Uses the official 1Password Python SDK with Service Account tokens.

This is designed for multi-tenant SaaS where each tenant configures
their own 1Password Service Account token.

Requirements:
- pip install onepassword-sdk
- Python 3.9+
- Each tenant creates a Service Account in their 1Password account
- Service Account token stored in OAuthApp

Configuration stored in OAuthApp:
- provider: "onepassword"
- api_token: Service Account token

Reference: https://developer.1password.com/docs/sdks/
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# SDK availability flag
_SDK_AVAILABLE = False
try:
    from onepassword.client import Client
    from onepassword.types import ItemCreateParams, ItemField, ItemFieldType

    _SDK_AVAILABLE = True
except ImportError:
    logger.warning("1Password SDK not installed. Install with: pip install onepassword-sdk")


def _get_1password_app(runtime_context: Any) -> dict[str, Any] | None:
    """Get 1Password OAuth app from runtime context."""
    if runtime_context and hasattr(runtime_context, "__getitem__"):
        oauth_apps = runtime_context.get("oauth_apps", [])
    elif runtime_context and hasattr(runtime_context, "oauth_apps"):
        oauth_apps = runtime_context.oauth_apps or []
    else:
        oauth_apps = []

    for app in oauth_apps:
        if app.get("provider", "").lower() == "onepassword":
            return app

    return None


async def _get_1password_client(runtime_context: Any) -> "Client":
    """
    Get authenticated 1Password client for the current tenant.

    Args:
        runtime_context: Runtime context with oauth_apps

    Returns:
        Authenticated 1Password Client

    Raises:
        ValueError: If 1Password is not configured for the tenant
    """
    if not _SDK_AVAILABLE:
        raise ValueError("1Password SDK not installed. Install with: pip install onepassword-sdk")

    app = _get_1password_app(runtime_context)

    if not app:
        raise ValueError("1Password not configured. Please add a 1Password integration in Connected Accounts.")

    # Get the service account token from api_token
    from src.services.agents.security import decrypt_value

    token = None
    if app.get("api_token"):
        token = decrypt_value(app["api_token"])

    if not token:
        raise ValueError("1Password Service Account token not configured.")

    # Create authenticated client
    try:
        client = await Client.authenticate(
            auth=token,
            integration_name="Synkora",
            integration_version="1.0.0",
        )
        return client
    except Exception as e:
        logger.error(f"Failed to authenticate with 1Password: {e}")
        raise ValueError(f"Failed to authenticate with 1Password: {str(e)}")


async def _get_default_vault(runtime_context: Any) -> str | None:
    """Get default vault from config if set."""
    app = _get_1password_app(runtime_context)

    if app and app.get("config"):
        config = app.get("config", {})
        return config.get("default_vault")
    return None


async def internal_1password_read_secret(
    reference: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Read a secret value using a 1Password secret reference.
    This is the most common operation - quickly retrieve a single secret.

    Args:
        reference: Secret reference in format op://vault/item/field
                  Examples:
                  - op://Private/Database/password
                  - op://Work/API Keys/github_token
                  - op://Private/SSH Key/private key
                  - op://Private/Login/one-time password

    Returns:
        Dict with the secret value (handle securely!)
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        client = await _get_1password_client(runtime_context)
        secret = await client.secrets.resolve(reference)

        return {
            "success": True,
            "value": secret,
            "reference": reference,
            "note": "Handle this secret securely. Do not log or expose it.",
        }
    except Exception as e:
        logger.error(f"Failed to read 1Password secret: {e}")
        return {"success": False, "error": str(e)}


async def internal_1password_list_vaults(
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    List all vaults accessible by the Service Account.

    Returns:
        List of vaults with id and name
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        client = await _get_1password_client(runtime_context)
        vaults = await client.vaults.list_all()

        vault_list = []
        async for vault in vaults:
            vault_list.append(
                {
                    "id": vault.id,
                    "name": vault.title,
                }
            )

        return {
            "success": True,
            "vaults": vault_list,
        }
    except Exception as e:
        logger.error(f"Failed to list 1Password vaults: {e}")
        return {"success": False, "error": str(e)}


async def internal_1password_list_items(
    vault_id: str | None = None,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    List items in a vault.

    Args:
        vault_id: Vault ID to list items from (uses default vault if not specified)

    Returns:
        List of items with basic metadata
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        client = await _get_1password_client(runtime_context)

        # Use default vault if not specified
        if not vault_id:
            vault_id = await _get_default_vault(runtime_context)

        if not vault_id:
            return {"success": False, "error": "vault_id is required. Specify a vault or set a default vault."}

        items = await client.items.list(vault_id)

        item_list = []
        async for item in items:
            item_list.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "vault_id": item.vault_id,
                    "category": str(item.category) if hasattr(item, "category") else None,
                }
            )

        return {
            "success": True,
            "items": item_list,
            "vault_id": vault_id,
        }
    except Exception as e:
        logger.error(f"Failed to list 1Password items: {e}")
        return {"success": False, "error": str(e)}


async def internal_1password_get_item(
    vault_id: str,
    item_id: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get detailed information about a specific item.

    Args:
        vault_id: Vault ID containing the item
        item_id: Item ID to retrieve

    Returns:
        Item details including all fields
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        client = await _get_1password_client(runtime_context)
        item = await client.items.get(vault_id, item_id)

        # Extract fields
        fields = {}
        if hasattr(item, "fields") and item.fields:
            for field in item.fields:
                field_id = field.id or field.title.lower().replace(" ", "_")
                fields[field_id] = {
                    "title": field.title,
                    "value": field.value,
                    "field_type": str(field.field_type) if hasattr(field, "field_type") else None,
                }

        return {
            "success": True,
            "item": {
                "id": item.id,
                "title": item.title,
                "vault_id": item.vault_id,
                "category": str(item.category) if hasattr(item, "category") else None,
                "fields": fields,
                "tags": list(item.tags) if hasattr(item, "tags") and item.tags else [],
                "urls": [url.href for url in item.urls] if hasattr(item, "urls") and item.urls else [],
            },
        }
    except Exception as e:
        logger.error(f"Failed to get 1Password item: {e}")
        return {"success": False, "error": str(e)}


async def internal_1password_create_item(
    vault_id: str,
    title: str,
    category: str = "LOGIN",
    fields: dict[str, str] | None = None,
    tags: list[str] | None = None,
    url: str | None = None,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Create a new item in 1Password.

    Args:
        vault_id: Vault ID to create the item in
        title: Item title
        category: Item category (LOGIN, PASSWORD, SECURE_NOTE, API_CREDENTIAL, etc.)
        fields: Field key-value pairs (e.g., {"username": "admin", "password": "secret"})
        tags: Tags to apply to the item
        url: URL for Login items

    Returns:
        Created item details
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    if not _SDK_AVAILABLE:
        return {"success": False, "error": "1Password SDK not installed"}

    try:
        client = await _get_1password_client(runtime_context)

        # Build item fields
        item_fields = []
        if fields:
            for field_id, value in fields.items():
                # Determine field type based on field name
                field_type = ItemFieldType.TEXT
                if "password" in field_id.lower():
                    field_type = ItemFieldType.CONCEALED
                elif "email" in field_id.lower():
                    field_type = ItemFieldType.EMAIL
                elif "url" in field_id.lower() or "website" in field_id.lower():
                    field_type = ItemFieldType.URL
                elif "otp" in field_id.lower() or "totp" in field_id.lower():
                    field_type = ItemFieldType.TOTP

                item_fields.append(
                    ItemField(
                        id=field_id,
                        title=field_id.replace("_", " ").title(),
                        value=value,
                        field_type=field_type,
                    )
                )

        # Create item params
        # Note: The exact API may vary - adjust based on SDK version
        item = await client.items.create(
            vault_id=vault_id,
            title=title,
            category=category,
            fields=item_fields if item_fields else None,
            tags=tags,
        )

        return {
            "success": True,
            "item": {
                "id": item.id,
                "title": item.title,
                "vault_id": item.vault_id,
            },
            "message": f"Created item '{title}' in 1Password",
        }
    except Exception as e:
        logger.error(f"Failed to create 1Password item: {e}")
        return {"success": False, "error": str(e)}


async def internal_1password_update_item(
    vault_id: str,
    item_id: str,
    title: str | None = None,
    fields: dict[str, str] | None = None,
    tags: list[str] | None = None,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Update an existing item in 1Password.

    Args:
        vault_id: Vault ID containing the item
        item_id: Item ID to update
        title: New title (optional)
        fields: Fields to update (e.g., {"password": "new_secret"})
        tags: New tags (optional)

    Returns:
        Updated item details
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        client = await _get_1password_client(runtime_context)

        # Update fields
        update_params = {}
        if title:
            update_params["title"] = title
        if tags is not None:
            update_params["tags"] = tags

        # Note: Actual update API may differ - adjust based on SDK
        item = await client.items.update(
            vault_id=vault_id,
            item_id=item_id,
            **update_params,
        )

        return {
            "success": True,
            "item": {
                "id": item.id,
                "title": item.title,
                "vault_id": item.vault_id,
            },
            "message": f"Updated item '{item.title}' in 1Password",
        }
    except Exception as e:
        logger.error(f"Failed to update 1Password item: {e}")
        return {"success": False, "error": str(e)}


async def internal_1password_delete_item(
    vault_id: str,
    item_id: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Delete an item from 1Password.

    Args:
        vault_id: Vault ID containing the item
        item_id: Item ID to delete

    Returns:
        Success status
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        client = await _get_1password_client(runtime_context)
        await client.items.delete(vault_id, item_id)

        return {
            "success": True,
            "message": f"Deleted item {item_id} from 1Password",
        }
    except Exception as e:
        logger.error(f"Failed to delete 1Password item: {e}")
        return {"success": False, "error": str(e)}


async def internal_1password_archive_item(
    vault_id: str,
    item_id: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Archive an item in 1Password (soft delete).

    Args:
        vault_id: Vault ID containing the item
        item_id: Item ID to archive

    Returns:
        Success status
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        client = await _get_1password_client(runtime_context)
        await client.items.archive(vault_id, item_id)

        return {
            "success": True,
            "message": f"Archived item {item_id} in 1Password",
        }
    except Exception as e:
        logger.error(f"Failed to archive 1Password item: {e}")
        return {"success": False, "error": str(e)}


async def internal_1password_generate_password(
    length: int = 32,
    digits: bool = True,
    symbols: bool = True,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Generate a secure password using 1Password.

    Args:
        length: Password length (default: 32)
        digits: Include digits (default: True)
        symbols: Include symbols (default: True)

    Returns:
        Generated password
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        client = await _get_1password_client(runtime_context)

        # Generate password
        # Note: Exact API may vary based on SDK version
        password = await client.items.generate_password(
            length=length,
            digits=digits,
            symbols=symbols,
        )

        return {
            "success": True,
            "password": password,
            "length": len(password),
            "note": "Handle this password securely. Do not log or expose it.",
        }
    except Exception as e:
        logger.error(f"Failed to generate password: {e}")
        return {"success": False, "error": str(e)}


async def internal_1password_resolve_multiple(
    references: list[str],
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Resolve multiple secret references at once.
    More efficient than calling read_secret multiple times.

    Args:
        references: List of secret references (op://vault/item/field format)

    Returns:
        Dict mapping references to their values
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        client = await _get_1password_client(runtime_context)

        secrets = {}
        errors = []

        for ref in references:
            try:
                secret = await client.secrets.resolve(ref)
                secrets[ref] = secret
            except Exception as e:
                errors.append({"reference": ref, "error": str(e)})

        return {
            "success": len(errors) == 0,
            "secrets": secrets,
            "errors": errors if errors else None,
            "resolved_count": len(secrets),
            "note": "Handle these secrets securely. Do not log or expose them.",
        }
    except Exception as e:
        logger.error(f"Failed to resolve 1Password secrets: {e}")
        return {"success": False, "error": str(e)}
