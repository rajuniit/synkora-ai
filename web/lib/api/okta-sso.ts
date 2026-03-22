/**
 * Okta SSO API Client
 * 
 * API functions for Okta SSO configuration and authentication
 */

import { apiClient } from './client';
import type {
  OktaTenant,
  OktaTenantCreate,
  OktaTenantUpdate,
  OktaSSOConfig,
} from '@/types/okta-sso';

export const oktaSSOApi = {
  /**
   * Get Okta tenant configuration for current tenant
   */
  getOktaTenant: async (): Promise<OktaTenant | null> => {
    try {
      const data = await apiClient.request('GET', '/api/v1/sso/okta/config');
      return data.data || data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },

  /**
   * Create Okta tenant configuration
   */
  createOktaTenant: async (config: OktaTenantCreate): Promise<OktaTenant> => {
    const data = await apiClient.request('POST', '/api/v1/sso/okta/config', config);
    return data.data || data;
  },

  /**
   * Update Okta tenant configuration
   */
  updateOktaTenant: async (config: OktaTenantUpdate): Promise<OktaTenant> => {
    const data = await apiClient.request('PUT', '/api/v1/sso/okta/config', config);
    return data.data || data;
  },

  /**
   * Delete Okta tenant configuration
   */
  deleteOktaTenant: async (): Promise<void> => {
    await apiClient.request('DELETE', '/api/v1/sso/okta/config');
  },

  /**
   * Test Okta SSO configuration
   */
  testOktaConfig: async (config: OktaSSOConfig): Promise<{ success: boolean; message: string }> => {
    const data = await apiClient.request('POST', '/api/v1/sso/okta/test', config);
    return data.data || data;
  },

  /**
   * Get Okta SSO login URL
   */
  getOktaLoginUrl: async (redirectUrl?: string): Promise<{ url: string }> => {
    const params = redirectUrl ? { redirect_url: redirectUrl } : {};
    const data = await apiClient.request('GET', '/api/v1/sso/okta/login', undefined, { params });
    return data.data || data;
  },

  /**
   * Handle Okta SSO callback (called by backend, but useful for client-side validation)
   */
  handleOktaCallback: async (params: URLSearchParams): Promise<void> => {
    // This is typically handled by the backend redirect
    // but we can use it for client-side error handling
    const error = params.get('error');
    if (error) {
      throw new Error(params.get('error_description') || 'Okta SSO authentication failed');
    }
  },

  /**
   * Get Okta SSO status for current tenant
   */
  getOktaStatus: async (): Promise<{ enabled: boolean; configured: boolean }> => {
    const data = await apiClient.request('GET', '/api/v1/sso/okta/status');
    return data.data || data;
  },
};
