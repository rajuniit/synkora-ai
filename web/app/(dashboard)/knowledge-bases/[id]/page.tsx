'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import {
  Database,
  ArrowLeft,
  Edit,
  Trash2,
  FileText,
  Layers,
  Activity,
  Search,
  AlertCircle,
  CheckCircle,
  Upload,
  Type,
  Globe,
  X,
  Loader2
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'
import FileUpload from '@/components/knowledge-bases/FileUpload'
import DocumentBrowser from '@/components/knowledge-bases/DocumentBrowser'

interface KnowledgeBase {
  id: number
  name: string
  description: string
  vector_db_provider: string
  embedding_provider: string
  embedding_model: string
  chunk_size: number
  chunk_overlap: number
  document_count: number
  total_chunks: number
  is_active: boolean
  created_at: string
  updated_at: string
}

interface DataSource {
  id: number
  source_type: string
  sync_status: string
  last_sync_at: string | null
  total_documents: number
}

interface SearchResult {
  content: string
  score: number
  metadata: Record<string, any>
}

export default function KnowledgeBaseDetailsPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [activeTab, setActiveTab] = useState<'overview' | 'sources' | 'documents' | 'search'>('overview')
  const [kb, setKb] = useState<KnowledgeBase | null>(null)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleting, setDeleting] = useState(false)
  
  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

  // Add content modals
  const [showPasteModal, setShowPasteModal] = useState(false)
  const [showWebsiteModal, setShowWebsiteModal] = useState(false)
  const [pasteTitle, setPasteTitle] = useState('')
  const [pasteContent, setPasteContent] = useState('')
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [addingContent, setAddingContent] = useState(false)

  useEffect(() => {
    fetchKnowledgeBase()
    fetchDataSources()
  }, [id])

  const fetchKnowledgeBase = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getKnowledgeBase(id)
      setKb(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      toast.error('Failed to load knowledge base')
    } finally {
      setLoading(false)
    }
  }

  const fetchDataSources = async () => {
    try {
      const data = await apiClient.getDataSources()
      // Filter by knowledge_base_id on client side for now
      setDataSources(Array.isArray(data) ? data.filter((ds: any) => ds.knowledge_base_id === parseInt(id)) : [])
    } catch (err) {
      console.error('Failed to fetch data sources:', err)
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return

    try {
      setSearching(true)
      setSearchError(null)
      const data = await apiClient.searchKnowledgeBase(id, searchQuery, 5)
      setSearchResults(data.data?.results || [])
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : 'Search failed')
      toast.error('Search failed')
    } finally {
      setSearching(false)
    }
  }

  const handleDelete = async () => {
    try {
      setDeleting(true)
      await apiClient.deleteKnowledgeBase(id)
      toast.success('Knowledge base deleted successfully')
      router.push('/knowledge-bases')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete knowledge base')
    } finally {
      setDeleting(false)
      setShowDeleteModal(false)
    }
  }

  const getProviderIcon = (provider: string) => {
    const icons: Record<string, string> = {
      QDRANT: '🔍',
      PINECONE: '🌲',
      WEAVIATE: '🔷',
      CHROMA: '🎨',
      MILVUS: '⚡',
    }
    return icons[provider?.toLowerCase()] || '📦'
  }

  const handleAddTextContent = async () => {
    if (!pasteTitle.trim() || !pasteContent.trim()) {
      toast.error('Please provide both title and content')
      return
    }

    setAddingContent(true)
    try {
      await apiClient.addTextContent(id, pasteTitle, pasteContent)
      toast.success('Text content added successfully')
      setShowPasteModal(false)
      setPasteTitle('')
      setPasteContent('')
      fetchKnowledgeBase()
      // Refresh documents tab
      setActiveTab('overview')
      setTimeout(() => setActiveTab('documents'), 0)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to add text content')
    } finally {
      setAddingContent(false)
    }
  }

  const handleCrawlWebsite = async () => {
    if (!websiteUrl.trim()) {
      toast.error('Please provide a URL')
      return
    }

    // Basic URL validation
    try {
      new URL(websiteUrl)
    } catch {
      toast.error('Please enter a valid URL (e.g., https://example.com)')
      return
    }

    setAddingContent(true)
    try {
      const result = await apiClient.crawlWebsite(id, websiteUrl)
      toast.success(result.message || 'Website content added successfully')
      setShowWebsiteModal(false)
      setWebsiteUrl('')
      fetchKnowledgeBase()
      // Refresh documents tab
      setActiveTab('overview')
      setTimeout(() => setActiveTab('documents'), 0)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to crawl website')
    } finally {
      setAddingContent(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600"></div>
      </div>
    )
  }

  if (error || !kb) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
        <div className="max-w-5xl mx-auto">
          <div className="bg-red-50 border-l-4 border-red-500 rounded-lg p-5">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <div>
                <h3 className="text-base font-semibold text-red-900">Error</h3>
                <p className="text-red-700 mt-1 text-sm">{error || 'Knowledge base not found'}</p>
              </div>
            </div>
          </div>
          <Link
            href="/knowledge-bases"
            className="mt-5 inline-flex items-center gap-2 text-red-600 hover:text-red-700 font-medium transition-colors text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Knowledge Bases
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Link
            href="/knowledge-bases"
            className="inline-flex items-center gap-2 text-red-600 hover:text-red-700 font-medium mb-5 transition-colors text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Knowledge Bases
          </Link>
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1">
                <div className="p-2.5 bg-red-600 rounded-lg shadow-sm">
                  <Database className="w-6 h-6 text-white" />
                </div>
                <div className="flex-1">
                  <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">{kb.name}</h1>
                  {kb.description && (
                    <p className="text-gray-600 mt-1 text-sm">{kb.description}</p>
                  )}
                  <div className="flex flex-wrap gap-2 mt-3">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      <span className="text-base">{getProviderIcon(kb.vector_db_provider)}</span>
                      {kb.vector_db_provider}
                    </span>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                      {kb.embedding_model}
                    </span>
                    {kb.is_active ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                        <CheckCircle className="w-3.5 h-3.5" />
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        <AlertCircle className="w-3.5 h-3.5" />
                        Inactive
                      </span>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="flex gap-2">
                <Link
                  href={`/knowledge-bases/${id}/wiki`}
                  className="inline-flex items-center gap-2 px-3 py-2 text-xs font-medium text-purple-600 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Wiki
                </Link>
                <Link
                  href={`/knowledge-bases/${id}/edit`}
                  className="inline-flex items-center gap-2 px-3 py-2 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                >
                  <Edit className="w-3.5 h-3.5" />
                  Edit
                </Link>
                <button
                  onClick={() => setShowDeleteModal(true)}
                  className="inline-flex items-center gap-2 px-3 py-2 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-2 bg-red-100 rounded-lg">
                <FileText className="w-4 h-4 text-red-600" />
              </div>
              <p className="text-xs font-medium text-gray-600">Documents</p>
            </div>
            <p className="text-2xl font-bold text-gray-900">{kb.document_count}</p>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Layers className="w-4 h-4 text-purple-600" />
              </div>
              <p className="text-xs font-medium text-gray-600">Chunks</p>
            </div>
            <p className="text-2xl font-bold text-gray-900">{kb.total_chunks}</p>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-2 bg-emerald-100 rounded-lg">
                <Database className="w-4 h-4 text-emerald-600" />
              </div>
              <p className="text-xs font-medium text-gray-600">Data Sources</p>
            </div>
            <p className="text-2xl font-bold text-gray-900">{dataSources.length}</p>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-2 bg-red-100 rounded-lg">
                <Activity className="w-4 h-4 text-red-600" />
              </div>
              <p className="text-xs font-medium text-gray-600">Status</p>
            </div>
            <p className="text-xl font-bold text-gray-900">{kb.is_active ? 'Active' : 'Inactive'}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-6 px-5">
              <button
                onClick={() => setActiveTab('overview')}
                className={`py-3 px-1 border-b-2 font-medium text-xs transition-colors ${
                  activeTab === 'overview'
                    ? 'border-red-500 text-red-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setActiveTab('sources')}
                className={`py-3 px-1 border-b-2 font-medium text-xs transition-colors ${
                  activeTab === 'sources'
                    ? 'border-red-500 text-red-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Data Sources ({dataSources.length})
              </button>
              <button
                onClick={() => setActiveTab('documents')}
                className={`py-3 px-1 border-b-2 font-medium text-xs transition-colors ${
                  activeTab === 'documents'
                    ? 'border-red-500 text-red-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="flex items-center gap-2">
                  <Upload className="w-3.5 h-3.5" />
                  Documents ({kb.document_count})
                </span>
              </button>
              <button
                onClick={() => setActiveTab('search')}
                className={`py-3 px-1 border-b-2 font-medium text-xs transition-colors ${
                  activeTab === 'search'
                    ? 'border-red-500 text-red-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="flex items-center gap-2">
                  <Search className="w-3.5 h-3.5" />
                  Search
                </span>
              </button>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-5">
            {activeTab === 'overview' && (
              <div className="space-y-5">
                <div>
                  <h2 className="text-base font-semibold text-gray-900 mb-3">Configuration</h2>
                  <dl className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="bg-red-50 rounded-lg p-3">
                      <dt className="text-xs font-medium text-gray-500 mb-1">Vector Database</dt>
                      <dd className="text-sm font-semibold text-gray-900">{kb.vector_db_provider}</dd>
                    </div>
                    <div className="bg-red-50 rounded-lg p-3">
                      <dt className="text-xs font-medium text-gray-500 mb-1">Embedding Provider</dt>
                      <dd className="text-sm font-semibold text-gray-900">{kb.embedding_provider}</dd>
                    </div>
                    <div className="bg-red-50 rounded-lg p-3">
                      <dt className="text-xs font-medium text-gray-500 mb-1">Embedding Model</dt>
                      <dd className="text-sm font-semibold text-gray-900">{kb.embedding_model}</dd>
                    </div>
                    <div className="bg-red-50 rounded-lg p-3">
                      <dt className="text-xs font-medium text-gray-500 mb-1">Chunk Size</dt>
                      <dd className="text-sm font-semibold text-gray-900">{kb.chunk_size} characters</dd>
                    </div>
                    <div className="bg-red-50 rounded-lg p-3">
                      <dt className="text-xs font-medium text-gray-500 mb-1">Chunk Overlap</dt>
                      <dd className="text-sm font-semibold text-gray-900">{kb.chunk_overlap} characters</dd>
                    </div>
                    <div className="bg-red-50 rounded-lg p-3">
                      <dt className="text-xs font-medium text-gray-500 mb-1">Created</dt>
                      <dd className="text-sm font-semibold text-gray-900">
                        {new Date(kb.created_at).toLocaleDateString()}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>
            )}

            {activeTab === 'sources' && (
              <div>
                {dataSources.length === 0 ? (
                  <div className="text-center py-10">
                    <Database className="w-12 h-12 text-red-400 mx-auto mb-4" />
                    <h3 className="text-base font-semibold text-gray-900 mb-2">No data sources connected</h3>
                    <p className="text-gray-600 text-sm mb-5">Connect a data source to start syncing documents to this knowledge base.</p>
                    <Link
                      href={`/data-sources/connect?kb_id=${id}`}
                      className="inline-flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all text-xs font-medium shadow-sm"
                    >
                      <Database className="w-4 h-4" />
                      Connect Data Source
                    </Link>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {dataSources.map((source) => (
                      <Link
                        key={source.id}
                        href={`/data-sources/${source.id}`}
                        className="bg-white rounded-xl border-2 border-gray-200 p-5 hover:border-red-300 hover:shadow-md transition-all"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            {source.source_type}
                          </span>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            source.sync_status === 'active' ? 'bg-emerald-100 text-emerald-800' :
                            source.sync_status === 'error' ? 'bg-red-100 text-red-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {source.sync_status}
                          </span>
                        </div>
                        <div className="space-y-2">
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Documents</p>
                            <p className="text-xl font-bold text-gray-900">{source.total_documents}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Last Sync</p>
                            <p className="text-xs text-gray-900">
                              {source.last_sync_at
                                ? new Date(source.last_sync_at).toLocaleString()
                                : 'Never'}
                            </p>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'documents' && (
              <div className="space-y-6">
                {/* Add Content Section */}
                <div>
                  <h3 className="text-base font-semibold text-gray-900 mb-2">Add Content</h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Add information to this knowledge base. Your AI agents will use this content to answer questions.
                  </p>

                  {/* Input Source Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    {/* Upload Documents Card */}
                    <div className="bg-white border-2 border-gray-200 rounded-xl p-5 hover:border-red-300 hover:shadow-md transition-all cursor-pointer group">
                      <div className="p-3 bg-red-100 rounded-xl w-fit mb-3 group-hover:bg-red-200 transition-colors">
                        <Upload className="w-6 h-6 text-red-600" />
                      </div>
                      <h4 className="font-semibold text-gray-900 mb-1">Upload Documents</h4>
                      <p className="text-sm text-gray-500">PDF, DOCX, TXT, MD, HTML, CSV (Max 50MB)</p>
                    </div>

                    {/* Paste Text Card */}
                    <button
                      onClick={() => setShowPasteModal(true)}
                      className="bg-white border-2 border-gray-200 rounded-xl p-5 hover:border-red-300 hover:shadow-md transition-all text-left group"
                    >
                      <div className="p-3 bg-purple-100 rounded-xl w-fit mb-3 group-hover:bg-purple-200 transition-colors">
                        <Type className="w-6 h-6 text-purple-600" />
                      </div>
                      <h4 className="font-semibold text-gray-900 mb-1">Paste Text</h4>
                      <p className="text-sm text-gray-500">Direct manual content entry</p>
                    </button>

                    {/* Add Website Card */}
                    <button
                      onClick={() => setShowWebsiteModal(true)}
                      className="bg-white border-2 border-gray-200 rounded-xl p-5 hover:border-red-300 hover:shadow-md transition-all text-left group"
                    >
                      <div className="p-3 bg-emerald-100 rounded-xl w-fit mb-3 group-hover:bg-emerald-200 transition-colors">
                        <Globe className="w-6 h-6 text-emerald-600" />
                      </div>
                      <h4 className="font-semibold text-gray-900 mb-1">Add Website</h4>
                      <p className="text-sm text-gray-500">Crawl content from a URL</p>
                    </button>
                  </div>

                  {/* File Upload Area */}
                  <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                    <FileUpload
                      onUploadComplete={() => {
                        fetchKnowledgeBase()
                        // Trigger document browser refresh by re-mounting
                        setActiveTab('overview')
                        setTimeout(() => setActiveTab('documents'), 0)
                      }}
                      onUpload={async (files, onProgress) => {
                        return await apiClient.uploadDocuments(id, files, onProgress)
                      }}
                    />
                  </div>
                </div>

                {/* Documents List */}
                <div>
                  <h3 className="text-base font-semibold text-gray-900 mb-3">All Documents ({kb.document_count})</h3>
                  <DocumentBrowser
                    kbId={id}
                    onGetDocuments={(params) => apiClient.getKnowledgeBaseDocuments(id, params)}
                    onDeleteDocument={(docId) => apiClient.deleteKnowledgeBaseDocument(id, docId)}
                    onBulkDelete={(docIds) => apiClient.bulkDeleteKnowledgeBaseDocuments(id, docIds)}
                    onDownloadDocument={(docId) => apiClient.downloadKnowledgeBaseDocument(id, docId)}
                  />
                </div>
              </div>
            )}

            {activeTab === 'search' && (
              <div className="space-y-5">
                <form onSubmit={handleSearch} className="flex gap-3">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search knowledge base..."
                    className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                  <button
                    type="submit"
                    disabled={searching || !searchQuery.trim()}
                    className="px-5 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-sm font-medium shadow-sm"
                  >
                    {searching ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Searching...
                      </>
                    ) : (
                      <>
                        <Search className="w-4 h-4" />
                        Search
                      </>
                    )}
                  </button>
                </form>

                {searchError && (
                  <div className="bg-red-50 border-l-4 border-red-500 rounded-lg p-3">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-red-600" />
                      <p className="text-red-700 text-sm">{searchError}</p>
                    </div>
                  </div>
                )}

                {searchResults.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-base font-semibold text-gray-900">
                      Results ({searchResults.length})
                    </h3>
                    {searchResults.map((result, index) => (
                      <div
                        key={index}
                        className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-red-300 transition-all"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                            Score: {(result.score * 100).toFixed(1)}%
                          </span>
                          {result.metadata.source && (
                            <span className="text-xs text-gray-500">
                              Source: {result.metadata.source}
                            </span>
                          )}
                        </div>
                        <p className="text-gray-700 text-sm whitespace-pre-wrap leading-relaxed">{result.content}</p>
                        {result.metadata && Object.keys(result.metadata).length > 0 && (
                          <div className="mt-3 pt-3 border-t border-gray-100">
                            <p className="text-xs font-medium text-gray-500 mb-2">Metadata:</p>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(result.metadata).map(([key, value]) => (
                                <span
                                  key={key}
                                  className="inline-flex items-center px-2 py-1 rounded text-xs bg-red-50 text-gray-700"
                                >
                                  <span className="font-medium">{key}:</span>&nbsp;{String(value)}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {searchResults.length === 0 && searchQuery && !searching && !searchError && (
                  <div className="text-center py-10">
                    <Search className="w-12 h-12 text-red-400 mx-auto mb-4" />
                    <h3 className="text-base font-semibold text-gray-900 mb-2">No results found</h3>
                    <p className="text-gray-600 text-sm">Try adjusting your search query or check if documents have been synced.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertCircle className="w-5 h-5 text-red-600" />
              </div>
              <h3 className="text-base font-semibold text-gray-900">Delete Knowledge Base</h3>
            </div>
            
            <p className="text-gray-600 text-sm mb-5">
              Are you sure you want to delete <span className="font-semibold">"{kb.name}"</span>? 
              This action cannot be undone and will permanently delete all associated documents and data.
            </p>
            
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-white hover:border-red-300 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
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

      {/* Paste Text Modal */}
      {showPasteModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-purple-100 rounded-xl">
                  <Type className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Paste Text Content</h3>
                  <p className="text-sm text-gray-500">Add text directly to your knowledge base</p>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowPasteModal(false)
                  setPasteTitle('')
                  setPasteContent('')
                }}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={pasteTitle}
                  onChange={(e) => setPasteTitle(e.target.value)}
                  placeholder="e.g., Company FAQ, Product Guide, Meeting Notes"
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Content <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={pasteContent}
                  onChange={(e) => setPasteContent(e.target.value)}
                  placeholder="Paste or type your content here..."
                  rows={10}
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
                />
                <p className="text-xs text-gray-500 mt-1">
                  {pasteContent.length} characters
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setShowPasteModal(false)
                  setPasteTitle('')
                  setPasteContent('')
                }}
                disabled={addingContent}
                className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleAddTextContent}
                disabled={addingContent || !pasteTitle.trim() || !pasteContent.trim()}
                className="px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-xl hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {addingContent ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Adding...
                  </>
                ) : (
                  'Add Content'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Website Modal */}
      {showWebsiteModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-emerald-100 rounded-xl">
                  <Globe className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Add Website Content</h3>
                  <p className="text-sm text-gray-500">Crawl and import content from a URL</p>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowWebsiteModal(false)
                  setWebsiteUrl('')
                }}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Website URL <span className="text-red-500">*</span>
                </label>
                <input
                  type="url"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  placeholder="https://example.com/docs"
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 mt-2">
                  We'll extract the main content from this page and add it to your knowledge base.
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setShowWebsiteModal(false)
                  setWebsiteUrl('')
                }}
                disabled={addingContent}
                className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCrawlWebsite}
                disabled={addingContent || !websiteUrl.trim()}
                className="px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-xl hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {addingContent ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Crawling...
                  </>
                ) : (
                  'Crawl Website'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
