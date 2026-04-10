'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Mail, CreditCard, Database, BarChart3, Activity, Lock } from 'lucide-react'
import { useIntegrations } from '@/hooks/useIntegrations'
import { usePermissions } from '@/hooks/usePermissions'
import { IntegrationCard } from '@/components/integrations'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/ErrorAlert'

const INTEGRATION_TYPES = [
  { value: 'email', label: 'Email', icon: Mail, description: 'Email service providers' },
  { value: 'payment', label: 'Payment', icon: CreditCard, description: 'Payment gateways' },
  { value: 'storage', label: 'Storage', icon: Database, description: 'Cloud storage services' },
  { value: 'analytics', label: 'Analytics', icon: BarChart3, description: 'Analytics platforms' },
  { value: 'monitoring', label: 'Monitoring', icon: Activity, description: 'Monitoring services' },
]

export default function IntegrationsPage() {
  const router = useRouter()
  const [selectedType, setSelectedType] = useState<string>('all')
  const { configs, loading, error, testConnection, activateConfig, deleteConfig, refetch } = useIntegrations()
  const { hasPermission, loading: permissionsLoading } = usePermissions()

  // Check permissions
  const canCreate = hasPermission('integration_configs', 'create')
  const canUpdate = hasPermission('integration_configs', 'update')
  const canDelete = hasPermission('integration_configs', 'delete')
  const canRead = hasPermission('integration_configs', 'read')
  const isPlatformOwner = hasPermission('platform', 'read')

  const handleTest = async (id: string) => {
    try {
      await testConnection(id)
      alert('Connection test successful!')
    } catch (err: any) {
      alert(`Connection test failed: ${err.message}`)
    }
  }

  const handleActivate = async (id: string) => {
    try {
      await activateConfig(id)
      await refetch()
    } catch (err: any) {
      alert(`Failed to activate: ${err.message}`)
    }
  }

  const handleDelete = async (id: string) => {
    if (!canDelete) {
      alert('You do not have permission to delete integration configurations')
      return
    }
    
    if (!confirm('Are you sure you want to delete this integration configuration?')) {
      return
    }
    
    try {
      await deleteConfig(id)
      await refetch()
    } catch (err: any) {
      alert(`Failed to delete: ${err.message}`)
    }
  }

  // Filter configs based on role:
  // - Platform Owners see all configs (including platform configs)
  // - Other users only see tenant-specific configs (not platform configs)
  const visibleConfigs = isPlatformOwner 
    ? configs 
    : configs.filter(config => !config.is_platform_config)

  const filteredConfigs = selectedType === 'all'
    ? visibleConfigs
    : visibleConfigs.filter(config => config.integration_type === selectedType)

  if (loading || permissionsLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner />
      </div>
    )
  }

  // Check read permission
  if (!canRead) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <Lock className="mx-auto h-12 w-12 text-yellow-600 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Access Denied
          </h3>
          <p className="text-gray-600">
            You do not have permission to view integration configurations.
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <ErrorAlert message={error} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Integrations</h1>
              <p className="text-gray-600 mt-1 text-sm">
                Manage third-party service integrations
              </p>
            </div>
            {canCreate && (
              <div className="relative group">
                <button className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-lg hover:from-primary-600 hover:to-primary-700 transition-all text-xs font-medium shadow-sm">
                  <Plus size={16} />
                  Add Integration
                </button>
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              {INTEGRATION_TYPES.map(type => {
                const Icon = type.icon
                return (
                  <button
                    key={type.value}
                    onClick={() => router.push(`/settings/integrations/${type.value}/create`)}
                    className="w-full flex items-center gap-3 px-3.5 py-2.5 hover:bg-primary-50 transition-colors first:rounded-t-lg last:rounded-b-lg text-left"
                  >
                    <Icon size={16} className="text-primary-600" />
                    <div>
                      <div className="text-sm font-medium text-gray-900">{type.label}</div>
                      <div className="text-xs text-gray-500">{type.description}</div>
                    </div>
                  </button>
                )
              })}
              </div>
            </div>
          )}
        </div>

        {/* Integration Type Filters */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedType('all')}
            className={`px-3 py-1.5 rounded-lg transition-all text-xs font-medium ${
              selectedType === 'all'
                ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-sm'
                : 'bg-white text-gray-700 hover:bg-primary-50 border border-gray-200'
            }`}
          >
            All
          </button>
          {INTEGRATION_TYPES.map(type => {
            const Icon = type.icon
            return (
              <button
                key={type.value}
                onClick={() => setSelectedType(type.value)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all text-xs font-medium ${
                  selectedType === type.value
                    ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-sm'
                    : 'bg-white text-gray-700 hover:bg-primary-50 border border-gray-200'
                }`}
              >
                <Icon size={14} />
                {type.label}
              </button>
            )
          })}
        </div>
      </div>

        {filteredConfigs.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-primary-50 mb-4">
              <Plus size={28} className="text-primary-500" />
            </div>
            <h3 className="text-base font-semibold text-gray-900 mb-2">
              No integrations found
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              {selectedType === 'all'
                ? 'Get started by adding your first integration using the "Add Integration" button above'
                : `No ${selectedType} integrations configured. Use the "Add Integration" button above to add one.`}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredConfigs.map(config => (
              <div key={config.id} className="bg-white rounded-lg border border-gray-200 shadow-sm hover:border-primary-300 transition-all">
                <IntegrationCard
                  config={config}
                  onTest={handleTest}
                  onActivate={canUpdate ? handleActivate : undefined}
                  onDelete={canDelete ? handleDelete : undefined}
                  isPlatformOwner={isPlatformOwner}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
