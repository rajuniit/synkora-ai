/**
 * SAML 2.0 SSO API Client
 */

import { apiClient } from './client'
import type { SAMLConfig, SAMLConfigCreateRequest } from '@/types/saml-config'

export const samlConfigApi = {
  /**
   * Get the SAML config for the current tenant.
   * Returns null if no config has been created yet.
   */
  getConfig: async (): Promise<SAMLConfig | null> => {
    try {
      const data = await apiClient.request('GET', '/api/v1/saml/config')
      return data.data ?? data
    } catch (error: any) {
      if (error?.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  /**
   * Create or update the SAML config for the current tenant.
   * Exactly one of idp_metadata_url or idp_metadata_xml must be provided.
   */
  saveConfig: async (config: SAMLConfigCreateRequest): Promise<SAMLConfig> => {
    const data = await apiClient.request('POST', '/api/v1/saml/config', config)
    return data.data ?? data
  },

  /**
   * Delete the SAML config for the current tenant.
   */
  deleteConfig: async (): Promise<void> => {
    await apiClient.request('DELETE', '/api/v1/saml/config')
  },
}
