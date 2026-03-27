'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { 
  Webhook, 
  ArrowLeft, 
  Plus,
  List,
  Activity
} from 'lucide-react'
import { WebhookList, WebhookForm, WebhookEvents } from '@/components/webhooks'

type TabType = 'list' | 'create' | 'events'

export default function AgentWebhooksPage() {
  const params = useParams()
  const agentName = decodeURIComponent(params?.agentName as string || '')
  const [activeTab, setActiveTab] = useState<TabType>('list')
  const [refreshKey, setRefreshKey] = useState(0)

  const handleWebhookCreated = () => {
    setActiveTab('list')
    setRefreshKey(prev => prev + 1)
  }

  const handleCreateClick = () => {
    setActiveTab('create')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-red-50/30 to-gray-50 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Link
            href={`/agents/${encodeURIComponent(agentName)}/view`}
            className="inline-flex items-center gap-2 text-red-600 hover:text-red-700 font-medium mb-3 transition-colors text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Agent
          </Link>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-red-100 rounded-lg">
                <Webhook className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Webhooks</h1>
                <p className="text-gray-600 mt-1 text-sm">
                  Manage webhook integrations for {agentName}
                </p>
              </div>
            </div>
            {activeTab === 'list' && (
              <button
                onClick={handleCreateClick}
                className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-lg transition-all shadow-sm hover:shadow-md"
              >
                <Plus className="w-4 h-4" />
                Add Webhook
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
                Webhooks
              </button>
              <button
                onClick={() => setActiveTab('events')}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'events'
                    ? 'border-red-500 text-red-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Activity className="w-4 h-4" />
                Event History
              </button>
              {activeTab === 'create' && (
                <button
                  className="flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 border-red-500 text-red-600"
                >
                  <Plus className="w-4 h-4" />
                  Create Webhook
                </button>
              )}
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          {activeTab === 'list' && (
            <WebhookList
              agentName={agentName}
              refreshKey={refreshKey}
              onCreateClick={handleCreateClick}
            />
          )}
          {activeTab === 'create' && (
            <WebhookForm
              agentName={agentName}
              onSuccess={handleWebhookCreated}
              onCancel={() => setActiveTab('list')}
            />
          )}
          {activeTab === 'events' && (
            <WebhookEvents agentName={agentName} />
          )}
        </div>
      </div>
    </div>
  )
}
