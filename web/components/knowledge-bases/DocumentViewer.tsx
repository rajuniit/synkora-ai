'use client'

import { useState, useEffect } from 'react'
import { X, Download, Loader2, FileText, AlertCircle, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react'
import { apiClient } from '@/lib/api/client'

interface Segment {
  id: string
  position: number
  content: string
  word_count: number
  tokens: number
  created_at: string
}

interface DocumentDetails {
  id: string
  title: string
  source_type: string
  source_url?: string
  s3_url?: string
  mime_type?: string
  file_size?: number
  chunk_count: number
  has_images: boolean
  image_count: number
  images: any[]
  created_at: string
  updated_at: string
  metadata: Record<string, any>
  data_source?: {
    id: string
    name: string
    type: string
  }
  content?: string
  segments: Segment[]
}

interface DocumentViewerProps {
  kbId: string
  docId: string
  docTitle: string
  onClose: () => void
  onDownload: () => Promise<void>
}

export default function DocumentViewer({
  kbId,
  docId,
  onClose,
  onDownload,
}: DocumentViewerProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [docDetails, setDocDetails] = useState<DocumentDetails | null>(null)
  const [activeTab, setActiveTab] = useState<'preview' | 'chunks'>('preview')
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadDocument()
  }, [docId])

  const loadDocument = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch document details with content and segments
      const details = await apiClient.getKnowledgeBaseDocument(kbId, docId)
      setDocDetails(details)
    } catch (err) {
      console.error('Error loading document:', err)
      setError(err instanceof Error ? err.message : 'Failed to load document')
    } finally {
      setLoading(false)
    }
  }

  const handleViewInNewTab = () => {
    if (docDetails?.s3_url) {
      window.open(docDetails.s3_url, '_blank')
    } else if (docDetails?.source_url) {
      window.open(docDetails.source_url, '_blank')
    }
  }

  const toggleChunk = (chunkId: string) => {
    const newExpanded = new Set(expandedChunks)
    if (newExpanded.has(chunkId)) {
      newExpanded.delete(chunkId)
    } else {
      newExpanded.add(chunkId)
    }
    setExpandedChunks(newExpanded)
  }

  const expandAllChunks = () => {
    if (docDetails) {
      setExpandedChunks(new Set(docDetails.segments.map(s => s.id)))
    }
  }

  const collapseAllChunks = () => {
    setExpandedChunks(new Set())
  }

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'N/A'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const isPDF = (mimeType?: string) => {
    return mimeType === 'application/pdf' || docDetails?.title.toLowerCase().endsWith('.pdf')
  }

  const isOfficeDoc = (mimeType?: string) => {
    const officeTypes = [
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-powerpoint',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    ]
    return officeTypes.includes(mimeType || '') || 
           docDetails?.title.toLowerCase().match(/\.(doc|docx|xls|xlsx|ppt|pptx)$/)
  }

  const renderPreview = () => {
    if (!docDetails) return null

    const fileUrl = docDetails.s3_url || docDetails.source_url

    // PDF Preview using iframe
    if (isPDF(docDetails.mime_type) && fileUrl) {
      return (
        <div className="flex flex-col h-full">
          <div className="flex-1 bg-gray-100">
            <iframe
              src={fileUrl}
              className="w-full h-full border-0"
              title={docDetails.title}
            />
          </div>
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-600 text-center">
            PDF viewer. For better experience,{' '}
            <button
              onClick={handleViewInNewTab}
              className="text-blue-600 hover:text-blue-700 underline"
            >
              open in a new tab
            </button>
          </div>
        </div>
      )
    }

    // Office Document Preview (DOC, DOCX, XLS, XLSX, PPT, PPTX)
    if (isOfficeDoc(docDetails.mime_type) && fileUrl) {
      // Use Google Docs Viewer for Office documents
      const viewerUrl = `https://docs.google.com/viewer?url=${encodeURIComponent(fileUrl)}&embedded=true`
      
      return (
        <div className="flex flex-col h-full">
          <div className="flex-1 bg-gray-100">
            <iframe
              src={viewerUrl}
              className="w-full h-full border-0"
              title={docDetails.title}
            />
          </div>
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-600 text-center">
            If the document doesn't display, try{' '}
            <button
              onClick={handleViewInNewTab}
              className="text-blue-600 hover:text-blue-700 underline"
            >
              opening it in a new tab
            </button>
          </div>
        </div>
      )
    }

    return (
      <div className="prose max-w-none p-6">
        {docDetails.content ? (
          <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
            <pre className="whitespace-pre-wrap font-sans text-sm text-gray-800 leading-relaxed">
              {docDetails.content}
            </pre>
          </div>
        ) : (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No preview available for this document</p>
            <p className="text-sm text-gray-500 mt-2">
              Try downloading the file or viewing it in a new tab
            </p>
            {fileUrl && (
              <button
                onClick={handleViewInNewTab}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center gap-2"
              >
                <ExternalLink className="w-4 h-4" />
                Open in New Tab
              </button>
            )}
          </div>
        )}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Loading document...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl p-8 max-w-md">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Failed to Load Document
            </h3>
            <p className="text-gray-600 mb-4">{error}</p>
            <div className="flex gap-2 justify-center">
              <button
                onClick={loadDocument}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!docDetails) {
    return null
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold text-gray-900 truncate">
              {docDetails.title}
            </h2>
            <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                {docDetails.source_type}
              </span>
              <span>{formatFileSize(docDetails.file_size)}</span>
              <span>{docDetails.chunk_count} chunks</span>
              {docDetails.has_images && (
                <span>{docDetails.image_count} images</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 ml-4">
            {(docDetails.s3_url || docDetails.source_url) && (
              <button
                onClick={handleViewInNewTab}
                className="px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors inline-flex items-center gap-2"
                title="View in new tab"
              >
                <ExternalLink className="w-4 h-4" />
                Open
              </button>
            )}
            <button
              onClick={onDownload}
              className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              title="Download"
            >
              <Download className="w-5 h-5" />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 px-6">
          <button
            onClick={() => setActiveTab('preview')}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'preview'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Preview
          </button>
          <button
            onClick={() => setActiveTab('chunks')}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'chunks'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Chunks ({docDetails.segments.length})
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'preview' ? (
            renderPreview()
          ) : (
            <div className="h-full overflow-auto p-6">
              <div className="space-y-4">
                {/* Chunk Controls */}
                <div className="flex items-center justify-between pb-4 border-b border-gray-200">
                  <h3 className="text-sm font-medium text-gray-700">
                    {docDetails.segments.length} chunk{docDetails.segments.length !== 1 ? 's' : ''}
                  </h3>
                  <div className="flex gap-2">
                    <button
                      onClick={expandAllChunks}
                      className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                    >
                      Expand All
                    </button>
                    <span className="text-gray-300">|</span>
                    <button
                      onClick={collapseAllChunks}
                      className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                    >
                      Collapse All
                    </button>
                  </div>
                </div>

                {/* Chunks List */}
                {docDetails.segments.length === 0 ? (
                  <div className="text-center py-12">
                    <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">No chunks available</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {docDetails.segments.map((segment) => {
                      const isExpanded = expandedChunks.has(segment.id)
                      return (
                        <div
                          key={segment.id}
                          className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:border-gray-300 transition-colors"
                        >
                          <button
                            onClick={() => toggleChunk(segment.id)}
                            className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
                          >
                            <div className="flex items-center gap-3 text-left">
                              <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">
                                {segment.position}
                              </span>
                              <div>
                                <p className="text-sm font-medium text-gray-900">
                                  Chunk {segment.position}
                                </p>
                                <p className="text-xs text-gray-500">
                                  {segment.word_count} words · {segment.tokens} tokens
                                </p>
                              </div>
                            </div>
                            {isExpanded ? (
                              <ChevronUp className="w-5 h-5 text-gray-400" />
                            ) : (
                              <ChevronDown className="w-5 h-5 text-gray-400" />
                            )}
                          </button>
                          
                          {isExpanded && (
                            <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
                              <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700 leading-relaxed">
                                {segment.content}
                              </pre>
                              <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500">
                                Created: {formatDate(segment.created_at)}
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer with Metadata */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Created</p>
              <p className="font-medium text-gray-900">{formatDate(docDetails.created_at)}</p>
            </div>
            <div>
              <p className="text-gray-500">Updated</p>
              <p className="font-medium text-gray-900">{formatDate(docDetails.updated_at)}</p>
            </div>
            {docDetails.data_source && (
              <div>
                <p className="text-gray-500">Data Source</p>
                <p className="font-medium text-gray-900">{docDetails.data_source.name}</p>
              </div>
            )}
            {docDetails.mime_type && (
              <div>
                <p className="text-gray-500">Type</p>
                <p className="font-medium text-gray-900">{docDetails.mime_type}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
