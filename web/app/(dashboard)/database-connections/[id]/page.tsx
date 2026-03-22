'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  Database,
  ArrowLeft,
  Edit,
  Trash2,
  TestTube,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Loader2,
  Copy
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'

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

export default function DatabaseConnectionDetailsPage() {
  const params = useParams()
  const router = useRouter()
  const [connection, setConnection] = useState<DatabaseConnection | null>(null)
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)
  const [deleteModal, setDeleteModal] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchConnection()
  }, [params.id])

  const fetchConnection = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getDatabaseConnection(params.id as string)
      setConnection(data)
    } catch {
      toast.error('Failed to load connection details')
      router.push('/database-connections')
    } finally {
      setLoading(false)
    }
  }

  const testConnection = async () => {
    setTesting(true)
    try {
      const data = await apiClient.testDatabaseConnection(params.id as string)
      if (data.success) {
        toast.success('Connection test successful')
        fetchConnection() // Refresh to get updated test status
      } else {
        toast.error(data.message || 'Connection test failed')
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to test connection')
    } finally {
      setTesting(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await apiClient.deleteDatabaseConnection(params.id as string)
      toast.success('Connection deleted successfully')
      router.push('/database-connections')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete connection')
    } finally {
      setDeleting(false)
      setDeleteModal(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard')
  }

  const getStatusColor = (status: string) => {
    if (status === 'active') return 'bg-green-100 text-green-800'
    if (status === 'inactive') return 'bg-gray-100 text-gray-800'
    if (status === 'error') return 'bg-red-100 text-red-800'
    return 'bg-yellow-100 text-yellow-800' // pending
  }

  const getStatusIcon = (status: string) => {
    if (status === 'active') return <CheckCircle className="w-4 h-4" />
    if (status === 'inactive') return <XCircle className="w-4 h-4" />
    if (status === 'error') return <AlertCircle className="w-4 h-4" />
    return <Clock className="w-4 h-4" /> // pending
  }

  const getStatusText = (status: string) => {
    if (status === 'active') return 'Active'
    if (status === 'inactive') return 'Inactive'
    if (status === 'error') return 'Error'
    return 'Pending'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600"></div>
      </div>
    )
  }

  if (!connection) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <Link
            href="/database-connections"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Connections
          </Link>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-teal-100 rounded-lg">
                <Database className="w-6 h-6 text-teal-600" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">{connection.name}</h1>
                <p className="text-gray-600 mt-1">{connection.type}</p>
              </div>
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={testConnection}
                disabled={testing}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-teal-600 bg-teal-50 rounded-lg hover:bg-teal-100 transition-colors disabled:opacity-50"
              >
                {testing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Testing...
                  </>
                ) : (
                  <>
                    <TestTube className="w-4 h-4" />
                    Test Connection
                  </>
                )}
              </button>
              <Link
                href={`/database-connections/${connection.id}/edit`}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <Edit className="w-4 h-4" />
                Edit
              </Link>
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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Status Card */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-sm font-medium text-gray-500 mb-4">Status</h2>
            <div className="space-y-4">
              <div>
                <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${getStatusColor(connection.status)}`}>
                  {getStatusIcon(connection.status)}
                  {getStatusText(connection.status)}
                </span>
              </div>
              
              {connection.last_tested_at && (
                <div className="text-sm text-gray-600">
                  <p className="font-medium mb-1">Last Tested</p>
                  <p>{new Date(connection.last_tested_at).toLocaleString()}</p>
                </div>
              )}
              
              {connection.last_error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm font-medium text-red-900 mb-1">Last Error</p>
                  <p className="text-sm text-red-700">{connection.last_error}</p>
                </div>
              )}
            </div>
          </div>

          {/* Connection Details */}
          <div className="lg:col-span-2 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Connection Details</h2>
            
            {connection.description && (
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-700">{connection.description}</p>
              </div>
            )}
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">Host</label>
                <div className="flex items-center gap-2">
                  <p className="text-gray-900 font-mono">{connection.host}</p>
                  <button
                    onClick={() => copyToClipboard(connection.host)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">Port</label>
                <p className="text-gray-900 font-mono">{connection.port}</p>
              </div>
              
              {connection.database && (
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">Database</label>
                  <p className="text-gray-900 font-mono">{connection.database}</p>
                </div>
              )}
              
              {connection.username && (
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">Username</label>
                  <p className="text-gray-900 font-mono">{connection.username}</p>
                </div>
              )}
              
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-500 mb-1">Connection String</label>
                <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg font-mono text-sm">
                  <p className="flex-1 truncate text-gray-900">
                    {connection.type.toLowerCase()}://{connection.username}@{connection.host}:{connection.port}/{connection.database || ''}
                  </p>
                  <button
                    onClick={() => copyToClipboard(`${connection.type.toLowerCase()}://${connection.username}@${connection.host}:${connection.port}/${connection.database || ''}`)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Metadata */}
        <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Metadata</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">Created</label>
              <p className="text-gray-900">{new Date(connection.created_at).toLocaleString()}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">Last Updated</label>
              <p className="text-gray-900">{new Date(connection.updated_at).toLocaleString()}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Modal */}
      {deleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Delete Connection</h3>
            </div>
            
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete <span className="font-semibold">{connection.name}</span>? 
              This action cannot be undone.
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
                    <Loader2 className="w-4 h-4 animate-spin" />
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
