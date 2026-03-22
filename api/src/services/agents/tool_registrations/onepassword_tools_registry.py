"""1Password tool registrations - SDK-based for SaaS."""

from typing import Any

from src.services.agents.internal_tools.onepassword_tools import (
    internal_1password_archive_item,
    internal_1password_create_item,
    internal_1password_delete_item,
    internal_1password_generate_password,
    internal_1password_get_item,
    internal_1password_list_items,
    internal_1password_list_vaults,
    internal_1password_read_secret,
    internal_1password_resolve_multiple,
    internal_1password_update_item,
)


def register_1password_tools(adk_tools_instance):
    """Register all 1Password tools (SDK-based for SaaS)."""

    # Wrapper functions
    async def onepassword_read_secret_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_1password_read_secret(
            reference=kwargs.get("reference"),
            config=config,
            runtime_context=runtime_context,
        )

    async def onepassword_list_vaults_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_1password_list_vaults(
            config=config,
            runtime_context=runtime_context,
        )

    async def onepassword_list_items_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_1password_list_items(
            vault_id=kwargs.get("vault_id"),
            config=config,
            runtime_context=runtime_context,
        )

    async def onepassword_get_item_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_1password_get_item(
            vault_id=kwargs.get("vault_id"),
            item_id=kwargs.get("item_id"),
            config=config,
            runtime_context=runtime_context,
        )

    async def onepassword_create_item_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_1password_create_item(
            vault_id=kwargs.get("vault_id"),
            title=kwargs.get("title"),
            category=kwargs.get("category", "LOGIN"),
            fields=kwargs.get("fields"),
            tags=kwargs.get("tags"),
            url=kwargs.get("url"),
            config=config,
            runtime_context=runtime_context,
        )

    async def onepassword_update_item_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_1password_update_item(
            vault_id=kwargs.get("vault_id"),
            item_id=kwargs.get("item_id"),
            title=kwargs.get("title"),
            fields=kwargs.get("fields"),
            tags=kwargs.get("tags"),
            config=config,
            runtime_context=runtime_context,
        )

    async def onepassword_delete_item_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_1password_delete_item(
            vault_id=kwargs.get("vault_id"),
            item_id=kwargs.get("item_id"),
            config=config,
            runtime_context=runtime_context,
        )

    async def onepassword_archive_item_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_1password_archive_item(
            vault_id=kwargs.get("vault_id"),
            item_id=kwargs.get("item_id"),
            config=config,
            runtime_context=runtime_context,
        )

    async def onepassword_generate_password_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_1password_generate_password(
            length=kwargs.get("length", 32),
            digits=kwargs.get("digits", True),
            symbols=kwargs.get("symbols", True),
            config=config,
            runtime_context=runtime_context,
        )

    async def onepassword_resolve_multiple_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_1password_resolve_multiple(
            references=kwargs.get("references"),
            config=config,
            runtime_context=runtime_context,
        )

    # Register all tools
    adk_tools_instance.register_tool(
        name="internal_1password_read_secret",
        description="Read a secret value from 1Password using a secret reference. Format: op://vault/item/field. Examples: op://Private/Database/password, op://Work/API Keys/github_token. This is the fastest way to retrieve a single secret.",
        parameters={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Secret reference in format op://vault/item/field",
                },
            },
            "required": ["reference"],
        },
        function=onepassword_read_secret_wrapper,
    )

    adk_tools_instance.register_tool(
        name="internal_1password_list_vaults",
        description="List all vaults accessible by the configured 1Password Service Account.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=onepassword_list_vaults_wrapper,
    )

    adk_tools_instance.register_tool(
        name="internal_1password_list_items",
        description="List items in a 1Password vault. Returns item titles and IDs for browsing credentials.",
        parameters={
            "type": "object",
            "properties": {
                "vault_id": {
                    "type": "string",
                    "description": "Vault ID to list items from. Use list_vaults first to get vault IDs.",
                },
            },
            "required": ["vault_id"],
        },
        function=onepassword_list_items_wrapper,
    )

    adk_tools_instance.register_tool(
        name="internal_1password_get_item",
        description="Get detailed information about a specific 1Password item including all fields and values.",
        parameters={
            "type": "object",
            "properties": {
                "vault_id": {
                    "type": "string",
                    "description": "Vault ID containing the item",
                },
                "item_id": {
                    "type": "string",
                    "description": "Item ID to retrieve",
                },
            },
            "required": ["vault_id", "item_id"],
        },
        function=onepassword_get_item_wrapper,
    )

    adk_tools_instance.register_tool(
        name="internal_1password_create_item",
        description="Create a new item in 1Password. Supports Login, Password, Secure Note, API Credential categories.",
        parameters={
            "type": "object",
            "properties": {
                "vault_id": {
                    "type": "string",
                    "description": "Vault ID to create the item in",
                },
                "title": {
                    "type": "string",
                    "description": "Item title",
                },
                "category": {
                    "type": "string",
                    "description": "Item category",
                    "enum": ["LOGIN", "PASSWORD", "SECURE_NOTE", "API_CREDENTIAL", "CREDIT_CARD", "IDENTITY"],
                    "default": "LOGIN",
                },
                "fields": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "Field key-value pairs (e.g., {'username': 'admin', 'password': 'secret'})",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to apply to the item",
                },
                "url": {
                    "type": "string",
                    "description": "URL for Login items",
                },
            },
            "required": ["vault_id", "title"],
        },
        function=onepassword_create_item_wrapper,
    )

    adk_tools_instance.register_tool(
        name="internal_1password_update_item",
        description="Update an existing item in 1Password.",
        parameters={
            "type": "object",
            "properties": {
                "vault_id": {
                    "type": "string",
                    "description": "Vault ID containing the item",
                },
                "item_id": {
                    "type": "string",
                    "description": "Item ID to update",
                },
                "title": {
                    "type": "string",
                    "description": "New title (optional)",
                },
                "fields": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "Fields to update (e.g., {'password': 'new_secret'})",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New tags (replaces existing)",
                },
            },
            "required": ["vault_id", "item_id"],
        },
        function=onepassword_update_item_wrapper,
    )

    adk_tools_instance.register_tool(
        name="internal_1password_delete_item",
        description="Permanently delete an item from 1Password. Use archive_item for soft delete.",
        parameters={
            "type": "object",
            "properties": {
                "vault_id": {
                    "type": "string",
                    "description": "Vault ID containing the item",
                },
                "item_id": {
                    "type": "string",
                    "description": "Item ID to delete",
                },
            },
            "required": ["vault_id", "item_id"],
        },
        function=onepassword_delete_item_wrapper,
    )

    adk_tools_instance.register_tool(
        name="internal_1password_archive_item",
        description="Archive an item in 1Password (soft delete). Item can be restored later.",
        parameters={
            "type": "object",
            "properties": {
                "vault_id": {
                    "type": "string",
                    "description": "Vault ID containing the item",
                },
                "item_id": {
                    "type": "string",
                    "description": "Item ID to archive",
                },
            },
            "required": ["vault_id", "item_id"],
        },
        function=onepassword_archive_item_wrapper,
    )

    adk_tools_instance.register_tool(
        name="internal_1password_generate_password",
        description="Generate a secure password using 1Password's generator.",
        parameters={
            "type": "object",
            "properties": {
                "length": {
                    "type": "integer",
                    "description": "Password length (default: 32)",
                    "default": 32,
                },
                "digits": {
                    "type": "boolean",
                    "description": "Include digits (default: true)",
                    "default": True,
                },
                "symbols": {
                    "type": "boolean",
                    "description": "Include symbols (default: true)",
                    "default": True,
                },
            },
            "required": [],
        },
        function=onepassword_generate_password_wrapper,
    )

    adk_tools_instance.register_tool(
        name="internal_1password_resolve_multiple",
        description="Resolve multiple secret references at once. More efficient than multiple read_secret calls. Returns a mapping of references to values.",
        parameters={
            "type": "object",
            "properties": {
                "references": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of secret references in op://vault/item/field format",
                },
            },
            "required": ["references"],
        },
        function=onepassword_resolve_multiple_wrapper,
    )
