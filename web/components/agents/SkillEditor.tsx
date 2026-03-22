'use client'

import { useState, useEffect } from 'react'
import { X, Save, Loader2, FileText, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { apiClient } from '@/lib/api/client'

interface SkillEditorProps {
  fileId: string
  filename: string
  onClose: () => void
  onSave?: () => void
}

export default function SkillEditor({ fileId, filename, onClose, onSave }: SkillEditorProps) {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasChanges, setHasChanges] = useState(false)
  const [originalContent, setOriginalContent] = useState('')

  // Load file content
  useEffect(() => {
    const loadContent = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await apiClient.request('GET', `/api/v1/agents/context-files/${fileId}/content`)
        const fileContent = response?.data?.content || response?.content || ''
        setContent(fileContent)
        setOriginalContent(fileContent)
      } catch (err) {
        console.error('Failed to load skill content:', err)
        setError('Failed to load skill content')
      } finally {
        setLoading(false)
      }
    }

    loadContent()
  }, [fileId])

  // Track changes
  useEffect(() => {
    setHasChanges(content !== originalContent)
  }, [content, originalContent])

  // Handle save
  const handleSave = async () => {
    if (!hasChanges) return

    setSaving(true)
    try {
      await apiClient.request('PUT', `/api/v1/agents/context-files/${fileId}/content`, {
        content
      })
      setOriginalContent(content)
      setHasChanges(false)
      toast.success('Skill updated successfully')
      onSave?.()
    } catch (err) {
      console.error('Failed to save skill:', err)
      toast.error('Failed to save skill')
    } finally {
      setSaving(false)
    }
  }

  // Handle close with unsaved changes warning
  const handleClose = () => {
    if (hasChanges) {
      if (confirm('You have unsaved changes. Are you sure you want to close?')) {
        onClose()
      }
    } else {
      onClose()
    }
  }

  // Format filename for display
  const displayName = filename.startsWith('skill-')
    ? filename.replace('skill-', '').replace('.md', '').split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
    : filename

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl h-[85vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-red-50 to-pink-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Edit Skill</h2>
              <p className="text-sm text-gray-600">{displayName}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {hasChanges && (
              <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-full">
                Unsaved changes
              </span>
            )}
            <button
              onClick={handleClose}
              className="p-2 hover:bg-white/80 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-red-500 animate-spin" />
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
                <p className="text-gray-900 font-medium">{error}</p>
                <button
                  onClick={onClose}
                  className="mt-4 px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
                >
                  Close
                </button>
              </div>
            </div>
          ) : (
            <div className="flex-1 p-4 overflow-hidden">
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="w-full h-full p-4 border border-gray-200 rounded-xl font-mono text-sm resize-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="Enter skill content..."
                spellCheck={false}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
          <div className="text-sm text-gray-500">
            {content.length.toLocaleString()} characters
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!hasChanges || saving}
              className="px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 rounded-lg hover:from-red-600 hover:to-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-red-500/30"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Save Changes
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
