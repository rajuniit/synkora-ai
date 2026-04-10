'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  Clock,
  ArrowLeft,
  Trash2,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  AlertCircle,
  Calendar,
  Database,
  TrendingUp,
  Loader2,
  Activity
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'

interface ScheduledTask {
  id: string
  name: string
  description: string | null
  task_type: string
  schedule_type: string
  cron_expression: string | null
  interval_seconds: number | null
  config: any
  is_active: boolean
  last_run_at: string | null
  last_run_status: string | null
  next_run_at: string | null
  created_at: string
  updated_at: string
}

interface TaskExecution {
  id: string
  status: string
  started_at: string
  completed_at: string | null
  result: any | null
  error_message: string | null
  execution_time_seconds: number | null
}

export default function ScheduledTaskDetailsPage() {
  const params = useParams()
  const router = useRouter()
  const [task, setTask] = useState<ScheduledTask | null>(null)
  const [executions, setExecutions] = useState<TaskExecution[]>([])
  const [loading, setLoading] = useState(true)
  const [executionsLoading, setExecutionsLoading] = useState(true)
  const [deleteModal, setDeleteModal] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchTask()
    fetchExecutions()
  }, [params.id])

  const fetchTask = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getScheduledTask(params.id as string)
      setTask(data)
    } catch {
      toast.error('Failed to load task details')
      router.push('/scheduled-tasks')
    } finally {
      setLoading(false)
    }
  }

  const fetchExecutions = async () => {
    try {
      setExecutionsLoading(true)
      const data = await apiClient.getTaskExecutions(params.id as string, 0, 10)
      setExecutions(Array.isArray(data) ? data : [])
    } catch (error) {
      console.error('Failed to load executions:', error)
      setExecutions([])
    } finally {
      setExecutionsLoading(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await apiClient.deleteScheduledTask(params.id as string)
      toast.success('Task deleted successfully')
      router.push('/scheduled-tasks')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete task')
    } finally {
      setDeleting(false)
      setDeleteModal(false)
    }
  }

  const toggleTask = async () => {
    if (!task) return
    
    try {
      await apiClient.toggleScheduledTask(params.id as string)
      toast.success(`Task ${task.is_active ? 'paused' : 'activated'} successfully`)
      fetchTask()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to toggle task')
    }
  }

  const executeTask = async () => {
    try {
      await apiClient.executeScheduledTask(params.id as string)
      toast.success('Task execution started')
      setTimeout(() => {
        fetchTask()
        fetchExecutions()
      }, 2000)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to execute task')
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type?.toUpperCase()) {
      case 'DATABASE_QUERY': return <Database className="w-6 h-6" />
      case 'DATA_ANALYSIS': return <TrendingUp className="w-6 h-6" />
      default: return <Clock className="w-6 h-6" />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type?.toUpperCase()) {
      case 'DATABASE_QUERY': return 'bg-blue-100 text-blue-800'
      case 'DATA_ANALYSIS': return 'bg-purple-100 text-purple-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'success': return 'bg-green-100 text-green-800'
      case 'failed': return 'bg-red-100 text-red-800'
      case 'running': return 'bg-blue-100 text-blue-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const formatSchedule = (task: ScheduledTask) => {
    if (task.schedule_type === 'cron') {
      return task.cron_expression || 'N/A'
    } else if (task.schedule_type === 'interval') {
      const seconds = task.interval_seconds || 0
      if (seconds < 60) return `Every ${seconds} seconds`
      if (seconds < 3600) return `Every ${Math.floor(seconds / 60)} minutes`
      if (seconds < 86400) return `Every ${Math.floor(seconds / 3600)} hours`
      return `Every ${Math.floor(seconds / 86400)} days`
    }
    return 'N/A'
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleString()
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A'
    if (seconds < 60) return `${seconds.toFixed(2)}s`
    return `${(seconds / 60).toFixed(2)}m`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600"></div>
      </div>
    )
  }

  if (!task) {
    return null
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <Link
            href="/scheduled-tasks"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Tasks
          </Link>
          
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className={`p-3 rounded-lg ${getTypeColor(task.task_type)}`}>
                {getTypeIcon(task.task_type)}
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">{task.name}</h1>
                <p className="text-gray-600 mt-1">{task.task_type}</p>
              </div>
            </div>

            <div className="flex gap-3 flex-wrap">
              <button
                onClick={toggleTask}
                className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  task.is_active
                    ? 'text-yellow-600 bg-yellow-50 hover:bg-yellow-100'
                    : 'text-green-600 bg-green-50 hover:bg-green-100'
                }`}
              >
                {task.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                {task.is_active ? 'Pause' : 'Activate'}
              </button>
              <button
                onClick={executeTask}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-teal-600 bg-teal-50 rounded-lg hover:bg-teal-100 transition-colors"
              >
                <Play className="w-4 h-4" />
                Run Now
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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Status Card */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-sm font-medium text-gray-500 mb-4">Status</h2>
            <div className="space-y-4">
              <div>
                <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                  task.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {task.is_active ? <CheckCircle className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                  {task.is_active ? 'Active' : 'Paused'}
                </span>
              </div>
              
              {task.last_run_at && (
                <div className="text-sm text-gray-600">
                  <p className="font-medium mb-1">Last Run</p>
                  <p>{formatDate(task.last_run_at)}</p>
                  {task.last_run_status && (
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium mt-1 ${getStatusColor(task.last_run_status)}`}>
                      {task.last_run_status === 'success' ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                      {task.last_run_status}
                    </span>
                  )}
                </div>
              )}
              
              {task.next_run_at && (
                <div className="text-sm text-gray-600">
                  <p className="font-medium mb-1">Next Run</p>
                  <p>{formatDate(task.next_run_at)}</p>
                </div>
              )}
            </div>
          </div>

          {/* Task Details */}
          <div className="lg:col-span-2 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Task Details</h2>
            
            {task.description && (
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-700">{task.description}</p>
              </div>
            )}
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">Schedule Type</label>
                <p className="text-gray-900 capitalize">{task.schedule_type}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">Schedule</label>
                <div className="flex items-center gap-2 text-gray-900">
                  <Calendar className="w-4 h-4 text-gray-400" />
                  {formatSchedule(task)}
                </div>
              </div>
              
              {task.config && Object.keys(task.config).length > 0 && (
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-500 mb-2">Configuration</label>
                  <pre className="bg-gray-50 rounded-lg p-4 overflow-x-auto text-sm text-gray-900">
                    {JSON.stringify(task.config, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Metadata */}
        <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Metadata</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">Created</label>
              <p className="text-gray-900">{formatDate(task.created_at)}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">Last Updated</label>
              <p className="text-gray-900">{formatDate(task.updated_at)}</p>
            </div>
          </div>
        </div>

        {/* Execution History */}
        <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">Execution History</h2>
            </div>
          </div>

          <div className="p-6">
            {executionsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-teal-600 animate-spin" />
              </div>
            ) : executions.length === 0 ? (
              <div className="text-center py-12">
                <Activity className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600">No execution history yet</p>
              </div>
            ) : (
              <div className="space-y-4">
                {executions.map((execution) => (
                  <div
                    key={execution.id}
                    className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor(execution.status)}`}>
                          {execution.status === 'success' ? <CheckCircle className="w-3 h-3" /> : execution.status === 'running' ? <Loader2 className="w-3 h-3 animate-spin" /> : <XCircle className="w-3 h-3" />}
                          {execution.status}
                        </span>
                        {execution.execution_time_seconds !== null && (
                          <span className="text-sm text-gray-600">
                            Duration: {formatDuration(execution.execution_time_seconds)}
                          </span>
                        )}
                      </div>
                      <span className="text-sm text-gray-500">
                        {formatDate(execution.started_at)}
                      </span>
                    </div>
                    
                    {execution.error_message && (
                      <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-sm font-medium text-red-900 mb-1">Error</p>
                        <p className="text-sm text-red-700">{execution.error_message}</p>
                      </div>
                    )}
                    
                    {execution.result && (
                      <div className="mt-2">
                        <p className="text-sm font-medium text-gray-700 mb-1">Result</p>
                        <pre className="bg-gray-50 rounded p-2 text-xs text-gray-900 overflow-x-auto">
                          {JSON.stringify(execution.result, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
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
              <h3 className="text-lg font-semibold text-gray-900">Delete Task</h3>
            </div>
            
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete <span className="font-semibold">{task.name}</span>? 
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
