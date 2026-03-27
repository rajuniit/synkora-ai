'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  Activity,
  Plus,
  Edit,
  Trash2,
  Play,
  Eye,
  Search,
  Clock,
  CheckCircle,
  AlertCircle,
  Zap,
  Server,
  BarChart3,
  Settings,
} from 'lucide-react'
import {
  getLoadTests,
  deleteLoadTest,
  type LoadTest,
} from '@/lib/api/load-testing'

export default function LoadTestingPage() {
  const [loadTests, setLoadTests] = useState<LoadTest[]>([])
  const [filteredTests, setFilteredTests] = useState<LoadTest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [deleteModal, setDeleteModal] = useState<{ show: boolean; test: LoadTest | null }>({
    show: false,
    test: null,
  })
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchLoadTests()
  }, [])

  useEffect(() => {
    filterTests()
  }, [searchQuery, statusFilter, loadTests])

  const fetchLoadTests = async () => {
    try {
      setLoading(true)
      const response = await getLoadTests()
      setLoadTests(response.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tests')
      toast.error('Failed to load load tests')
    } finally {
      setLoading(false)
    }
  }

  const filterTests = () => {
    let filtered = loadTests

    if (searchQuery) {
      filtered = filtered.filter(test =>
        test.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        test.description?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    if (statusFilter) {
      filtered = filtered.filter(test => test.status === statusFilter)
    }

    setFilteredTests(filtered)
  }

  const openDeleteModal = (test: LoadTest) => {
    setDeleteModal({ show: true, test })
  }

  const closeDeleteModal = () => {
    setDeleteModal({ show: false, test: null })
  }

  const confirmDelete = async () => {
    if (!deleteModal.test) return

    setDeleting(true)
    try {
      await deleteLoadTest(deleteModal.test.id)
      toast.success(`"${deleteModal.test.name}" has been deleted`)
      closeDeleteModal()
      fetchLoadTests()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete')
    } finally {
      setDeleting(false)
    }
  }

  const getStatusBadge = (status: string) => {
    const styles = {
      draft: 'bg-gray-100 text-gray-700',
      ready: 'bg-blue-100 text-blue-700',
      running: 'bg-green-100 text-green-700',
      paused: 'bg-yellow-100 text-yellow-700',
    }
    return styles[status as keyof typeof styles] || styles.draft
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-primary-50 via-white to-primary-50/30">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your load tests...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-50/30 p-4 md:p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Load Testing</h1>
              <p className="text-gray-600 mt-1">
                Test your AI agents at scale with K6-powered load tests
              </p>
            </div>
            <div className="flex gap-3 flex-wrap">
              <Link
                href="/load-testing/proxy"
                className="inline-flex items-center gap-2 px-4 py-2.5 border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 rounded-xl transition-all shadow-sm font-medium"
              >
                <Server className="w-5 h-5" />
                Proxy Config
              </Link>
              <Link
                href="/load-testing/create"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white rounded-xl transition-all shadow-sm hover:shadow-md font-medium"
              >
                <Plus className="w-5 h-5" />
                Create Test
              </Link>
            </div>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-primary-100 rounded-xl">
                  <Activity className="w-5 h-5 text-primary-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Total Tests</p>
                  <p className="text-2xl font-bold text-gray-900">{loadTests.length}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-green-100 rounded-xl">
                  <Zap className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Running</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {loadTests.filter(t => t.status === 'running').length}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-blue-100 rounded-xl">
                  <CheckCircle className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Ready</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {loadTests.filter(t => t.status === 'ready').length}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-gray-100 rounded-xl">
                  <Edit className="w-5 h-5 text-gray-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Draft</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {loadTests.filter(t => t.status === 'draft').length}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Search and Filter */}
          {loadTests.length > 0 && (
            <div className="flex gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search load tests..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent shadow-sm"
                />
              </div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent shadow-sm"
              >
                <option value="">All Status</option>
                <option value="draft">Draft</option>
                <option value="ready">Ready</option>
                <option value="running">Running</option>
              </select>
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Load Tests Grid */}
        {filteredTests.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
            <div className="w-32 h-32 mx-auto mb-6 relative">
              <div className="absolute inset-0 bg-gradient-to-br from-primary-100 to-primary-50 rounded-2xl transform rotate-6"></div>
              <div className="absolute inset-0 bg-white rounded-2xl shadow-sm border border-gray-100 flex items-center justify-center">
                <BarChart3 className="w-12 h-12 text-primary-500" />
              </div>
            </div>

            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              {loadTests.length === 0 ? 'Create your first load test' : 'No results found'}
            </h3>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              {loadTests.length === 0
                ? 'Load tests help you understand how your AI agents perform under heavy traffic.'
                : 'Try adjusting your search or filters.'}
            </p>
            {loadTests.length === 0 && (
              <Link
                href="/load-testing/create"
                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white rounded-xl transition-all shadow-sm hover:shadow-md font-medium"
              >
                <Plus className="w-5 h-5" />
                Create Load Test
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredTests.map((test) => (
              <div
                key={test.id}
                className="bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all hover:border-primary-200 group"
              >
                <div className="p-5">
                  {/* Header */}
                  <div className="flex items-start gap-3 mb-4">
                    <div className="p-2.5 bg-primary-100 rounded-xl group-hover:bg-primary-200 transition-colors">
                      <Activity className="w-5 h-5 text-primary-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-gray-900 truncate">
                        {test.name}
                      </h3>
                      <p className="text-sm text-gray-500 line-clamp-2 mt-1">
                        {test.description || 'No description'}
                      </p>
                    </div>
                  </div>

                  {/* Status Badge */}
                  <div className="mb-4">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${getStatusBadge(test.status)}`}>
                      <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                      {test.status.charAt(0).toUpperCase() + test.status.slice(1)}
                    </span>
                  </div>

                  {/* Info */}
                  <div className="flex items-center gap-4 mb-4 py-3 border-t border-gray-100">
                    <div className="flex items-center gap-2">
                      <Server className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-600 truncate max-w-[150px]">
                        {test.target_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-500">{formatDate(test.updated_at)}</span>
                    </div>
                  </div>

                  {/* Last Run */}
                  {test.last_run && (
                    <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                      <div className="text-xs text-gray-500 mb-1">Last Run</div>
                      <div className="flex items-center justify-between">
                        <span className={`text-sm font-medium ${
                          test.last_run.status === 'completed' ? 'text-green-600' :
                          test.last_run.status === 'failed' ? 'text-red-600' :
                          'text-gray-600'
                        }`}>
                          {test.last_run.status.charAt(0).toUpperCase() + test.last_run.status.slice(1)}
                        </span>
                        {test.last_run.started_at && (
                          <span className="text-xs text-gray-500">
                            {formatDate(test.last_run.started_at)}
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Link
                      href={`/load-testing/${test.id}`}
                      className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                      View
                    </Link>
                    {test.status === 'ready' && (
                      <Link
                        href={`/load-testing/${test.id}/runs`}
                        className="inline-flex items-center justify-center px-3 py-2.5 text-sm font-medium text-green-700 bg-green-100 rounded-lg hover:bg-green-200 transition-colors"
                      >
                        <Play className="w-4 h-4" />
                      </Link>
                    )}
                    <button
                      onClick={() => openDeleteModal(test)}
                      disabled={test.status === 'running'}
                      className="inline-flex items-center justify-center px-3 py-2.5 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete Modal */}
      {deleteModal.show && deleteModal.test && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 bg-red-100 rounded-xl">
                <Trash2 className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Delete Load Test</h3>
            </div>

            <p className="text-gray-600 mb-6">
              Are you sure you want to delete <span className="font-semibold text-gray-900">"{deleteModal.test.name}"</span>?
              All test runs and results will be permanently removed.
            </p>

            <div className="flex gap-3 justify-end">
              <button
                onClick={closeDeleteModal}
                disabled={deleting}
                className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                disabled={deleting}
                className="px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
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
