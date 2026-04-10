'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  Database,
  Plus,
  Trash2,
  Eye,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  Search,
  Filter,
  FileText,
  Slack,
  Mail
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'

interface DataSource {
  id: number
  name: string
  type: string
  knowledge_base_id: number
  knowledge_base_name?: string
  config: Record<string, any>
  status: string
  sync_enabled: boolean
  last_sync_at: string | null
  last_error: string | null
  total_documents: number
  created_at: string
  updated_at: string
}

export default function DataSourcesPage() {
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [filteredSources, setFilteredSources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [deleteModal, setDeleteModal] = useState<{ show: boolean; source: DataSource | null }>({
    show: false,
    source: null,
  })
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchDataSources()
  }, [])

  useEffect(() => {
    filterDataSources()
  }, [searchQuery, filterType, filterStatus, dataSources])

  const fetchDataSources = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getDataSources()
      setDataSources(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      toast.error('Failed to load data sources')
    } finally {
      setLoading(false)
    }
  }

  const filterDataSources = () => {
    let filtered = dataSources

    // Search filter
    if (searchQuery) {
      filtered = filtered.filter(source =>
        source.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        source.type?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    // Type filter
    if (filterType !== 'all') {
      filtered = filtered.filter(source => source.type === filterType)
    }

    // Status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter(source => source.status === filterStatus)
    }

    setFilteredSources(filtered)
  }

  const openDeleteModal = (source: DataSource) => {
    setDeleteModal({ show: true, source })
  }

  const closeDeleteModal = () => {
    setDeleteModal({ show: false, source: null })
  }

  const confirmDelete = async () => {
    if (!deleteModal.source) return

    setDeleting(true)
    try {
      await apiClient.deleteDataSource(deleteModal.source.id.toString())
      toast.success(`Data source deleted successfully`)
      closeDeleteModal()
      fetchDataSources()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete data source'
      toast.error(errorMessage)
    } finally {
      setDeleting(false)
    }
  }

  const getSourceIcon = (sourceType: string) => {
    switch (sourceType?.toLowerCase()) {
      case 'SLACK':
        return <Slack className="w-5 h-5" />
      case 'GMAIL':
        return <Mail className="w-5 h-5" />
      default:
        return <Database className="w-5 h-5" />
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
        return 'bg-green-100 text-green-800'
      case 'syncing':
        return 'bg-blue-100 text-blue-800'
      case 'paused':
        return 'bg-yellow-100 text-yellow-800'
      case 'error':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return <CheckCircle className="w-3 h-3" />
      case 'syncing':
        return <RefreshCw className="w-3 h-3 animate-spin" />
      case 'error':
        return <AlertCircle className="w-3 h-3" />
      default:
        return <Clock className="w-3 h-3" />
    }
  }

  const uniqueTypes = Array.from(new Set(dataSources.map(s => s.type)))
  const uniqueStatuses = Array.from(new Set(dataSources.map(s => s.status)))

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header - More Compact */}
        <div className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-5">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-gradient-to-r from-red-500 to-red-600 rounded-lg shadow-sm">
                <Database className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Data Sources</h1>
                <p className="text-gray-600 mt-0.5 text-sm">
                  Connect and manage data sources for your knowledge bases
                </p>
              </div>
            </div>
            <Link
              href="/data-sources/connect"
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-lg transition-all shadow-sm hover:shadow-md"
            >
              <Plus className="w-4 h-4" />
              Connect Source
            </Link>
          </div>

          {/* Stats Bar - More Compact */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-5">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2.5 mb-1.5">
                <div className="p-1.5 bg-red-100 rounded-lg">
                  <Database className="w-4 h-4 text-red-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Total Sources</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{dataSources.length}</p>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2.5 mb-1.5">
                <div className="p-1.5 bg-green-100 rounded-lg">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Active</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {dataSources.filter(s => s.status === 'active').length}
              </p>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2.5 mb-1.5">
                <div className="p-1.5 bg-purple-100 rounded-lg">
                  <FileText className="w-4 h-4 text-purple-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Documents</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {dataSources.reduce((sum, s) => sum + s.total_documents, 0)}
              </p>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2.5 mb-1.5">
                <div className="p-1.5 bg-red-100 rounded-lg">
                  <RefreshCw className="w-4 h-4 text-red-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Syncing</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {dataSources.filter(s => s.status === 'syncing').length}
              </p>
            </div>
          </div>

          {/* Search and Filter Bar - More Compact */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3.5">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search data sources..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                />
              </div>
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-gray-400" />
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                >
                  <option key="all-types" value="all">All Types</option>
                  {uniqueTypes.map(type => (
                    <option key={`type-${type}`} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                >
                  <option key="all-statuses" value="all">All Statuses</option>
                  {uniqueStatuses.map(status => (
                    <option key={`status-${status}`} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border-l-4 border-red-500 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Data Sources Grid */}
        {filteredSources.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border-2 border-dashed border-gray-300 p-10 text-center">
            <Database className="w-14 h-14 text-gray-400 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-gray-900 mb-1.5">
              {dataSources.length === 0 ? 'No data sources connected' : 'No results found'}
            </h3>
            <p className="text-gray-600 text-sm mb-5">
              {dataSources.length === 0
                ? 'Connect your first data source to start syncing documents.'
                : 'Try adjusting your search or filter criteria.'}
            </p>
            {dataSources.length === 0 && (
              <Link
                href="/data-sources/connect"
                className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-lg transition-all shadow-sm hover:shadow-md"
              >
                <Plus className="w-4 h-4" />
                Connect Data Source
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSources.map((source) => (
              <div
                key={source.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-all hover:border-red-300"
              >
                <div className="p-5">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-start gap-2.5 flex-1">
                      <div className={`p-2 rounded-lg ${getSourceColor(source.type)}`}>
                        {getSourceIcon(source.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-base font-semibold text-gray-900 mb-0.5">
                          {source.name || source.type?.toUpperCase() || 'UNKNOWN'}
                        </h3>
                        <Link
                          href={`/knowledge-bases/${source.knowledge_base_id}`}
                          className="text-xs text-red-600 hover:text-red-700 truncate block"
                        >
                          {source.knowledge_base_name || `KB #${source.knowledge_base_id}`}
                        </Link>
                      </div>
                    </div>
                  </div>

                  {/* Status Badge */}
                  <div className="mb-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(source.status)}`}>
                      {getStatusIcon(source.status)}
                      {source.status}
                    </span>
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-3 mb-3 py-3 border-t border-b border-gray-100">
                    <div>
                      <div className="flex items-center gap-1.5 mb-1">
                        <FileText className="w-3.5 h-3.5 text-gray-400" />
                        <p className="text-xs text-gray-500">Documents</p>
                      </div>
                      <p className="text-lg font-bold text-gray-900">{source.total_documents}</p>
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5 mb-1">
                        <Clock className="w-3.5 h-3.5 text-gray-400" />
                        <p className="text-xs text-gray-500">Last Sync</p>
                      </div>
                      <p className="text-xs font-medium text-gray-900">
                        {source.last_sync_at
                          ? new Date(source.last_sync_at).toLocaleDateString()
                          : 'Never'}
                      </p>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-2">
                    <Link
                      href={`/data-sources/${source.id}`}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      View
                    </Link>
                    <button
                      onClick={() => openDeleteModal(source)}
                      className="inline-flex items-center justify-center px-3 py-2 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteModal.show && deleteModal.source && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Delete Data Source</h3>
            </div>
            
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete the <span className="font-semibold">{deleteModal.source.name}</span> data source? 
              This action cannot be undone and will permanently delete all associated documents.
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={closeDeleteModal}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
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
