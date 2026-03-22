'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { apiClient } from '@/lib/api/client'
import {
  Database,
  Plus,
  Trash2,
  Eye,
  Edit,
  CheckCircle,
  XCircle,
  Clock,
  Search,
  Filter,
  AlertCircle,
  Server
} from 'lucide-react'

interface DatabaseConnection {
  id: number
  name: string
  description: string | null
  type: string
  host: string
  port: number
  database: string | null
  username: string | null
  status: string
  last_tested_at: string | null
  last_test_status: string | null
  last_error: string | null
  created_at: string
  updated_at: string
}

export default function DatabaseConnectionsPage() {
  const [connections, setConnections] = useState<DatabaseConnection[]>([])
  const [filteredConnections, setFilteredConnections] = useState<DatabaseConnection[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [deleteModal, setDeleteModal] = useState<{ show: boolean; connection: DatabaseConnection | null }>({
    show: false,
    connection: null,
  })
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchConnections()
  }, [])

  useEffect(() => {
    filterConnections()
  }, [searchQuery, filterType, filterStatus, connections])

  const fetchConnections = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getDatabaseConnections()
      setConnections(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      toast.error('Failed to load database connections')
    } finally {
      setLoading(false)
    }
  }

  const filterConnections = () => {
    let filtered = connections

    if (searchQuery) {
      filtered = filtered.filter(conn =>
        conn.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        conn.type?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        conn.host?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    if (filterType !== 'all') {
      filtered = filtered.filter(conn => conn.type === filterType)
    }

    if (filterStatus !== 'all') {
      filtered = filtered.filter(conn => conn.status === filterStatus)
    }

    setFilteredConnections(filtered)
  }

  const confirmDelete = async () => {
    if (!deleteModal.connection) return

    setDeleting(true)
    try {
      await apiClient.deleteDatabaseConnection(deleteModal.connection.id.toString())
      toast.success('Database connection deleted successfully')
      setDeleteModal({ show: false, connection: null })
      fetchConnections()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete connection')
    } finally {
      setDeleting(false)
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type?.toUpperCase()) {
      case 'POSTGRESQL': return <Database className="w-4 h-4" />
      case 'ELASTICSEARCH': return <Server className="w-4 h-4" />
      default: return <Database className="w-4 h-4" />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type?.toUpperCase()) {
      case 'POSTGRESQL': return 'bg-blue-100 text-blue-800'
      case 'ELASTICSEARCH': return 'bg-purple-100 text-purple-800'
      case 'MYSQL': return 'bg-orange-100 text-orange-800'
      case 'MONGODB': return 'bg-green-100 text-green-800'
      default: return 'bg-amber-100 text-amber-800'
    }
  }

  const getStatusColor = (status: string) => {
    if (status === 'active') return 'bg-green-100 text-green-800'
    if (status === 'inactive') return 'bg-gray-100 text-gray-800'
    if (status === 'error') return 'bg-red-100 text-red-800'
    return 'bg-yellow-100 text-yellow-800' // pending
  }

  const getStatusIcon = (status: string) => {
    if (status === 'active') return <CheckCircle className="w-3 h-3" />
    if (status === 'inactive') return <XCircle className="w-3 h-3" />
    if (status === 'error') return <AlertCircle className="w-3 h-3" />
    return <Clock className="w-3 h-3" /> // pending
  }

  const getStatusText = (status: string) => {
    if (status === 'active') return 'Active'
    if (status === 'inactive') return 'Inactive'
    if (status === 'error') return 'Error'
    return 'Pending'
  }

  const uniqueTypes = Array.from(new Set(connections.map(c => c.type)))

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 via-red-50/30 to-red-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header - More Compact */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Database Connections</h1>
              <p className="text-gray-600 mt-1 text-sm">
                Manage database connections for data analysis agents
              </p>
            </div>
            <Link
              href="/database-connections/create"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-lg transition-all shadow-sm hover:shadow-md text-sm font-medium"
            >
              <Plus className="w-4 h-4" />
              Add Connection
            </Link>
          </div>

          {/* Stats Bar - More Compact */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-5">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-red-100 rounded-lg">
                  <Database className="w-4 h-4 text-red-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Total</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{connections.length}</p>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-emerald-100 rounded-lg">
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Active</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {connections.filter(c => c.status === 'active').length}
              </p>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-gray-100 rounded-lg">
                  <XCircle className="w-4 h-4 text-gray-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Inactive</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {connections.filter(c => c.status === 'inactive').length}
              </p>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-yellow-100 rounded-lg">
                  <Clock className="w-4 h-4 text-yellow-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Pending</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {connections.filter(c => c.status === 'pending').length}
              </p>
            </div>
          </div>

          {/* Search and Filter Bar - More Compact */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search connections..."
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
                  <option value="all">All Types</option>
                  {uniqueTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                >
                  <option value="all">All Status</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="pending">Pending</option>
                  <option value="error">Error</option>
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

        {/* Connections Grid - More Compact */}
        {filteredConnections.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border-2 border-dashed border-gray-300 p-10 text-center">
            <Database className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-gray-900 mb-2">
              {connections.length === 0 ? 'No database connections yet' : 'No results found'}
            </h3>
            <p className="text-sm text-gray-600 mb-5">
              {connections.length === 0
                ? 'Add your first database connection to enable data analysis.'
                : 'Try adjusting your search or filter criteria.'}
            </p>
            {connections.length === 0 && (
              <Link
                href="/database-connections/create"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-lg transition-all shadow-sm hover:shadow-md text-sm font-medium"
              >
                <Plus className="w-4 h-4" />
                Add Connection
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredConnections.map((connection) => (
              <div
                key={connection.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-all hover:border-red-300"
              >
                <div className="p-4">
                  {/* Header - More Compact */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-start gap-2.5 flex-1">
                      <div className={`p-1.5 rounded-lg ${getTypeColor(connection.type)}`}>
                        {getTypeIcon(connection.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-base font-semibold text-gray-900 mb-0.5 truncate">
                          {connection.name}
                        </h3>
                        <p className="text-xs text-gray-500 truncate">
                          {connection.host}:{connection.port}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Status Badge - More Compact */}
                  <div className="mb-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(connection.status)}`}>
                      {getStatusIcon(connection.status)}
                      {getStatusText(connection.status)}
                    </span>
                  </div>

                  {/* Description - More Compact */}
                  {connection.description && (
                    <p className="text-xs text-gray-600 mb-3 line-clamp-2">
                      {connection.description}
                    </p>
                  )}

                  {/* Database Info - More Compact */}
                  {connection.database && (
                    <div className="mb-3 p-2.5 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500 mb-0.5">Database</p>
                      <p className="text-xs font-medium text-gray-900 truncate">{connection.database}</p>
                    </div>
                  )}

                  {/* Action Buttons - More Compact */}
                  <div className="flex gap-1.5">
                    <Link
                      href={`/database-connections/${connection.id}`}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-red-700 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      View
                    </Link>
                    <Link
                      href={`/database-connections/${connection.id}/edit`}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                      <Edit className="w-3.5 h-3.5" />
                      Edit
                    </Link>
                    <button
                      onClick={() => setDeleteModal({ show: true, connection })}
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

      {/* Delete Confirmation Modal - Modern Design */}
      {deleteModal.show && deleteModal.connection && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Delete Connection</h3>
            </div>
            
            <p className="text-sm text-gray-600 mb-6">
              Are you sure you want to delete <span className="font-semibold">"{deleteModal.connection.name}"</span>? 
              This action cannot be undone and will permanently remove this database connection.
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteModal({ show: false, connection: null })}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm hover:shadow-md"
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
