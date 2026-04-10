'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api/client'
import type { App } from '@/lib/types'

export default function AppsPage() {
  const [apps, setApps] = useState<App[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadApps()
  }, [])

  const loadApps = async () => {
    try {
      const data = await apiClient.getApps()
      setApps(data)
    } catch (error) {
      console.error('Failed to load apps:', error)
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight mb-2">Apps</h1>
        <p className="text-gray-600">Create and manage your AI applications</p>
      </div>

      {/* Create New App Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        <button className="group relative bg-white border-2 border-dashed border-gray-300 rounded-xl p-8 hover:border-emerald-500 hover:bg-emerald-50/50 transition-all duration-200 flex flex-col items-center justify-center min-h-[240px]">
          <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mb-4 group-hover:bg-emerald-200 transition-colors">
            <svg className="w-8 h-8 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">Create New App</h3>
          <p className="text-sm text-gray-500 text-center">Start building your AI application</p>
        </button>

        {/* App Cards */}
        {apps.map((app) => (
          <div
            key={app.id}
            className="group bg-white rounded-xl border border-gray-200 hover:border-emerald-500 hover:shadow-lg transition-all duration-200 overflow-hidden"
          >
            <div className="p-6">
              {/* App Icon */}
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>

              {/* App Info */}
              <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-1">{app.name}</h3>
              <p className="text-sm text-gray-500 mb-4 line-clamp-2 min-h-[40px]">
                {app.description || 'No description provided'}
              </p>

              {/* App Meta */}
              <div className="flex items-center justify-between text-xs text-gray-400 mb-4">
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {new Date(app.created_at).toLocaleDateString()}
                </span>
                <span className="px-2 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
                  {app.mode}
                </span>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                <button className="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg transition-colors">
                  Open
                </button>
                <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                  <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {apps.length === 0 && (
        <div className="text-center py-16">
          <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No apps yet</h3>
          <p className="text-gray-500 mb-6">Create your first AI application to get started</p>
          <button className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg transition-colors">
            Create App
          </button>
        </div>
      )}
    </div>
  )
}
