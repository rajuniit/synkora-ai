'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  Clock,
  Plus,
  Trash2,
  Eye,
  Edit,
  CheckCircle,
  XCircle,
  Play,
  Pause,
  Search,
  Filter,
  AlertCircle,
  Calendar,
  Database,
  TrendingUp
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'

interface ScheduledTask {
  id: number
  name: string
  description: string | null
  task_type: string
  schedule_type: string
  cron_expression: string | null
  interval_seconds: number | null
  database_connection_id: number | null
  query: string | null
  chart_config: any | null
  notification_config: any | null
  is_active: boolean
  last_run_at: string | null
  last_run_status: string | null
  next_run_at: string | null
  created_at: string
  updated_at: string
}

export default function ScheduledTasksPage() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [filteredTasks, setFilteredTasks] = useState<ScheduledTask[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [deleteModal, setDeleteModal] = useState<{ show: boolean; task: ScheduledTask | null }>({
    show: false,
    task: null,
  })
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchTasks()
  }, [])

  useEffect(() => {
    filterTasks()
  }, [searchQuery, filterType, filterStatus, tasks])

  const fetchTasks = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getScheduledTasks()
      setTasks(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      toast.error('Failed to load scheduled tasks')
    } finally {
      setLoading(false)
    }
  }

  const filterTasks = () => {
    let filtered = tasks

    if (searchQuery) {
      filtered = filtered.filter(task =>
        task.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.task_type?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.description?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    if (filterType !== 'all') {
      filtered = filtered.filter(task => task.task_type === filterType)
    }

    if (filterStatus !== 'all') {
      if (filterStatus === 'active') {
        filtered = filtered.filter(task => task.is_active)
      } else if (filterStatus === 'inactive') {
        filtered = filtered.filter(task => !task.is_active)
      }
    }

    setFilteredTasks(filtered)
  }

  const confirmDelete = async () => {
    if (!deleteModal.task) return

    setDeleting(true)
    try {
      await apiClient.deleteScheduledTask(deleteModal.task.id.toString())
      toast.success('Scheduled task deleted successfully')
      setDeleteModal({ show: false, task: null })
      fetchTasks()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete task')
    } finally {
      setDeleting(false)
    }
  }

  const toggleTask = async (task: ScheduledTask) => {
    try {
      await apiClient.toggleScheduledTask(task.id.toString())
      toast.success(`Task ${task.is_active ? 'paused' : 'activated'} successfully`)
      fetchTasks()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to toggle task')
    }
  }

  const executeTask = async (task: ScheduledTask) => {
    try {
      await apiClient.executeScheduledTask(task.id.toString())
      toast.success('Task execution started')
      fetchTasks()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to execute task')
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type?.toUpperCase()) {
      case 'DATABASE_QUERY': return <Database className="w-4 h-4" />
      case 'DATA_ANALYSIS': return <TrendingUp className="w-4 h-4" />
      default: return <Clock className="w-4 h-4" />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type?.toUpperCase()) {
      case 'DATABASE_QUERY': return 'bg-blue-100 text-blue-800'
      case 'DATA_ANALYSIS': return 'bg-purple-100 text-purple-800'
      default: return 'bg-amber-100 text-amber-800'
    }
  }

  const getStatusColor = (isActive: boolean, lastRunStatus: string | null) => {
    if (!isActive) return 'bg-gray-100 text-gray-800'
    if (lastRunStatus === 'success') return 'bg-green-100 text-green-800'
    if (lastRunStatus === 'failed') return 'bg-red-100 text-red-800'
    return 'bg-yellow-100 text-yellow-800'
  }

  const getStatusIcon = (isActive: boolean, lastRunStatus: string | null) => {
    if (!isActive) return <Pause className="w-3 h-3" />
    if (lastRunStatus === 'success') return <CheckCircle className="w-3 h-3" />
    if (lastRunStatus === 'failed') return <XCircle className="w-3 h-3" />
    return <Clock className="w-3 h-3" />
  }

  const getStatusText = (isActive: boolean, lastRunStatus: string | null) => {
    if (!isActive) return 'Paused'
    if (lastRunStatus === 'success') return 'Success'
    if (lastRunStatus === 'failed') return 'Failed'
    return 'Pending'
  }

  const formatSchedule = (task: ScheduledTask) => {
    if (task.schedule_type === 'cron') {
      return task.cron_expression || 'N/A'
    } else if (task.schedule_type === 'interval') {
      const seconds = task.interval_seconds || 0
      if (seconds < 60) return `Every ${seconds}s`
      if (seconds < 3600) return `Every ${Math.floor(seconds / 60)}m`
      if (seconds < 86400) return `Every ${Math.floor(seconds / 3600)}h`
      return `Every ${Math.floor(seconds / 86400)}d`
    }
    return 'N/A'
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleString()
  }

  const uniqueTypes = Array.from(new Set(tasks.map(t => t.task_type)))

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
              <h1 className="text-2xl font-bold text-gray-900">Scheduled Tasks</h1>
              <p className="text-gray-600 mt-1 text-sm">
                Schedule and automate recurring tasks
              </p>
            </div>
            <Link
              href="/scheduled-tasks/create"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-lg transition-all shadow-sm hover:shadow-md text-sm font-medium"
            >
              <Plus className="w-4 h-4" />
              Create Task
            </Link>
          </div>

          {/* Stats Bar - More Compact */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-5">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-red-100 rounded-lg">
                  <Clock className="w-4 h-4 text-red-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Total</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{tasks.length}</p>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-emerald-100 rounded-lg">
                  <Play className="w-4 h-4 text-emerald-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Active</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {tasks.filter(t => t.is_active).length}
              </p>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-green-100 rounded-lg">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Successful</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {tasks.filter(t => t.last_run_status === 'success').length}
              </p>
            </div>
            
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-red-100 rounded-lg">
                  <XCircle className="w-4 h-4 text-red-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Failed</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">
                {tasks.filter(t => t.last_run_status === 'failed').length}
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
                  placeholder="Search tasks..."
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

        {/* Tasks Grid - More Compact */}
        {filteredTasks.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border-2 border-dashed border-gray-300 p-10 text-center">
            <Clock className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-gray-900 mb-2">
              {tasks.length === 0 ? 'No scheduled tasks yet' : 'No results found'}
            </h3>
            <p className="text-sm text-gray-600 mb-5">
              {tasks.length === 0
                ? 'Create your first scheduled task to automate data analysis.'
                : 'Try adjusting your search or filter criteria.'}
            </p>
            {tasks.length === 0 && (
              <Link
                href="/scheduled-tasks/create"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-lg transition-all shadow-sm hover:shadow-md text-sm font-medium"
              >
                <Plus className="w-4 h-4" />
                Create Task
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredTasks.map((task) => (
              <div
                key={task.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-all hover:border-red-300"
              >
                <div className="p-4">
                  {/* Header - More Compact */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-start gap-2.5 flex-1 min-w-0">
                      <div className={`p-1.5 rounded-lg flex-shrink-0 ${getTypeColor(task.task_type)}`}>
                        {getTypeIcon(task.task_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-base font-semibold text-gray-900 mb-0.5 break-words line-clamp-2" title={task.name}>
                          {task.name}
                        </h3>
                        <p className="text-xs text-gray-500 flex items-center gap-1 flex-wrap">
                          <Calendar className="w-3 h-3 flex-shrink-0" />
                          <span className="truncate">{formatSchedule(task)}</span>
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Status Badge - More Compact */}
                  <div className="mb-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(task.is_active, task.last_run_status)}`}>
                      {getStatusIcon(task.is_active, task.last_run_status)}
                      {getStatusText(task.is_active, task.last_run_status)}
                    </span>
                  </div>

                  {/* Description - More Compact */}
                  {task.description && (
                    <p className="text-xs text-gray-600 mb-3 line-clamp-2">
                      {task.description}
                    </p>
                  )}

                  {/* Run Info - More Compact */}
                  <div className="text-xs text-gray-500 mb-3 space-y-0.5 p-2.5 bg-gray-50 rounded-lg">
                    <p>Last run: {formatDate(task.last_run_at)}</p>
                    {task.next_run_at && (
                      <p>Next run: {formatDate(task.next_run_at)}</p>
                    )}
                  </div>

                  {/* Action Buttons - More Compact */}
                  <div className="flex gap-1.5 flex-wrap">
                    <button
                      onClick={() => toggleTask(task)}
                      className={`inline-flex items-center justify-center px-2.5 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                        task.is_active
                          ? 'text-yellow-600 bg-yellow-50 hover:bg-yellow-100'
                          : 'text-green-600 bg-green-50 hover:bg-green-100'
                      }`}
                      title={task.is_active ? 'Pause' : 'Activate'}
                    >
                      {task.is_active ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                    </button>
                    <button
                      onClick={() => executeTask(task)}
                      className="inline-flex items-center justify-center px-2.5 py-1.5 text-xs font-medium text-red-700 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                      title="Run now"
                    >
                      <Play className="w-3.5 h-3.5" />
                    </button>
                    <Link
                      href={`/scheduled-tasks/${task.id}`}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      View
                    </Link>
                    <Link
                      href={`/scheduled-tasks/${task.id}/edit`}
                      className="inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                      <Edit className="w-3.5 h-3.5" />
                    </Link>
                    <button
                      onClick={() => setDeleteModal({ show: true, task })}
                      className="inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
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
      {deleteModal.show && deleteModal.task && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Delete Task</h3>
            </div>
            
            <p className="text-sm text-gray-600 mb-6">
              Are you sure you want to delete <span className="font-semibold">"{deleteModal.task.name}"</span>? 
              This action cannot be undone and will permanently remove this scheduled task.
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteModal({ show: false, task: null })}
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
