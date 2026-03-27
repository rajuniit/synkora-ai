'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { 
  Send, 
  ArrowLeft, 
  Plus,
  List
} from 'lucide-react'
import { OutputConfigList, OutputConfigForm } from '@/components/agent-outputs'
import { useAgentOutputs } from '@/hooks/useAgentOutputs'
import { apiClient } from '@/lib/api/client'
import type { OutputConfig, CreateOutputConfigData } from '@/types/agent-outputs'
import toast from 'react-hot-toast'

type TabType = 'list' | 'create' | 'edit'

export default function AgentOutputsPage() {
  const params = useParams()
  const agentName = decodeURIComponent(params?.agentName as string || '')
  const [activeTab, setActiveTab] = useState<TabType>('list')
  const [refreshKey, setRefreshKey] = useState(0)
  const [editingConfig, setEditingConfig] = useState<OutputConfig | undefined>()
  const [agentId, setAgentId] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const { createOutput, updateOutput } = useAgentOutputs(agentId)

  // Fetch agent to get ID
  useEffect(() => {
    const fetchAgent = async () => {
      try {
        setLoading(true)
        const agent = await apiClient.getAgent(agentName)
        setAgentId(agent.id)
      } catch (error) {
        toast.error('Failed to load agent')
        console.error('Error fetching agent:', error)
      } finally {
        setLoading(false)
      }
    }

    if (agentName) {
      fetchAgent()
    }
  }, [agentName])

  const handleOutputSubmit = async (data: CreateOutputConfigData) => {
    try {
      if (editingConfig) {
        await updateOutput(editingConfig.id, data)
        toast.success('Output configuration updated successfully')
      } else {
        await createOutput(data)
        toast.success('Output configuration created successfully')
      }
      setActiveTab('list')
      setEditingConfig(undefined)
      setRefreshKey(prev => prev + 1)
    } catch (error: any) {
      toast.error(error.message || 'Failed to save output configuration')
      throw error
    }
  }

  const handleCreateClick = () => {
    setEditingConfig(undefined)
    setActiveTab('create')
  }

  const handleEditClick = (config: OutputConfig) => {
    setEditingConfig(config)
    setActiveTab('edit')
  }

  const handleCancel = () => {
    setActiveTab('list')
    setEditingConfig(undefined)
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Link
            href={`/agents/${encodeURIComponent(agentName)}/view`}
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 font-medium mb-3 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Agent
          </Link>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-xl sm:text-3xl font-bold text-gray-900">Output Configurations</h1>
              <p className="text-gray-600 mt-1">
                Route agent responses to Slack, Email, or Webhooks for {agentName}
              </p>
            </div>
            {activeTab === 'list' && (
              <button
                onClick={handleCreateClick}
                className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-lg transition-all shadow-sm hover:shadow-md"
              >
                <Plus className="w-4 h-4" />
                Add Output
              </button>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              <button
                onClick={() => setActiveTab('list')}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'list'
                    ? 'border-red-500 text-red-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <List className="w-4 h-4" />
                Output Configurations
              </button>
              {activeTab === 'create' && (
                <button
                  className="flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 border-red-500 text-red-600"
                >
                  <Plus className="w-4 h-4" />
                  Create Output
                </button>
              )}
              {activeTab === 'edit' && (
                <button
                  className="flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 border-red-500 text-red-600"
                >
                  <Plus className="w-4 h-4" />
                  Edit Output
                </button>
              )}
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Loading agent...</div>
          ) : agentId ? (
            <>
              {activeTab === 'list' && (
                <OutputConfigList
                  agentId={agentId}
                  refreshKey={refreshKey}
                  onCreateClick={handleCreateClick}
                  onEditClick={handleEditClick}
                />
              )}
              {(activeTab === 'create' || activeTab === 'edit') && (
                <OutputConfigForm
                  output={editingConfig}
                  onSubmit={handleOutputSubmit}
                  onCancel={handleCancel}
                />
              )}
            </>
          ) : (
            <div className="p-8 text-center text-red-500">Failed to load agent</div>
          )}
        </div>
      </div>
    </div>
  )
}
