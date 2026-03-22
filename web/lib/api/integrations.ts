import { apiClient } from './client'
import type { IntegrationConfig, TestConnectionResult } from '@/types/integrations'

export const integrationsApi = {
  // Get all integration configs
  getConfigs: async (integrationType?: string): Promise<IntegrationConfig[]> => {
    const params = integrationType ? { integration_type: integrationType } : {}
    const response = await apiClient.request('GET', '/console/api/integration-configs', undefined, { params })
    return response.data || response
  },

  // Get a specific config
  getConfig: async (id: string): Promise<IntegrationConfig> => {
    const response = await apiClient.request('GET', `/console/api/integration-configs/${id}`)
    return response.data || response
  },

  // Create a new config
  createConfig: async (data: {
    integration_type: string
    provider: string
    config_data: any
    is_active?: boolean
    is_default?: boolean
    is_platform_config?: boolean
  }): Promise<IntegrationConfig> => {
    const response = await apiClient.request('POST', '/console/api/integration-configs', data)
    return response.data || response
  },

  // Update a config
  updateConfig: async (id: string, data: {
    config_data?: any
    is_active?: boolean
    is_default?: boolean
    is_platform_config?: boolean
  }): Promise<IntegrationConfig> => {
    const response = await apiClient.request('PUT', `/console/api/integration-configs/${id}`, data)
    return response.data || response
  },

  // Delete a config
  deleteConfig: async (id: string): Promise<void> => {
    await apiClient.request('DELETE', `/console/api/integration-configs/${id}`)
  },

  // Test connection
  testConnection: async (id: string): Promise<TestConnectionResult> => {
    const response = await apiClient.request('POST', `/console/api/integration-configs/${id}/test`, {})
    return response.data || response
  },

  // Activate a config
  activateConfig: async (id: string): Promise<IntegrationConfig> => {
    const response = await apiClient.request('POST', `/console/api/integration-configs/${id}/activate`)
    return response.data || response
  },
}

// Export individual functions for easier imports
export const getIntegrations = integrationsApi.getConfigs
export const getIntegration = integrationsApi.getConfig
export const createIntegration = integrationsApi.createConfig
export const updateIntegration = integrationsApi.updateConfig
export const deleteIntegration = integrationsApi.deleteConfig
export const testIntegrationConnection = integrationsApi.testConnection
export const activateIntegration = integrationsApi.activateConfig
