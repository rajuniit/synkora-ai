/**
 * Social Auth Provider Configuration API Client
 * 
 * API functions for managing social authentication provider configurations (admin)
 */

import { apiClient } from './client';
import type { SocialProvider } from '@/types/social-auth';

export interface ProviderConfig {
  id: string;
  provider_name: string;
  client_id: string;
  client_secret?: string;
  redirect_uri?: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateProviderConfigRequest {
  provider_name: string;
  client_id: string;
  client_secret: string;
  redirect_uri?: string;
  enabled: string;
}

export interface UpdateProviderConfigRequest {
  client_id?: string;
  client_secret?: string;
  redirect_uri?: string;
  enabled?: string;
}

/**
 * Get all provider configurations
 */
export const listProviderConfigs = async (): Promise<ProviderConfig[]> => {
  const data = await apiClient.request('GET', '/api/v1/social-auth-config');
  return data.providers || data.data || data;
};

/**
 * Get a specific provider configuration
 */
export const getProviderConfig = async (providerName: SocialProvider): Promise<ProviderConfig> => {
  const data = await apiClient.request('GET', `/api/v1/social-auth-config/${providerName}`);
  return data.data || data;
};

/**
 * Create a new provider configuration
 */
export const createProviderConfig = async (config: {
  provider: SocialProvider;
  client_id: string;
  client_secret: string;
  redirect_uri?: string;
  is_enabled: boolean;
}): Promise<ProviderConfig> => {
  // Transform frontend format to backend format
  const backendConfig: CreateProviderConfigRequest = {
    provider_name: config.provider,
    client_id: config.client_id,
    client_secret: config.client_secret,
    redirect_uri: config.redirect_uri,
    enabled: config.is_enabled ? 'true' : 'false',
  };
  
  const data = await apiClient.request('POST', '/api/v1/social-auth-config', backendConfig);
  return data.provider || data.data || data;
};

/**
 * Update an existing provider configuration
 */
export const updateProviderConfig = async (
  providerName: SocialProvider,
  config: {
    provider: SocialProvider;
    client_id: string;
    client_secret?: string;
    redirect_uri?: string;
    is_enabled: boolean;
  }
): Promise<ProviderConfig> => {
  // Transform frontend format to backend format
  const backendConfig: UpdateProviderConfigRequest = {
    client_id: config.client_id,
    redirect_uri: config.redirect_uri,
    enabled: config.is_enabled ? 'true' : 'false',
  };
  
  // Only include client_secret if provided
  if (config.client_secret) {
    backendConfig.client_secret = config.client_secret;
  }
  
  const data = await apiClient.request('PUT', `/api/v1/social-auth-config/${providerName}`, backendConfig);
  return data.provider || data.data || data;
};

/**
 * Delete a provider configuration
 */
export const deleteProviderConfig = async (providerName: SocialProvider): Promise<void> => {
  await apiClient.request('DELETE', `/api/v1/social-auth-config/${providerName}`);
};

/**
 * Test a provider configuration
 */
export const testProviderConfig = async (providerName: SocialProvider): Promise<{ success: boolean; message: string }> => {
  const data = await apiClient.request('POST', `/api/v1/social-auth-config/${providerName}/test`);
  return data.data || data;
};

// Export as object for convenience
export const socialAuthConfigApi = {
  listProviderConfigs,
  getProviderConfig,
  createProviderConfig,
  updateProviderConfig,
  deleteProviderConfig,
  testProviderConfig,
};
