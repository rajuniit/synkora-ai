'use client'

import { useState, useEffect, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import {
  Search,
  Sparkles,
  Zap,
  Brain,
  TrendingUp,
  MessageSquare,
  Eye,
  Star,
  ChevronLeft,
  ChevronRight,
  LayoutGrid,
  List,
  SlidersHorizontal,
  CheckCircle,
  Award,
  Tag,
} from 'lucide-react'
import toast from 'react-hot-toast'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

interface PublicAgent {
  id: string
  agent_name: string
  description: string
  avatar?: string
  category: string
  tags: string[]
  likes_count: number
  dislikes_count: number
  usage_count: number
  model_name: string
  created_at: string
  user_rating?: 'like' | 'dislike' | null
  system_prompt?: string
  tools?: any[]
  provider?: string
}

interface Category {
  category: string
  count: number
}

// Get icon based on category
const getCategoryIcon = (category: string, size: number = 32) => {
  const icons: Record<string, any> = {
    Productivity: Zap,
    Research: Search,
    Development: Brain,
    Writing: Eye,
    'Data Analysis': TrendingUp,
    'Customer Support': MessageSquare,
    Education: Star,
    Entertainment: Sparkles,
    Other: Sparkles,
  }
  const Icon = icons[category] || Sparkles
  return <Icon size={size} />
}

const getInitials = (name: string) =>
  name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

// Get rating from likes/dislikes
const getRating = (agent: PublicAgent) => {
  const total = agent.likes_count + agent.dislikes_count
  if (total === 0) return 4.5
  const ratio = agent.likes_count / total
  return Math.round((3 + ratio * 2) * 10) / 10
}

// Get badge type based on agent properties
const getBadge = (agent: PublicAgent) => {
  const rating = getRating(agent)
  if (rating >= 4.9) return { type: 'top_rated', label: 'TOP RATED' }
  if (agent.usage_count > 100) return { type: 'verified', label: 'VERIFIED' }
  return null
}

// Main categories from agent creation
const mainCategories = [
  'Productivity',
  'Research',
  'Development',
  'Writing',
  'Data Analysis',
  'Customer Support',
  'Education',
  'Entertainment',
  'Other',
]

export default function BrowsePage() {
  const router = useRouter()
  const [agents, setAgents] = useState<PublicAgent[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [sortBy, setSortBy] = useState<string>('popular')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 9

  useEffect(() => {
    fetchCategories()
    fetchAgents()
  }, [selectedCategory, sortBy, searchQuery])

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/agents/categories`)
      const data = await response.json()
      if (data.success) {
        const normalized = (data.data.categories || []).map((c: any) => ({
          category: c.category || c.name,
          count: c.count ?? 0,
        }))
        setCategories(normalized)
      }
    } catch (error) {
      console.error('Failed to fetch categories:', error)
    }
  }

  const fetchAgents = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (selectedCategory) params.append('category', selectedCategory)
      if (searchQuery) params.append('search', searchQuery)
      if (sortBy) params.append('sort_by', sortBy)
      params.append('limit', '50')

      const response = await fetch(`${API_URL}/api/v1/agents/public?${params}`)
      const data = await response.json()
      if (data.success) {
        setAgents(data.data.agents)
      }
    } catch (error) {
      console.error('Failed to fetch agents:', error)
      toast.error('Failed to load agents')
    } finally {
      setLoading(false)
    }
  }

  const clearAllFilters = () => {
    setSelectedCategory('')
    setSelectedTags([])
    setSearchQuery('')
    setCurrentPage(1)
  }

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    )
  }

  // Extract all unique tags from agents
  const availableTags = useMemo(() => {
    const tagSet = new Set<string>()
    agents.forEach((agent) => {
      agent.tags?.forEach((tag) => tagSet.add(tag))
    })
    return Array.from(tagSet).slice(0, 10) // Limit to 10 tags
  }, [agents])

  // Filtered and paginated agents
  const filteredAgents = useMemo(() => {
    let result = [...agents]
    if (selectedTags.length > 0) {
      result = result.filter((a) =>
        selectedTags.some((tag) => a.tags?.includes(tag))
      )
    }
    return result
  }, [agents, selectedTags])

  const totalPages = Math.ceil(filteredAgents.length / itemsPerPage)
  const paginatedAgents = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage
    return filteredAgents.slice(start, start + itemsPerPage)
  }, [filteredAgents, currentPage])

  // Use main categories for the sidebar
  const displayCategories = mainCategories

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Breadcrumb */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-3">
          <nav className="flex items-center gap-2 text-sm">
            <button onClick={() => router.push('/')} className="text-gray-500 hover:text-red-600">
              Home
            </button>
            <ChevronRight size={14} className="text-gray-400" />
            <button onClick={() => router.push('/browse')} className="text-gray-500 hover:text-red-600">
              Marketplace
            </button>
            {selectedCategory && (
              <>
                <ChevronRight size={14} className="text-gray-400" />
                <span className="text-gray-900 font-medium">{selectedCategory} Agents</span>
              </>
            )}
          </nav>
        </div>
      </div>

      {/* Hero Section */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-xl sm:text-3xl font-bold text-gray-900">
                {selectedCategory ? `${selectedCategory} AI Agents` : 'AI Agents Marketplace'}
              </h1>
              <p className="mt-2 text-gray-600 max-w-2xl">
                Scale your operations with autonomous intelligence. Discover, deploy, and manage
                specialized agents for sales, HR, and document analysis.
              </p>
            </div>
            <button
              onClick={clearAllFilters}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <SlidersHorizontal size={16} />
              Clear All Filters
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-4 md:py-8">
        <div className="flex flex-col md:flex-row gap-6 md:gap-8">
          {/* Left Sidebar - hidden on mobile by default, shown on md+ */}
          <div className="w-full md:w-64 md:flex-shrink-0">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              {/* Categories */}
              <div className="mb-6">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  CATEGORIES
                </h3>
                <div className="space-y-1">
                  {displayCategories.map((cat) => (
                    <button
                      key={cat}
                      onClick={() =>
                        setSelectedCategory(cat === selectedCategory ? '' : cat)
                      }
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-colors ${
                        selectedCategory === cat
                          ? 'bg-red-50 text-red-700 font-medium'
                          : 'text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      <span className="text-gray-400">
                        {getCategoryIcon(cat, 16)}
                      </span>
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              {availableTags.length > 0 && (
                <>
                  <div className="border-t border-gray-200 my-4" />

                  {/* Tags Filter */}
                  <div>
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                      TAGS
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {availableTags.map((tag) => (
                        <button
                          key={tag}
                          onClick={() => toggleTag(tag)}
                          className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                            selectedTags.includes(tag)
                              ? 'bg-red-500 text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {tag}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Right Content */}
          <div className="flex-1 min-w-0">
            {/* Toolbar */}
            <div className="flex items-center justify-between mb-6">
              <div className="text-sm text-gray-600">
                Showing <span className="font-semibold text-gray-900">{filteredAgents.length} Agents</span>
                {selectedCategory && (
                  <span>
                    {' '}
                    for "<span className="text-gray-900">{selectedCategory}</span>"
                  </span>
                )}
              </div>

              <div className="flex items-center gap-3">
                {/* Sort */}
                <div className="flex items-center gap-2">
                  <select
                    aria-label="Sort by"
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="rounded-lg border border-gray-200 bg-white text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  >
                    <option value="popular">Most Popular</option>
                    <option value="recent">Recently Added</option>
                    <option value="rating">Highest Rated</option>
                    <option value="name">Name (A-Z)</option>
                  </select>
                </div>

                {/* View Toggle */}
                <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-2 ${
                      viewMode === 'grid' ? 'bg-red-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                    }`}
                    aria-label="Grid view"
                  >
                    <LayoutGrid size={18} />
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`p-2 ${
                      viewMode === 'list' ? 'bg-red-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                    }`}
                    aria-label="List view"
                  >
                    <List size={18} />
                  </button>
                </div>
              </div>
            </div>

            {/* Agent Cards Grid */}
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div
                    key={i}
                    className="bg-white rounded-xl border border-gray-200 overflow-hidden animate-pulse"
                  >
                    <div className="h-32 bg-gray-100" />
                    <div className="p-4 space-y-3">
                      <div className="h-4 bg-gray-100 rounded w-3/4" />
                      <div className="h-3 bg-gray-100 rounded w-1/2" />
                      <div className="h-10 bg-gray-100 rounded" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div
                className={
                  viewMode === 'grid'
                    ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5'
                    : 'space-y-4'
                }
              >
                {paginatedAgents.map((agent) => {
                  const badge = getBadge(agent)
                  const rating = getRating(agent)

                  if (viewMode === 'list') {
                    return (
                      <div
                        key={agent.id}
                        onClick={() => router.push(`/browse/${agent.id}`)}
                        className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer flex gap-4"
                      >
                        <div className="w-20 h-20 rounded-lg bg-gradient-to-br from-red-50 to-red-100 flex items-center justify-center text-red-500 flex-shrink-0">
                          {getCategoryIcon(agent.category, 32)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h3 className="text-base font-semibold text-gray-900">
                              {agent.agent_name}
                            </h3>
                            {badge && (
                              <span
                                className={`px-2 py-0.5 rounded text-xs font-medium ${
                                  badge.type === 'top_rated'
                                    ? 'bg-amber-100 text-amber-700'
                                    : 'bg-green-100 text-green-700'
                                }`}
                              >
                                {badge.type === 'verified' && <CheckCircle size={10} className="inline mr-1" />}
                                {badge.type === 'top_rated' && <Award size={10} className="inline mr-1" />}
                                {badge.label}
                              </span>
                            )}
                            <div className="flex items-center gap-1 text-sm text-amber-500 ml-auto">
                              <Star size={14} fill="currentColor" />
                              {rating}
                            </div>
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5">{agent.category || 'General'}</p>
                          <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                            {agent.description || 'AI agent for your business needs.'}
                          </p>
                        </div>
                        <div className="flex flex-col items-end justify-between">
                          <div className="text-right">
                            <div className="text-xs text-gray-500 uppercase">STARTING AT</div>
                            <div className="text-lg font-bold text-gray-900">$49<span className="text-sm font-normal text-gray-500">/mo</span></div>
                          </div>
                          <button className="px-4 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors">
                            View Details
                          </button>
                        </div>
                      </div>
                    )
                  }

                  return (
                    <div
                      key={agent.id}
                      onClick={() => router.push(`/browse/${agent.id}`)}
                      className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow cursor-pointer group"
                    >
                      {/* Card Header */}
                      <div className="relative h-32 bg-gradient-to-br from-red-50 to-red-100 flex items-center justify-center">
                        {badge && (
                          <span
                            className={`absolute top-3 left-3 px-2.5 py-1 rounded-full text-xs font-semibold flex items-center gap-1 ${
                              badge.type === 'top_rated'
                                ? 'bg-amber-100 text-amber-700'
                                : 'bg-green-100 text-green-700'
                            }`}
                          >
                            {badge.type === 'verified' && <CheckCircle size={12} />}
                            {badge.type === 'top_rated' && <Award size={12} />}
                            {badge.label}
                          </span>
                        )}
                        <div className="w-16 h-16 rounded-xl bg-white/80 backdrop-blur-sm flex items-center justify-center text-red-500 shadow-sm group-hover:scale-110 transition-transform">
                          {agent.avatar ? (
                            agent.avatar.startsWith('http://') || agent.avatar.startsWith('https://') ? (
                              <img
                                src={agent.avatar}
                                alt={agent.agent_name}
                                className="w-full h-full object-cover rounded-xl"
                              />
                            ) : (
                              <Image
                                src={agent.avatar}
                                alt={agent.agent_name}
                                fill
                                className="object-cover rounded-xl"
                              />
                            )
                          ) : (
                            getCategoryIcon(agent.category, 32)
                          )}
                        </div>
                      </div>

                      {/* Card Body */}
                      <div className="p-4">
                        <div className="flex items-start justify-between">
                          <div>
                            <h3 className="text-base font-semibold text-gray-900">
                              {agent.agent_name}
                            </h3>
                            <p className="text-xs text-gray-500 mt-0.5">
                              {agent.category || 'General'}
                            </p>
                          </div>
                          <div className="flex items-center gap-1 text-amber-500">
                            <Star size={14} fill="currentColor" />
                            <span className="text-sm font-medium">{rating}</span>
                          </div>
                        </div>

                        <p className="text-sm text-gray-600 mt-2 line-clamp-2 min-h-[40px]">
                          {agent.description || 'AI agent for your business needs.'}
                        </p>

                        <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100">
                          <div>
                            <div className="text-xs text-gray-500 uppercase">STARTING AT</div>
                            <div className="text-lg font-bold text-gray-900">
                              $49<span className="text-sm font-normal text-gray-500">/mo</span>
                            </div>
                          </div>
                          <button className="px-4 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors">
                            View Details
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Previous page"
                >
                  <ChevronLeft size={18} />
                </button>

                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum: number
                  if (totalPages <= 5) {
                    pageNum = i + 1
                  } else if (currentPage <= 3) {
                    pageNum = i + 1
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i
                  } else {
                    pageNum = currentPage - 2 + i
                  }

                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`w-10 h-10 rounded-lg text-sm font-medium transition-colors ${
                        currentPage === pageNum
                          ? 'bg-red-500 text-white'
                          : 'border border-gray-200 text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      {pageNum}
                    </button>
                  )
                })}

                {totalPages > 5 && currentPage < totalPages - 2 && (
                  <>
                    <span className="text-gray-400">...</span>
                    <button
                      onClick={() => setCurrentPage(totalPages)}
                      className="w-10 h-10 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50"
                    >
                      {totalPages}
                    </button>
                  </>
                )}

                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Next page"
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

    </div>
  )
}
