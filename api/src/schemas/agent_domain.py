"""
Agent Domain Schemas

Pydantic schemas for agent domain management.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RightSidebarConfig(BaseModel):
    """Right sidebar configuration."""

    enabled: bool = Field(False, description="Enable right sidebar")
    content: str | None = Field(None, description="Sidebar content (HTML/markdown)")
    width: str = Field("md", description="Sidebar width (sm/md/lg)")


class HeaderConfig(BaseModel):
    """Header configuration."""

    enabled: bool = Field(True, description="Enable header")
    logo_url: str | None = Field(None, description="Header logo URL")
    title: str | None = Field(None, description="Header title")
    tagline: str | None = Field(None, description="Header tagline")
    background_color: str | None = Field(None, description="Header background color (hex)")
    text_color: str | None = Field(None, description="Header text color (hex)")
    height: str = Field("normal", description="Header height (compact/normal)")


class FooterConfig(BaseModel):
    """Footer configuration."""

    enabled: bool = Field(True, description="Enable footer")
    content: str | None = Field(None, description="Footer content (HTML/markdown)")
    background_color: str | None = Field(None, description="Footer background color (hex)")
    text_color: str | None = Field(None, description="Footer text color (hex)")
    height: str = Field("compact", description="Footer height (compact/normal)")


class ThemeConfig(BaseModel):
    """Theme configuration."""

    primary_color: str | None = Field(None, description="Primary color (hex)")
    secondary_color: str | None = Field(None, description="Secondary color (hex)")
    background_color: str | None = Field(None, description="Background color (hex)")
    user_message_bg: str | None = Field(None, description="User message background (hex)")
    agent_message_bg: str | None = Field(None, description="Agent message background (hex)")
    message_style: str = Field("rounded", description="Message bubble style (rounded/square)")
    font_family: str | None = Field(None, description="Font family")
    font_size: str = Field("md", description="Font size (sm/md/lg)")
    spacing: str = Field("compact", description="Spacing (compact/normal/relaxed)")


class BrandingConfig(BaseModel):
    """Branding configuration."""

    page_title: str | None = Field(None, description="Page title")
    meta_description: str | None = Field(None, description="Meta description")
    favicon_url: str | None = Field(None, description="Favicon URL")


class ChatPageConfig(BaseModel):
    """Chat page customization configuration."""

    # Logo
    logo_url: str | None = Field(None, description="Custom logo URL")

    # Layout
    show_left_sidebar: bool = Field(True, description="Show left sidebar")
    right_sidebar: RightSidebarConfig | None = Field(None, description="Right sidebar config")

    # Header
    header: HeaderConfig | None = Field(None, description="Header configuration")

    # Footer
    footer: FooterConfig | None = Field(None, description="Footer configuration")

    # Theme
    theme: ThemeConfig | None = Field(None, description="Theme configuration")

    # Branding
    branding: BrandingConfig | None = Field(None, description="Branding configuration")

    # Legacy fields for backward compatibility
    title: str | None = Field(None, description="Custom page title (deprecated, use branding.page_title)")
    primary_color: str | None = Field(None, description="Primary brand color (deprecated, use theme.primary_color)")
    secondary_color: str | None = Field(
        None, description="Secondary brand color (deprecated, use theme.secondary_color)"
    )
    background_color: str | None = Field(None, description="Background color (deprecated, use theme.background_color)")
    text_color: str | None = Field(None, description="Text color (deprecated)")
    chat_bubble_color: str | None = Field(None, description="Chat bubble color (deprecated)")
    user_message_color: str | None = Field(
        None, description="User message color (deprecated, use theme.user_message_bg)"
    )
    bot_message_color: str | None = Field(
        None, description="Bot message color (deprecated, use theme.agent_message_bg)"
    )
    welcome_message: str | None = Field(None, description="Welcome message (deprecated)")
    description: str | None = Field(None, description="Agent description (deprecated)")
    footer_text: str | None = Field(None, description="Footer text (deprecated, use footer.content)")
    custom_css: str | None = Field(None, description="Custom CSS styles")
    show_branding: bool = Field(True, description="Show Synkora branding")
    enable_file_upload: bool = Field(True, description="Enable file uploads")
    enable_voice_input: bool = Field(False, description="Enable voice input")
    meta_title: str | None = Field(None, description="Meta title for SEO (deprecated, use branding.page_title)")
    meta_description: str | None = Field(
        None, description="Meta description for SEO (deprecated, use branding.meta_description)"
    )
    meta_keywords: str | None = Field(None, description="Meta keywords for SEO (deprecated)")
    favicon_url: str | None = Field(None, description="Custom favicon URL (deprecated, use branding.favicon_url)")

    @field_validator(
        "primary_color",
        "secondary_color",
        "background_color",
        "text_color",
        "chat_bubble_color",
        "user_message_color",
        "bot_message_color",
    )
    @classmethod
    def validate_hex_color(cls, v):
        """Validate hex color format."""
        if v and not v.startswith("#"):
            raise ValueError("Color must be in hex format (e.g., #FF5733)")
        if v and len(v) not in [4, 7]:  # #RGB or #RRGGBB
            raise ValueError("Invalid hex color format")
        return v


class AgentDomainBase(BaseModel):
    """Base schema for agent domain."""

    subdomain: str | None = Field(None, description="Subdomain (e.g., 'myagent')")
    domain: str | None = Field(None, description="Custom domain (e.g., 'chat.example.com')")
    is_custom_domain: bool = Field(False, description="Whether this is a custom domain")
    is_active: bool = Field(True, description="Whether the domain is active")
    chat_page_config: ChatPageConfig | None = Field(None, description="Chat page customization")


class AgentDomainCreate(AgentDomainBase):
    """Schema for creating an agent domain."""

    pass


class AgentDomainUpdate(BaseModel):
    """Schema for updating an agent domain."""

    subdomain: str | None = None
    domain: str | None = None
    is_custom_domain: bool | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    chat_page_config: ChatPageConfig | None = None

    @field_validator("subdomain")
    @classmethod
    def validate_subdomain(cls, v):
        """Validate subdomain is not empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("Subdomain cannot be empty. Every agent must have a subdomain.")
        return v


class AgentDomainResponse(AgentDomainBase):
    """Schema for agent domain response."""

    id: UUID
    agent_id: UUID
    tenant_id: UUID
    is_verified: bool
    verification_token: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DNSRecord(BaseModel):
    """DNS record information."""

    type: str = Field(..., description="Record type (A, CNAME, TXT)")
    name: str = Field(..., description="Record name/host")
    value: str = Field(..., description="Record value")
    ttl: int = Field(3600, description="Time to live in seconds")
    priority: int | None = Field(None, description="Priority (for MX records)")


class DNSRecordsResponse(BaseModel):
    """Response containing required DNS records."""

    records: list[DNSRecord]
    platform_domain: str = Field(..., description="Platform domain to use in DNS configuration")


class DNSVerificationResponse(BaseModel):
    """Response for DNS verification."""

    is_verified: bool
    message: str | None = Field(None, description="Verification message")
    details: dict[str, Any] | None = Field(None, description="Additional verification details for debugging")
