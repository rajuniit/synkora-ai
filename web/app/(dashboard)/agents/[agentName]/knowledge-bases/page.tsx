'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/ErrorAlert'
import EmptyState from '@/components/common/EmptyState'
import { apiClient } from '@/lib/api/client'

interface Agent {
  id: number
  name: string
  type: string
}

interface KnowledgeBase {
  id: number
  name: string
  description: string
  vector_db_provider: string
  total_documents: number
  total_chunks: number
}

interface AgentKnowledgeBase {
  id: number
  agent_id: number
  knowledge_base_id: number
  knowledge_base?: KnowledgeBase
  name?: string
  description?: string
  vector_db_provider?: string
  total_documents?: number
  total_chunks?: number
  retrieval_config: {
    top_k: number
    score_threshold: number
    include_metadata: boolean
  }
  created_at: string
  is_active?: boolean
}

export default function AgentKnowledgeBasesPage() {
  const params = useParams()
  const agentName = params.agentName as string

  const [agent, setAgent] = useState<Agent | null>(null)
  const [attachedKBs, setAttachedKBs] = useState<AgentKnowledgeBase[]>([])
  const [availableKBs, setAvailableKBs] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showAttachModal, setShowAttachModal] = useState(false)
  const [selectedKbId, setSelectedKbId] = useState<number | null>(null)
  const [attachConfig, setAttachConfig] = useState({
    top_k: 5,
    score_threshold: 0.7,
    include_metadata: true,
  })

  useEffect(() => {
    fetchAgent()
    fetchAvailableKBs()
  }, [agentName])

  useEffect(() => {
    if (agent) {
      fetchAttachedKBs()
    }
  }, [agent])

  const fetchAgent = async () => {
    try {
      const data = await apiClient.getAgent(agentName)
      setAgent({
        id: data.id,
        name: data.agent_name,
        type: data.agent_type
      })
    } catch (err) {
      console.error('Failed to fetch agent:', err)
    }
  }

  const fetchAttachedKBs = async () => {
    if (!agent) return
    
    try {
      setLoading(true)
      const kbs = await apiClient.getAgentKnowledgeBases(agent.id.toString())
      setAttachedKBs(kbs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const fetchAvailableKBs = async () => {
    try {
      const data: any = await apiClient.getKnowledgeBases()
      // Handle both response formats
      const kbs = data?.data?.knowledge_bases || data?.data || data || []
      setAvailableKBs(kbs)
    } catch (err) {
      console.error('Failed to fetch knowledge bases:', err)
    }
  }

  const handleAttach = async () => {
    if (!agent || !selectedKbId) return

    try {
      await apiClient.addKnowledgeBaseToAgent(agent.id.toString(), {
        knowledge_base_id: selectedKbId,
        retrieval_config: attachConfig,
      })

      setShowAttachModal(false)
      setSelectedKbId(null)
      fetchAttachedKBs()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to attach knowledge base')
    }
  }

  const handleDetach = async (kbId: number, kbName: string) => {
    if (!agent) return
    
    if (!confirm(`Are you sure you want to detach "${kbName}" from this agent?`)) {
      return
    }

    try {
      await apiClient.removeKnowledgeBaseFromAgent(agent.id.toString(), kbId.toString())
      fetchAttachedKBs()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to detach knowledge base')
    }
  }

  const getProviderBadgeColor = (provider: string) => {
    const colors: Record<string, string> = {
      QDRANT: 'bg-blue-100 text-blue-800',
      PINECONE: 'bg-purple-100 text-purple-800',
      WEAVIATE: 'bg-green-100 text-green-800',
      CHROMA: 'bg-orange-100 text-orange-800',
      MILVUS: 'bg-primary-100 text-primary-800',
    }
    return colors[provider.toUpperCase()] || 'bg-gray-100 text-gray-800'
  }

  const getUnattachedKBs = () => {
    const attachedIds = attachedKBs.map(akb => akb.knowledge_base_id)
    return availableKBs.filter(kb => !attachedIds.includes(kb.id))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          href={`/agents/${agentName}/view`}
          className="text-red-600 hover:text-red-700 flex items-center gap-2 mb-4 text-sm font-medium"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Agent
        </Link>
        
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Knowledge Bases</h1>
            <p className="text-gray-600 mt-1 text-sm">
              Configure which knowledge bases {agent?.name || agentName} can access
            </p>
          </div>
          
          <button
            onClick={() => setShowAttachModal(true)}
            disabled={getUnattachedKBs().length === 0}
            className="px-3 py-1.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed text-xs font-medium shadow-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Attach Knowledge Base
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorAlert message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      {/* Attached Knowledge Bases */}
      {attachedKBs.length === 0 ? (
        <EmptyState
          icon={
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
          }
          title="No knowledge bases attached"
          description="Attach a knowledge base to enable RAG capabilities for this agent."
          actionLabel={getUnattachedKBs().length > 0 ? "Attach Knowledge Base" : undefined}
          onAction={getUnattachedKBs().length > 0 ? () => setShowAttachModal(true) : undefined}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {attachedKBs.map((akb) => (
            <div
              key={akb.id}
              className="bg-white rounded-lg border border-gray-200 p-5 hover:border-red-300 hover:shadow-md transition-all"
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <Link
                  href={`/knowledge-bases/${akb.knowledge_base_id}`}
                  className="flex-1"
                >
                  <h3 className="text-base font-semibold text-gray-900 hover:text-primary-600 transition-colors">
                    {akb.knowledge_base?.name || akb.name || 'Unknown KB'}
                  </h3>
                  <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                    {akb.knowledge_base?.description || akb.description || ''}
                  </p>
                </Link>
              </div>

              {/* Provider Badge */}
              <div className="mb-4">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getProviderBadgeColor(akb.knowledge_base?.vector_db_provider || akb.vector_db_provider || 'unknown')}`}>
                  {akb.knowledge_base?.vector_db_provider || akb.vector_db_provider || 'unknown'}
                </span>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-3 mb-4 py-3 border-t border-b border-gray-100">
                <div>
                  <p className="text-xs text-gray-500">Documents</p>
                  <p className="text-base font-semibold text-gray-900">
                    {akb.knowledge_base?.total_documents ?? akb.total_documents ?? 0}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Chunks</p>
                  <p className="text-base font-semibold text-gray-900">
                    {akb.knowledge_base?.total_chunks ?? akb.total_chunks ?? 0}
                  </p>
                </div>
              </div>

              {/* Retrieval Config */}
              <div className="mb-4">
                <p className="text-xs text-gray-500 mb-2 font-medium">Retrieval Settings</p>
                <div className="space-y-1 bg-gray-50 rounded-md p-2.5">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">Top K:</span>
                    <span className="text-gray-900 font-medium">{akb.retrieval_config.top_k}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">Score Threshold:</span>
                    <span className="text-gray-900 font-medium">{akb.retrieval_config.score_threshold}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">Include Metadata:</span>
                    <span className="text-gray-900 font-medium">
                      {akb.retrieval_config.include_metadata ? 'Yes' : 'No'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <button
                onClick={() => handleDetach(akb.knowledge_base_id, akb.knowledge_base?.name || akb.name || 'KB')}
                className="w-full px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
              >
                Detach
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Attach Modal */}
      {showAttachModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto shadow-2xl border border-gray-200">
            <div className="flex justify-between items-center mb-5">
              <h2 className="text-xl font-bold text-gray-900">Attach Knowledge Base</h2>
              <button
                onClick={() => {
                  setShowAttachModal(false)
                  setSelectedKbId(null)
                }}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Select Knowledge Base */}
            <div className="mb-5">
              <label className="block text-xs font-medium text-gray-700 mb-2">
                Select Knowledge Base
              </label>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {getUnattachedKBs().map((kb) => (
                  <button
                    key={kb.id}
                    onClick={() => setSelectedKbId(kb.id)}
                    className={`w-full text-left p-3.5 rounded-lg border-2 transition-all ${
                      selectedKbId === kb.id
                        ? 'border-red-500 bg-red-50'
                        : 'border-gray-200 hover:border-red-200'
                    }`}
                  >
                    <h3 className="text-sm font-semibold text-gray-900">{kb.name}</h3>
                    <p className="text-xs text-gray-600 mt-1">{kb.description}</p>
                    <div className="flex gap-2 mt-2">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs ${getProviderBadgeColor(kb.vector_db_provider)}`}>
                        {kb.vector_db_provider}
                      </span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-700">
                        {kb.total_documents} docs
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Retrieval Configuration */}
            {selectedKbId && (
              <div className="space-y-4 mb-5">
                <h3 className="text-base font-semibold text-gray-900">Retrieval Configuration</h3>
                
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">
                    Top K Results
                  </label>
                  <input
                    type="number"
                    value={attachConfig.top_k}
                    onChange={(e) => setAttachConfig({ ...attachConfig, top_k: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                    min="1"
                    max="20"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Number of relevant chunks to retrieve (1-20)
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">
                    Score Threshold
                  </label>
                  <input
                    type="number"
                    value={attachConfig.score_threshold}
                    onChange={(e) => setAttachConfig({ ...attachConfig, score_threshold: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                    min="0"
                    max="1"
                    step="0.1"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Minimum similarity score (0.0-1.0)
                  </p>
                </div>

                <div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={attachConfig.include_metadata}
                      onChange={(e) => setAttachConfig({ ...attachConfig, include_metadata: e.target.checked })}
                      className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                    />
                    <span className="text-xs text-gray-700">Include metadata in results</span>
                  </label>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={handleAttach}
                disabled={!selectedKbId}
                className="flex-1 px-4 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium shadow-sm"
              >
                Attach Knowledge Base
              </button>
              <button
                onClick={() => {
                  setShowAttachModal(false)
                  setSelectedKbId(null)
                }}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  )
}
