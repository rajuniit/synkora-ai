import { useState, useEffect } from 'react'
import { integrationsApi } from '@/lib/api/integrations'
import type { IntegrationConfig } from '@/types/integrations'

export function useIntegrations(integrationType?: string) {
  const [configs, setConfigs] = useState<IntegrationConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchConfigs = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await integrationsApi.getConfigs(integrationType)
      setConfigs(data)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch integration configs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConfigs()
  }, [integrationType])

  const createConfig = async (data: {
    integration_type: string
    provider: string
    config_data: any
  }) => {
    try {
      const newConfig = await integrationsApi.createConfig(data)
      setConfigs([...configs, newConfig])
      return newConfig
    } catch (err: any) {
      throw new Error(err.message || 'Failed to create integration config')
    }
  }

  const updateConfig = async (id: string, data: {
    config_data?: any
    is_active?: boolean
    is_default?: boolean
  }) => {
    try {
      const updatedConfig = await integrationsApi.updateConfig(id, data)
      setConfigs(configs.map(c => c.id === id ? updatedConfig : c))
      return updatedConfig
    } catch (err: any) {
      throw new Error(err.message || 'Failed to update integration config')
    }
  }

  const deleteConfig = async (id: string) => {
    try {
      await integrationsApi.deleteConfig(id)
      setConfigs(configs.filter(c => c.id !== id))
    } catch (err: any) {
      throw new Error(err.message || 'Failed to delete integration config')
    }
  }

  const testConnection = async (id: string) => {
    try {
      return await integrationsApi.testConnection(id)
    } catch (err: any) {
      throw new Error(err.message || 'Failed to test connection')
    }
  }

  const activateConfig = async (id: string) => {
    try {
      const updatedConfig = await integrationsApi.activateConfig(id)
      setConfigs(configs.map(c => 
        c.id === id ? updatedConfig : 
        c.integration_type === updatedConfig.integration_type ? { ...c, is_active: false } : c
      ))
      return updatedConfig
    } catch (err: any) {
      throw new Error(err.message || 'Failed to activate integration config')
    }
  }

  const refetch = fetchConfigs

  return {
    configs,
    loading,
    error,
    fetchConfigs,
    createConfig,
    updateConfig,
    deleteConfig,
    testConnection,
    activateConfig,
    refetch,
  }
}
