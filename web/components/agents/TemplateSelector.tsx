'use client'

import { useState } from 'react'
import { Search, X, Check, Sparkles } from 'lucide-react'
import { AGENT_TEMPLATES, TEMPLATE_CATEGORIES, AgentTemplate, searchTemplates, getTemplatesByCategory } from '@/lib/data/agent-templates'

interface TemplateSelectorProps {
  onSelect: (template: AgentTemplate) => void
  onClose: () => void
}

export default function TemplateSelector({ onSelect, onClose }: TemplateSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [hoveredTemplate, setHoveredTemplate] = useState<string | null>(null)

  const filteredTemplates = searchQuery
    ? searchTemplates(searchQuery)
    : selectedCategory
      ? getTemplatesByCategory(selectedCategory)
      : AGENT_TEMPLATES

  const groupedTemplates = selectedCategory || searchQuery
    ? { [selectedCategory || 'Search Results']: filteredTemplates }
    : TEMPLATE_CATEGORIES.reduce((acc, cat) => {
        acc[cat.id] = getTemplatesByCategory(cat.id)
        return acc
      }, {} as Record<string, AgentTemplate[]>)

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-red-50 to-pink-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Choose a Template</h2>
              <p className="text-sm text-gray-600">Start with a pre-configured agent template</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/80 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Search and Filters */}
        <div className="px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-4">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  setSelectedCategory(null)
                }}
                placeholder="Search templates..."
                className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent text-sm"
              />
            </div>

            {/* Category Filters */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setSelectedCategory(null)
                  setSearchQuery('')
                }}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  !selectedCategory && !searchQuery
                    ? 'bg-red-100 text-red-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                All
              </button>
              {TEMPLATE_CATEGORIES.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => {
                    setSelectedCategory(cat.id)
                    setSearchQuery('')
                  }}
                  className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
                    selectedCategory === cat.id
                      ? 'bg-red-100 text-red-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <span>{cat.icon}</span>
                  {cat.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Templates Grid */}
        <div className="flex-1 overflow-y-auto p-6">
          {Object.entries(groupedTemplates).map(([category, templates]) => {
            if (templates.length === 0) return null
            const categoryInfo = TEMPLATE_CATEGORIES.find(c => c.id === category)

            return (
              <div key={category} className="mb-8 last:mb-0">
                {!searchQuery && (
                  <div className="flex items-center gap-2 mb-4">
                    <span className="text-xl">{categoryInfo?.icon}</span>
                    <h3 className="text-base font-semibold text-gray-900">{categoryInfo?.name || category}</h3>
                    <span className="text-sm text-gray-500">({templates.length})</span>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {templates.map((template) => (
                    <button
                      key={template.id}
                      onClick={() => onSelect(template)}
                      onMouseEnter={() => setHoveredTemplate(template.id)}
                      onMouseLeave={() => setHoveredTemplate(null)}
                      className={`relative text-left p-4 rounded-xl border-2 transition-all ${
                        hoveredTemplate === template.id
                          ? 'border-red-400 bg-red-50 shadow-md'
                          : 'border-gray-200 hover:border-gray-300 bg-white'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`w-10 h-10 ${template.color} rounded-lg flex items-center justify-center text-white text-lg flex-shrink-0`}>
                          {template.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-gray-900 text-sm">{template.name}</h4>
                          <p className="text-xs text-gray-500 mt-1 line-clamp-2">{template.description}</p>
                        </div>
                      </div>

                      {/* Tags */}
                      <div className="flex flex-wrap gap-1 mt-3">
                        {template.tags.slice(0, 3).map((tag) => (
                          <span
                            key={tag}
                            className="px-2 py-0.5 bg-gray-100 text-gray-600 text-[10px] rounded-full"
                          >
                            {tag}
                          </span>
                        ))}
                        {template.tags.length > 3 && (
                          <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-[10px] rounded-full">
                            +{template.tags.length - 3}
                          </span>
                        )}
                      </div>

                      {/* Hover indicator */}
                      {hoveredTemplate === template.id && (
                        <div className="absolute top-2 right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
                          <Check className="w-4 h-4 text-white" />
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )
          })}

          {filteredTemplates.length === 0 && (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Search className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No templates found</h3>
              <p className="text-gray-500">Try a different search term or category</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {AGENT_TEMPLATES.length} templates available
          </p>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Start from scratch instead
          </button>
        </div>
      </div>
    </div>
  )
}
