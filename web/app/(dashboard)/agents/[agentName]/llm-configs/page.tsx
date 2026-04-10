'use client'

import { useState } from 'react'
import { useParams} from 'next/navigation'
import { ArrowLeft, X, AlertTriangle } from 'lucide-react'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { LLMConfigForm, LLMConfigList } from '@/components/agents/llm-configs'
import { useLLMConfigManager } from '@/hooks/useAgentLLMConfigs'
import { AgentLLMConfig, AgentLLMConfigCreate, AgentLLMConfigUpdate } from '@/types/agent-llm-config'

export default function AgentLLMConfigsPage() {
  const params = useParams()
  const agentName = params.agentName as string

  const {
    configs,
    isLoading,
    create: createConfig,
    update: updateConfig,
    delete: deleteConfig,
    setDefault: setDefaultConfig,
  } = useLLMConfigManager(agentName)

  const [showForm, setShowForm] = useState(false)
  const [editingConfig, setEditingConfig] = useState<AgentLLMConfig | undefined>()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [deletingConfigId, setDeletingConfigId] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const handleAdd = () => {
    setEditingConfig(undefined)
    setShowForm(true)
  }

  const handleEdit = (config: AgentLLMConfig) => {
    setEditingConfig(config)
    setShowForm(true)
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingConfig(undefined)
  }

  const handleSubmit = async (data: AgentLLMConfigCreate | AgentLLMConfigUpdate) => {
    setIsSubmitting(true)
    try {
      if (editingConfig) {
        await updateConfig(editingConfig.id, data as AgentLLMConfigUpdate)
        toast.success('Configuration updated successfully')
      } else {
        await createConfig(data as AgentLLMConfigCreate)
        toast.success('Configuration created successfully')
      }
      setShowForm(false)
      setEditingConfig(undefined)
    } catch (error: any) {
      toast.error(error.message || 'Failed to save configuration')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = (configId: string) => {
    setDeletingConfigId(configId)
  }

  const confirmDelete = async () => {
    if (!deletingConfigId) return
    setIsDeleting(true)
    try {
      await deleteConfig(deletingConfigId)
      toast.success('Configuration deleted successfully')
      setDeletingConfigId(null)
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete configuration')
    } finally {
      setIsDeleting(false)
    }
  }

  const handleSetDefault = async (configId: string) => {
    try {
      await setDefaultConfig(configId)
      toast.success('Default configuration updated')
    } catch (error: any) {
      toast.error(error.message || 'Failed to set default configuration')
    }
  }

  const handleToggleEnabled = async (configId: string, enabled: boolean) => {
    try {
      await updateConfig(configId, { enabled })
      toast.success(`Configuration ${enabled ? 'enabled' : 'disabled'}`)
    } catch (error: any) {
      toast.error(error.message || 'Failed to update configuration')
    }
  }


  const deletingConfig = configs.find(c => c.id === deletingConfigId)

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40">
      {/* Delete Confirmation Modal */}
      {deletingConfigId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Delete Configuration</h3>
            </div>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete{' '}
              <span className="font-medium text-gray-900">
                {deletingConfig?.name || 'this configuration'}
              </span>
              ? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeletingConfigId(null)}
                disabled={isDeleting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                disabled={isDeleting}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
              >
                {isDeleting && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-4">
            <Link
              href={`/agents/${agentName}/view`}
              className="p-2 hover:bg-red-50 rounded-lg transition-colors text-red-600"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">AI Model Config</h1>
              <p className="text-sm text-gray-500 mt-1">
                Manage AI models for <span className="font-semibold text-gray-700">{agentName}</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {showForm ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900">
                {editingConfig ? 'Edit Configuration' : 'Add Configuration'}
              </h2>
              <button
                onClick={handleCancel}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-600" />
              </button>
            </div>
            <LLMConfigForm
              config={editingConfig}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              isSubmitting={isSubmitting}
            />
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                About AI Model Config
              </h2>
              <p className="text-sm text-gray-600">
                Configure multiple AI models for your agent. The agent will use the default
                configuration for most requests, and can fall back to other enabled configurations
                if needed. You can also specify different models for different use cases.
              </p>
            </div>

            <LLMConfigList
              configs={configs}
              onAdd={handleAdd}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onSetDefault={handleSetDefault}
              onToggleEnabled={handleToggleEnabled}
              isLoading={isLoading}
            />
          </div>
        )}
      </div>
    </div>
  )
}
