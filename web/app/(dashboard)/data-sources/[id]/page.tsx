'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import {
  ArrowLeft,
  Database,
  RefreshCw,
  Trash2,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  Calendar,
  Activity,
  Settings,
  Slack,
  Mail,
  TrendingUp,
  TrendingDown,
  History
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'

interface DataSource {
  id: number
  name: string
  type: string
  knowledge_base_id: number | null
  tenant_id: string
  config: Record<string, any>
  status: string
  sync_enabled: boolean
  last_sync_at: string | null
  last_error: string | null
  total_documents: number
  created_at: string
  updated_at: string
}

interface SyncHistory {
  id: number
  started_at: string
  completed_at: string | null
  status: string
  documents_processed: number
  documents_added: number
  documents_updated: number
  documents_deleted: number
  documents_failed: number
  error_message: string | null
}

export default function DataSourceDetailsPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [dataSource, setDataSource] = useState<DataSource | null>(null)
  const [syncHistory, setSyncHistory] = useState<SyncHistory[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'config'>('overview')
  const [deleteModal, setDeleteModal] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchDataSource()
    fetchSyncHistory()
  }, [id])

  const fetchDataSource = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getDataSource(id)
      setDataSource(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      toast.error('Failed to load data source')
    } finally {
      setLoading(false)
    }
  }

  const fetchSyncHistory = async () => {
    try {
      const data = await apiClient.getDataSourceSyncHistory(id)
      setSyncHistory(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch sync history:', err)
      setSyncHistory([])
    }
  }

  const handleSync = async () => {
    try {
      setSyncing(true)
      setError(null)
      await apiClient.syncDataSource(id)
      toast.success('Sync started successfully')
      setTimeout(() => {
        fetchDataSource()
        fetchSyncHistory()
        setSyncing(false)
      }, 2000)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to trigger sync'
      setError(errorMessage)
      toast.error(errorMessage)
      setSyncing(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await apiClient.deleteDataSource(id)
      toast.success('Data source deleted successfully')
      router.push('/data-sources')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete data source'
      toast.error(errorMessage)
      setDeleting(false)
    }
  }

  const getSourceIcon = (sourceType: string) => {
    switch (sourceType?.toLowerCase()) {
      case 'SLACK':
        return <Slack className="w-6 h-6" />
      case 'GMAIL':
        return <Mail className="w-6 h-6" />
      default:
        return <Database className="w-6 h-6" />
    }
  }

  const getSourceColor = (sourceType: string) => {
    switch (sourceType?.toLowerCase()) {
      case 'SLACK':
        return 'bg-purple-100 text-purple-800'
      case 'GMAIL':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'syncing':
      case 'in_progress':
        return 'bg-blue-100 text-blue-800'
      case 'paused':
      case 'inactive':
        return 'bg-yellow-100 text-yellow-800'
      case 'error':
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
      case 'completed':
        return <CheckCircle className="w-3 h-3" />
      case 'syncing':
      case 'in_progress':
        return <RefreshCw className="w-3 h-3 animate-spin" />
      case 'error':
      case 'failed':
        return <AlertCircle className="w-3 h-3" />
      default:
        return <Clock className="w-3 h-3" />
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error || !dataSource) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border-l-4 border-red-500 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-red-700">{error || 'Data source not found'}</p>
            </div>
          </div>
          <Link
            href="/data-sources"
            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Data Sources
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Back Button */}
        <Link
          href="/data-sources"
          className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Data Sources
        </Link>

        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4 flex-1">
              <div className={`p-3 rounded-lg ${getSourceColor(dataSource.type)}`}>
                {getSourceIcon(dataSource.type)}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="text-2xl font-bold text-gray-900">{dataSource.name}</h1>
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor(dataSource.status)}`}>
                    {getStatusIcon(dataSource.status)}
                    {dataSource.status}
                  </span>
                </div>
                <p className="text-gray-600 mb-2">
                  {dataSource.type?.toUpperCase()} Data Source
                </p>
                {dataSource.knowledge_base_id && (
                  <Link
                    href={`/knowledge-bases/${dataSource.knowledge_base_id}`}
                    className="text-sm text-blue-600 hover:text-blue-700 inline-flex items-center gap-1"
                  >
                    <Database className="w-4 h-4" />
                    View Knowledge Base
                  </Link>
                )}
              </div>
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={handleSync}
                disabled={syncing || dataSource.status === 'syncing' || !dataSource.sync_enabled}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                {syncing ? 'Syncing...' : 'Sync Now'}
              </button>
              <button
                onClick={() => setDeleteModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {dataSource.last_error && (
          <div className="bg-red-50 border-l-4 border-red-500 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <div>
                <p className="font-medium text-red-800">Sync Error</p>
                <p className="text-sm text-red-700 mt-1">{dataSource.last_error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-blue-100 rounded-lg">
                <FileText className="w-5 h-5 text-blue-600" />
              </div>
              <p className="text-sm font-medium text-gray-600">Documents</p>
            </div>
            <p className="text-3xl font-bold text-gray-900">{dataSource.total_documents}</p>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-green-100 rounded-lg">
                <Clock className="w-5 h-5 text-green-600" />
              </div>
              <p className="text-sm font-medium text-gray-600">Last Sync</p>
            </div>
            <p className="text-lg font-semibold text-gray-900">
              {dataSource.last_sync_at
                ? new Date(dataSource.last_sync_at).toLocaleDateString()
                : 'Never'}
            </p>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Activity className="w-5 h-5 text-purple-600" />
              </div>
              <p className="text-sm font-medium text-gray-600">Sync Status</p>
            </div>
            <p className="text-lg font-semibold text-gray-900 capitalize">
              {dataSource.sync_enabled ? 'Enabled' : 'Disabled'}
            </p>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-orange-100 rounded-lg">
                <Calendar className="w-5 h-5 text-orange-600" />
              </div>
              <p className="text-sm font-medium text-gray-600">Created</p>
            </div>
            <p className="text-sm font-semibold text-gray-900">
              {new Date(dataSource.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6">
              <button
                onClick={() => setActiveTab('overview')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'overview'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4" />
                  Overview
                </div>
              </button>
              <button
                onClick={() => setActiveTab('history')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'history'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4" />
                  Sync History ({syncHistory.length})
                </div>
              </button>
              <button
                onClick={() => setActiveTab('config')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'config'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Settings className="w-4 h-4" />
                  Configuration
                </div>
              </button>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'overview' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Source Information</h2>
                  <dl className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <dt className="text-sm font-medium text-gray-500 mb-1">Source Type</dt>
                      <dd className="text-base font-semibold text-gray-900 capitalize">{dataSource.type}</dd>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <dt className="text-sm font-medium text-gray-500 mb-1">Status</dt>
                      <dd className="text-base font-semibold text-gray-900 capitalize">{dataSource.status}</dd>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <dt className="text-sm font-medium text-gray-500 mb-1">Created</dt>
                      <dd className="text-base font-semibold text-gray-900">
                        {new Date(dataSource.created_at).toLocaleString()}
                      </dd>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <dt className="text-sm font-medium text-gray-500 mb-1">Last Updated</dt>
                      <dd className="text-base font-semibold text-gray-900">
                        {new Date(dataSource.updated_at).toLocaleString()}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>
            )}

            {activeTab === 'history' && (
              <div className="space-y-4">
                {syncHistory.length === 0 ? (
                  <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
                    <History className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-600 font-medium">No sync history available</p>
                    <p className="text-sm text-gray-500 mt-1">Sync history will appear here after the first sync</p>
                  </div>
                ) : (
                  syncHistory.map((sync) => (
                    <div key={sync.id} className="bg-gray-50 rounded-lg border border-gray-200 p-6 hover:border-blue-300 transition-colors">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <p className="text-sm font-semibold text-gray-900">
                            {new Date(sync.started_at).toLocaleString()}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            Duration: {sync.completed_at
                              ? `${Math.round((new Date(sync.completed_at).getTime() - new Date(sync.started_at).getTime()) / 1000)}s`
                              : 'In progress'}
                          </p>
                        </div>
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor(sync.status)}`}>
                          {getStatusIcon(sync.status)}
                          {sync.status}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-white rounded-lg p-3">
                          <p className="text-xs text-gray-500 mb-1">Processed</p>
                          <p className="text-xl font-bold text-gray-900">{sync.documents_processed}</p>
                        </div>
                        <div className="bg-white rounded-lg p-3">
                          <div className="flex items-center gap-1 mb-1">
                            <TrendingUp className="w-3 h-3 text-green-600" />
                            <p className="text-xs text-gray-500">Added</p>
                          </div>
                          <p className="text-xl font-bold text-green-600">{sync.documents_added}</p>
                        </div>
                        <div className="bg-white rounded-lg p-3">
                          <p className="text-xs text-gray-500 mb-1">Updated</p>
                          <p className="text-xl font-bold text-blue-600">{sync.documents_updated}</p>
                        </div>
                        <div className="bg-white rounded-lg p-3">
                          <div className="flex items-center gap-1 mb-1">
                            <TrendingDown className="w-3 h-3 text-red-600" />
                            <p className="text-xs text-gray-500">Failed</p>
                          </div>
                          <p className="text-xl font-bold text-red-600">{sync.documents_failed}</p>
                        </div>
                      </div>
                      {sync.error_message && (
                        <div className="mt-4 bg-red-50 border-l-4 border-red-500 rounded p-3">
                          <p className="text-xs font-medium text-red-800 mb-1">Error Message</p>
                          <p className="text-sm text-red-700">{sync.error_message}</p>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === 'config' && (
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Configuration</h2>
                <div className="space-y-3">
                  {Object.entries(dataSource.config).length === 0 ? (
                    <div className="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
                      <Settings className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                      <p className="text-gray-600">No configuration available</p>
                    </div>
                  ) : (
                    Object.entries(dataSource.config).map(([key, value]) => (
                      <div key={key} className="flex items-start justify-between py-3 px-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                        <span className="text-sm font-medium text-gray-700 capitalize">
                          {key.replace(/_/g, ' ')}
                        </span>
                        <span className="text-sm text-gray-900 font-mono">
                          {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Delete Data Source</h3>
            </div>
            
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete this <span className="font-semibold">{dataSource.type}</span> data source? 
              This action cannot be undone and will permanently delete all associated documents.
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteModal(false)}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {deleting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
