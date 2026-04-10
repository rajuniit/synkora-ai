'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils/cn'
import type { WikiArticle, AutopilotStatus } from '@/lib/api/knowledge-autopilot'
import { getWikiArticles, searchWiki, getAutopilotStatus, triggerCompilation } from '@/lib/api/knowledge-autopilot'

const CATEGORY_CONFIG: Record<string, { label: string; icon: string; color: string; bg: string; border: string }> = {
  projects: { label: 'Projects', icon: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z', color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
  people: { label: 'People', icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z', color: 'text-purple-600', bg: 'bg-purple-50', border: 'border-purple-200' },
  decisions: { label: 'Decisions', icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z', color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200' },
  processes: { label: 'Processes', icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  architecture: { label: 'Architecture', icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10', color: 'text-cyan-600', bg: 'bg-cyan-50', border: 'border-cyan-200' },
  general: { label: 'General', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z', color: 'text-gray-500', bg: 'bg-gray-50', border: 'border-gray-200' },
}

interface WikiBrowserProps {
  kbId: string
  kbName: string
}

export function WikiBrowser({ kbId, kbName }: WikiBrowserProps) {
  const router = useRouter()
  const [articles, setArticles] = useState<WikiArticle[]>([])
  const [categories, setCategories] = useState<Record<string, WikiArticle[]>>({})
  const [status, setStatus] = useState<AutopilotStatus | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<WikiArticle[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [compiling, setCompiling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [compileError, setCompileError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [kbId, selectedCategory])

  const loadData = async () => {
    try {
      setError(null)
      const [articlesData, statusData] = await Promise.all([
        getWikiArticles(kbId, selectedCategory || undefined),
        getAutopilotStatus(kbId),
      ])
      setArticles(articlesData.articles || [])
      setCategories(articlesData.categories || {})
      setStatus(statusData)
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to load wiki data'
      setError(msg)
      console.error('Failed to load wiki:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults(null)
      return
    }
    try {
      const data = await searchWiki(kbId, searchQuery)
      setSearchResults(data.results || [])
    } catch (err) {
      console.error('Search failed:', err)
    }
  }

  const handleCompile = async () => {
    setCompiling(true)
    setCompileError(null)
    try {
      const result = await triggerCompilation(kbId)
      if (result?.status === 'failed') {
        setCompileError(result.error || 'Compilation failed')
      }
      await loadData()
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Compilation failed'
      setCompileError(msg)
      console.error('Compilation failed:', err)
    } finally {
      setCompiling(false)
    }
  }

  const displayArticles = searchResults !== null ? searchResults : articles

  const healthPct = status ? ((1 - status.avg_staleness) * 100).toFixed(0) : '100'
  const healthColor =
    !status || status.avg_staleness < 0.3 ? 'text-emerald-500' :
    status.avg_staleness < 0.6 ? 'text-amber-500' : 'text-primary-500'
  const healthBarColor =
    !status || status.avg_staleness < 0.3 ? 'bg-emerald-500' :
    status.avg_staleness < 0.6 ? 'bg-amber-500' : 'bg-primary-500'

  return (
    <div className="flex h-full">
      {/* Left sidebar: categories */}
      <div className="w-64 flex-shrink-0 border-r border-gray-200 bg-white overflow-y-auto hidden md:flex md:flex-col">
        <div className="p-5 flex-1">
          <h3 className="text-[10px] font-extrabold text-gray-400 uppercase tracking-[0.15em] mb-4">Categories</h3>
          <button
            onClick={() => { setSelectedCategory(null); setSearchResults(null) }}
            className={cn(
              'w-full text-left px-3 py-2.5 rounded-xl text-sm font-bold transition-all mb-1',
              !selectedCategory ? 'bg-primary-50 text-primary-600 shadow-sm' : 'text-gray-600 hover:bg-gray-50',
            )}
          >
            All Articles
            <span className={cn('ml-1.5 text-xs font-medium', !selectedCategory ? 'text-primary-400' : 'text-gray-400')}>
              {status?.total_articles || 0}
            </span>
          </button>
          {Object.entries(CATEGORY_CONFIG).map(([key, config]) => {
            const count = status?.category_counts?.[key] || 0
            if (count === 0 && !categories[key]) return null
            return (
              <button
                key={key}
                onClick={() => { setSelectedCategory(key); setSearchResults(null) }}
                className={cn(
                  'w-full text-left px-3 py-2.5 rounded-xl text-sm font-semibold transition-all mb-1 flex items-center gap-2.5',
                  selectedCategory === key ? 'bg-primary-50 text-primary-600 shadow-sm' : 'text-gray-600 hover:bg-gray-50',
                )}
              >
                <svg className={cn('w-4 h-4 flex-shrink-0', selectedCategory === key ? 'text-primary-500' : config.color)} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={config.icon} />
                </svg>
                {config.label}
                <span className={cn('ml-auto text-xs font-medium', selectedCategory === key ? 'text-primary-400' : 'text-gray-400')}>{count}</span>
              </button>
            )
          })}
        </div>

        {/* Autopilot status panel */}
        {status && (
          <div className="p-5 border-t border-gray-100">
            <h3 className="text-[10px] font-extrabold text-gray-400 uppercase tracking-[0.15em] mb-4">Autopilot</h3>

            {/* Health bar */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-gray-500">Knowledge Health</span>
                <span className={cn('text-xs font-extrabold', healthColor)}>{healthPct}%</span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={cn('h-full rounded-full transition-all duration-700', healthBarColor)}
                  style={{ width: `${healthPct}%` }}
                />
              </div>
            </div>

            {status.last_compilation && (
              <div className="text-xs text-gray-500 space-y-1.5 mb-4">
                <div className="flex justify-between">
                  <span className="font-medium">Last compiled</span>
                  <span className="text-gray-700 font-semibold">
                    {status.last_compilation.completed_at
                      ? new Date(status.last_compilation.completed_at).toLocaleDateString()
                      : 'In progress'}
                  </span>
                </div>
                {(status.last_compilation.articles_created > 0 || status.last_compilation.articles_updated > 0) && (
                  <div className="flex justify-between">
                    <span className="font-medium">Changes</span>
                    <span className="text-gray-700 font-semibold">
                      +{status.last_compilation.articles_created} / ~{status.last_compilation.articles_updated}
                    </span>
                  </div>
                )}
              </div>
            )}

            <button
              onClick={handleCompile}
              disabled={compiling}
              className="w-full px-3 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 text-white text-sm font-bold rounded-xl hover:from-primary-600 hover:to-primary-700 transition-all shadow-sm shadow-primary-500/20 disabled:opacity-50"
            >
              {compiling ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Compiling...
                </span>
              ) : (
                'Compile Now'
              )}
            </button>
          </div>
        )}
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto bg-gray-50/80">
        {/* Search bar */}
        <div className="sticky top-0 bg-white/95 backdrop-blur-sm px-5 py-3.5 border-b border-gray-200 z-10">
          <div className="flex items-center gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  if (!e.target.value.trim()) setSearchResults(null)
                }}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search wiki articles..."
                className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border-2 border-gray-200 rounded-xl text-sm font-medium text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 focus:bg-white transition-all"
              />
              <svg className="absolute left-3.5 top-3 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            {/* Mobile compile button */}
            <button
              onClick={handleCompile}
              disabled={compiling}
              className="md:hidden px-4 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 text-white text-xs font-bold rounded-xl disabled:opacity-50"
            >
              {compiling ? 'Compiling...' : 'Compile'}
            </button>
          </div>
        </div>

        {/* Error messages */}
        {(error || compileError) && (
          <div className="mx-5 mt-4">
            <div className="bg-primary-50 border border-primary-200 rounded-xl px-4 py-3 text-sm font-medium text-primary-700">
              {compileError || error}
            </div>
          </div>
        )}

        {/* Articles grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-[3px] border-gray-200 border-b-primary-500 rounded-full animate-spin" />
              <span className="text-xs font-semibold text-gray-400">Loading articles...</span>
            </div>
          </div>
        ) : displayArticles.length === 0 ? (
          <div className="text-center py-20 px-4">
            <div className="w-20 h-20 mx-auto mb-5 rounded-2xl bg-gradient-to-br from-primary-50 to-primary-100/50 flex items-center justify-center border border-primary-200/50">
              <svg className="w-10 h-10 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <h3 className="text-xl font-extrabold tracking-tight text-gray-900 mb-2">No wiki articles yet</h3>
            <p className="text-sm text-gray-500 mb-8 max-w-md mx-auto leading-relaxed">
              Click &ldquo;Compile Now&rdquo; to auto-generate wiki articles from your knowledge base documents using AI.
            </p>
            <button
              onClick={handleCompile}
              disabled={compiling}
              className="px-8 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white text-sm font-bold rounded-xl hover:from-primary-600 hover:to-primary-700 transition-all shadow-lg shadow-primary-500/25 disabled:opacity-50"
            >
              {compiling ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Compiling...
                </span>
              ) : (
                'Generate Wiki'
              )}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 p-5">
            {displayArticles.map((article) => {
              const catConfig = CATEGORY_CONFIG[article.category] || CATEGORY_CONFIG.general
              return (
                <button
                  key={article.id}
                  onClick={() => router.push(`/knowledge-bases/${kbId}/wiki/${article.slug}`)}
                  className="bg-white border border-gray-200 rounded-xl p-5 text-left hover:border-primary-300 hover:shadow-lg hover:shadow-primary-500/5 transition-all group"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <div className={cn('w-6 h-6 rounded-lg flex items-center justify-center', catConfig.bg)}>
                      <svg className={cn('w-3.5 h-3.5', catConfig.color)} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={catConfig.icon} />
                      </svg>
                    </div>
                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">{catConfig.label}</span>
                    {article.staleness_score > 0.5 && (
                      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full ml-auto border border-amber-200">Stale</span>
                    )}
                  </div>
                  <h4 className="text-sm font-bold text-gray-900 mb-1.5 line-clamp-2 group-hover:text-primary-600 transition-colors">{article.title}</h4>
                  {article.summary && (
                    <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">{article.summary}</p>
                  )}
                  <div className="flex items-center gap-3 mt-4 pt-3 border-t border-gray-100 text-[10px] font-semibold text-gray-400">
                    <span className="flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      {article.source_documents?.length || 0} sources
                    </span>
                    <span className="flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                      </svg>
                      {(article.forward_links?.length || 0) + (article.backlinks?.length || 0)} links
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
