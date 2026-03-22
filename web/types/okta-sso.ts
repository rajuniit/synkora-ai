/**
 * Okta SSO Types
 * 
 * Type definitions for Okta Single Sign-On configuration and authentication
 */

export interface OktaTenant {
  id: string;
  tenant_id: string;
  okta_domain: string;
  client_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OktaTenantCreate {
  okta_domain: string;
  client_id: string;
  client_secret: string;
  is_active?: boolean;
}

export interface OktaTenantUpdate {
  okta_domain?: string;
  client_id?: string;
  client_secret?: string;
  is_active?: boolean;
}

export interface OktaSSOConfig {
  okta_domain: string;
  client_id: string;
  client_secret: string;
}

export interface OktaSsoCallbackParams {
  login?: string;
  email?: string;
  error?: string;
  message?: string;
}

// Form validation schemas
export interface OktaSsoFormData {
  okta_domain: string;
  client_id: string;
  client_secret: string;
  is_active: boolean;
}

// Helper function to validate Okta domain format
export function isValidOktaDomain(domain: string): boolean {
  // Okta domain should be in format: {subdomain}.okta.com or {subdomain}.oktapreview.com
  const oktaDomainRegex = /^[a-zA-Z0-9-]+\.(okta|oktapreview)\.com$/;
  return oktaDomainRegex.test(domain);
}

// Helper function to format Okta domain
export function formatOktaDomain(domain: string): string {
  // Remove https:// or http:// if present
  let formatted = domain.replace(/^https?:\/\//, '');
  // Remove trailing slash if present
  formatted = formatted.replace(/\/$/, '');
  return formatted;
}
