/**
 * Social Authentication API Client
 * 
 * API functions for social login and account linking
 */

import { apiClient } from './client';
import type {
  SocialProvider,
  SocialAuthProvider,
  LinkProviderRequest,
  ProviderStatus,
} from '@/types/social-auth';

const getApiUrl = (): string => {
  if (typeof window !== 'undefined') {
    // In browser, construct from current location
    const { protocol, hostname } = window.location;
    const port = hostname === 'localhost' ? '8000' : '';
    return port ? `${protocol}//${hostname}:${port}` : `${protocol}//${hostname}`;
  }
  return 'http://localhost:8000';
};

/**
 * Get OAuth login URL for a provider
 */
export const getLoginUrl = (provider: SocialProvider, redirectUrl?: string): Promise<{ authorization_url: string }> => {
  const params = new URLSearchParams({ provider });
  if (redirectUrl) {
    params.append('redirect_url', redirectUrl);
  }
  // Return as promise to match hook expectations
  return Promise.resolve({
    authorization_url: `${getApiUrl()}/api/v1/auth/social/login?${params.toString()}`
  });
};

/**
 * Get list of linked social providers for current user
 */
export const getLinkedProviders = async (): Promise<SocialAuthProvider[]> => {
  const data = await apiClient.request('GET', '/api/v1/auth/social/providers');
  return data.data || data;
};

/**
 * Link a social provider to current account
 */
export const linkProvider = async (data: LinkProviderRequest): Promise<{ url: string }> => {
  const response = await apiClient.request('POST', '/api/v1/auth/social/link', data);
  return response.data || response;
};

/**
 * Unlink a social provider from current account
 */
export const unlinkProvider = async (provider: SocialProvider): Promise<void> => {
  await apiClient.request('DELETE', `/api/v1/auth/social/unlink/${provider}`);
};

/**
 * Check if a provider is linked
 */
export const getProviderStatus = async (provider: SocialProvider): Promise<ProviderStatus> => {
  const data = await apiClient.request('GET', `/api/v1/auth/social/status/${provider}`);
  return data.data || data;
};

/**
 * Handle OAuth callback (called by backend, but useful for client-side validation)
 */
export const handleCallback = async (params: URLSearchParams): Promise<void> => {
  // This is typically handled by the backend redirect
  // but we can use it for client-side error handling
  const error = params.get('error');
  if (error) {
    throw new Error(params.get('message') || 'Authentication failed');
  }
};

// Also export as object for backward compatibility
export const socialAuthApi = {
  getLoginUrl,
  getLinkedProviders,
  linkProvider,
  unlinkProvider,
  getProviderStatus,
  handleCallback,
};
