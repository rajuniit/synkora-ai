'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  BookOpen,
  Plus,
  Edit,
  Trash2,
  Eye,
  FileText,
  AlertCircle,
  CheckCircle,
  Search,
  Clock,
  FolderOpen,
  ChevronRight,
  Home
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'

interface KnowledgeBase {
  id: number
  name: string
  description: string
  vector_db_provider: string
  embedding_provider: string
  embedding_model: string
  document_count: number
  total_chunks: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export default function KnowledgeBasesPage() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [filteredKBs, setFilteredKBs] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [deleteModal, setDeleteModal] = useState<{ show: boolean; kb: KnowledgeBase | null }>({
    show: false,
    kb: null,
  })
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchKnowledgeBases()
  }, [])

  useEffect(() => {
    filterKnowledgeBases()
  }, [searchQuery, knowledgeBases])

  const fetchKnowledgeBases = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getKnowledgeBases()
      setKnowledgeBases(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      toast.error('Failed to load knowledge bases')
    } finally {
      setLoading(false)
    }
  }

  const filterKnowledgeBases = () => {
    let filtered = knowledgeBases

    // Search filter
    if (searchQuery) {
      filtered = filtered.filter(kb =>
        kb.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        kb.description?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    setFilteredKBs(filtered)
  }

  const openDeleteModal = (kb: KnowledgeBase) => {
    setDeleteModal({ show: true, kb })
  }

  const closeDeleteModal = () => {
    setDeleteModal({ show: false, kb: null })
  }

  const confirmDelete = async () => {
    if (!deleteModal.kb) return

    setDeleting(true)
    try {
      await apiClient.deleteKnowledgeBase(deleteModal.kb.id.toString())
      toast.success(`"${deleteModal.kb.name}" has been deleted`)
      closeDeleteModal()
      fetchKnowledgeBases()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete'
      toast.error(errorMessage)
    } finally {
      setDeleting(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your knowledge bases...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-6xl mx-auto">
        {/* Breadcrumb */}
        <div className="flex items-center gap-1.5 text-sm mb-4">
          <Link href="/" className="text-gray-500 hover:text-red-600 transition-colors flex items-center gap-1">
            <Home className="w-3.5 h-3.5" />
            Home
          </Link>
          <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
          <span className="text-gray-900 font-medium">Knowledge Bases</span>
        </div>

        {/* Header */}
        <div className="mb-6 md:mb-8">
          <div className="flex items-center justify-between gap-3 mb-4 md:mb-6">
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Your Knowledge</h1>
              <p className="text-sm text-gray-600 mt-1 hidden sm:block">
                Store and organize information for your AI agents to use
              </p>
            </div>
            <Link
              href="/knowledge-bases/create"
              className="inline-flex items-center gap-2 px-4 py-2 md:px-5 md:py-2.5 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-xl transition-all shadow-sm hover:shadow-md font-medium text-sm flex-shrink-0"
            >
              <Plus className="w-4 h-4 md:w-5 md:h-5" />
              <span className="hidden sm:inline">Add Knowledge Base</span>
              <span className="sm:hidden">Add</span>
            </Link>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-3 gap-3 md:gap-4 mb-4 md:mb-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-red-100 rounded-xl">
                  <BookOpen className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Knowledge Bases</p>
                  <p className="text-2xl font-bold text-gray-900">{knowledgeBases.length}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-blue-100 rounded-xl">
                  <FileText className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Total Documents</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {knowledgeBases.reduce((sum, kb) => sum + kb.document_count, 0)}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-purple-100 rounded-xl">
                  <CheckCircle className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Active</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {knowledgeBases.filter(kb => kb.is_active).length}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Search Bar - Simplified */}
          {knowledgeBases.length > 0 && (
            <div className="relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search your knowledge bases..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent shadow-sm"
              />
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

        {/* Knowledge Bases Grid */}
        {filteredKBs.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
            {/* Illustration */}
            <div className="w-32 h-32 mx-auto mb-6 relative">
              <div className="absolute inset-0 bg-gradient-to-br from-red-100 to-red-50 rounded-2xl transform rotate-6"></div>
              <div className="absolute inset-0 bg-white rounded-2xl shadow-sm border border-gray-100 flex items-center justify-center">
                <FolderOpen className="w-12 h-12 text-red-500" />
              </div>
            </div>

            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              {knowledgeBases.length === 0 ? 'Create your first knowledge base' : 'No results found'}
            </h3>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              {knowledgeBases.length === 0
                ? 'Knowledge bases help your AI agents answer questions using your own documents, websites, and content.'
                : 'Try adjusting your search to find what you\'re looking for.'}
            </p>
            {knowledgeBases.length === 0 && (
              <Link
                href="/knowledge-bases/create"
                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-xl transition-all shadow-sm hover:shadow-md font-medium"
              >
                <Plus className="w-5 h-5" />
                Add Knowledge Base
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredKBs.map((kb) => (
              <div
                key={kb.id}
                className="bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all hover:border-red-200 group"
              >
                <div className="p-5">
                  {/* Header */}
                  <div className="flex items-start gap-3 mb-4">
                    <div className="p-2.5 bg-red-100 rounded-xl group-hover:bg-red-200 transition-colors">
                      <BookOpen className="w-5 h-5 text-red-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-gray-900 truncate">
                        {kb.name}
                      </h3>
                      <p className="text-sm text-gray-500 line-clamp-2 mt-1">
                        {kb.description || 'No description added'}
                      </p>
                    </div>
                  </div>

                  {/* Status Badge */}
                  <div className="mb-4">
                    {kb.is_active ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
                        <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                        <span className="w-1.5 h-1.5 bg-gray-400 rounded-full"></span>
                        Inactive
                      </span>
                    )}
                  </div>

                  {/* Stats */}
                  <div className="flex items-center gap-4 mb-4 py-3 border-t border-gray-100">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-600">
                        <span className="font-semibold text-gray-900">{kb.document_count}</span> documents
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-500">{formatDate(kb.updated_at)}</span>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-2">
                    <Link
                      href={`/knowledge-bases/${kb.id}`}
                      prefetch={false}
                      className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                      Open
                    </Link>
                    <Link
                      href={`/knowledge-bases/${kb.id}/edit`}
                      prefetch={false}
                      className="inline-flex items-center justify-center px-3 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                      <Edit className="w-4 h-4" />
                    </Link>
                    <button
                      onClick={() => openDeleteModal(kb)}
                      className="inline-flex items-center justify-center px-3 py-2.5 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
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

      {/* Delete Confirmation Modal */}
      {deleteModal.show && deleteModal.kb && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 bg-red-100 rounded-xl">
                <Trash2 className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Delete Knowledge Base</h3>
            </div>

            <p className="text-gray-600 mb-6">
              Are you sure you want to delete <span className="font-semibold text-gray-900">"{deleteModal.kb.name}"</span>?
              All documents and data will be permanently removed.
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
