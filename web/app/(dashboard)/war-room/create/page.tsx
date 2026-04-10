'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { ArrowLeft, Plus, X, Users, Zap, Globe, ExternalLink, Info, GitPullRequest, FileCode, ChevronDown, ChevronUp, AlertTriangle, Loader2, Link } from 'lucide-react'
import toast from 'react-hot-toast'
import { createDebate, updateDebate, getDebate, getDebateTemplates, fetchPRInfo } from '@/lib/api/war-room'
import { apiClient } from '@/lib/api/client'
import type { DebateTemplate, DebateContext, PRInfo } from '@/lib/api/war-room'

interface AgentOption {
  id: string
  agent_name: string
}

interface ParticipantRow {
  agent_id: string
  role: string
}

export default function CreateDebatePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const editId = searchParams.get('edit')
  const isEditMode = !!editId

  const [templates, setTemplates] = useState<DebateTemplate[]>([])
  const [agents, setAgents] = useState<AgentOption[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingData, setLoadingData] = useState(!!editId)

  const [topic, setTopic] = useState('')
  const [debateType, setDebateType] = useState<'structured' | 'freeform'>('structured')
  const [rounds, setRounds] = useState(3)
  const [participants, setParticipants] = useState<ParticipantRow[]>([
    { agent_id: '', role: '' },
    { agent_id: '', role: '' },
  ])
  const [synthesizerAgentId, setSynthesizerAgentId] = useState('')
  const [isPublic, setIsPublic] = useState(false)
  const [allowExternal, setAllowExternal] = useState(false)
  const [contextType, setContextType] = useState<'none' | 'github_pr' | 'text'>('none')
  const [prUrl, setPrUrl] = useState('')
  const [prInfo, setPrInfo] = useState<PRInfo | null>(null)
  const [prLoading, setPrLoading] = useState(false)
  const [prError, setPrError] = useState<string | null>(null)
  const [textContext, setTextContext] = useState('')
  const [showDiff, setShowDiff] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const [tmpl, agentData] = await Promise.all([
          getDebateTemplates(),
          apiClient.getAgents(1, 100),
        ])
        setTemplates(tmpl.templates || [])
        setAgents((agentData.agents_list || agentData.agents || []).map((a: any) => ({
          id: a.id,
          agent_name: a.agent_name,
        })))

        // Load existing debate data for edit mode
        if (editId) {
          try {
            const debate = await getDebate(editId)
            setTopic(debate.topic)
            setDebateType(debate.debate_type as 'structured' | 'freeform')
            setRounds(debate.rounds)
            setIsPublic(debate.is_public)
            setAllowExternal(debate.allow_external)
            if (debate.participants.length > 0) {
              setParticipants(
                debate.participants
                  .filter((p) => !p.is_external)
                  .map((p) => ({
                    agent_id: p.agent_id || '',
                    role: p.role || '',
                  }))
              )
            }
            // Restore context if present
            const ctx = debate.debate_metadata?.context
            if (ctx?.type === 'github_pr') {
              setContextType('github_pr')
              setPrUrl(ctx.github_url || '')
              setPrInfo({
                repo_full_name: ctx.repo_full_name || '',
                pr_number: ctx.pr_number || 0,
                pr_title: ctx.pr_title || '',
                pr_description: ctx.pr_description || '',
                pr_author: ctx.pr_author || '',
                pr_base_branch: ctx.pr_base_branch || '',
                pr_head_branch: ctx.pr_head_branch || '',
                pr_diff: ctx.pr_diff || '',
                pr_files_changed: ctx.pr_files_changed || [],
                additions: 0,
                deletions: 0,
                changed_files: ctx.pr_files_changed?.length || 0,
                state: '',
                mergeable: null,
                html_url: ctx.github_url || '',
              })
            } else if (ctx?.type === 'text') {
              setContextType('text')
              setTextContext(ctx.text || '')
            }
          } catch (err) {
            console.error('Failed to load debate:', err)
            toast.error('Failed to load debate for editing')
            router.push('/war-room')
          } finally {
            setLoadingData(false)
          }
        }
      } catch (err) {
        console.error('Failed to load:', err)
      }
    }
    load()
  }, [editId, router])

  const applyTemplate = (template: DebateTemplate) => {
    setTopic(template.topic_template.replace('{topic}', ''))
    const newParticipants = template.suggested_roles.map((role) => ({
      agent_id: '',
      role,
    }))
    setParticipants(newParticipants.length >= 2 ? newParticipants : [...newParticipants, { agent_id: '', role: '' }])
    // Set context type if template specifies it
    if (template.context_type === 'github_pr') {
      setContextType('github_pr')
    }
    toast.success(`Template "${template.name}" applied!`)
  }

  const handleFetchPR = async () => {
    if (!prUrl.trim()) return
    setPrLoading(true)
    setPrError(null)
    try {
      const info = await fetchPRInfo(prUrl.trim())
      setPrInfo(info)
      // Auto-set topic if empty
      if (!topic) {
        setTopic(`Review PR #${info.pr_number}: ${info.pr_title}`)
      }
    } catch (err) {
      setPrError(err instanceof Error ? err.message : 'Failed to fetch PR info')
      setPrInfo(null)
    } finally {
      setPrLoading(false)
    }
  }

  const addParticipant = () => {
    if (participants.length >= 8) return
    setParticipants([...participants, { agent_id: '', role: '' }])
  }

  const removeParticipant = (index: number) => {
    if (participants.length <= 2) return
    setParticipants(participants.filter((_, i) => i !== index))
  }

  const updateParticipant = (index: number, field: keyof ParticipantRow, value: string) => {
    const updated = [...participants]
    updated[index] = { ...updated[index], [field]: value }
    setParticipants(updated)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!topic.trim() || participants.some((p) => !p.agent_id)) return

    setLoading(true)
    try {
      // Build context
      let context: DebateContext | undefined
      if (contextType === 'github_pr' && prInfo) {
        context = {
          type: 'github_pr',
          github_url: prUrl,
          repo_full_name: prInfo.repo_full_name,
          pr_number: prInfo.pr_number,
          pr_title: prInfo.pr_title,
          pr_description: prInfo.pr_description,
          pr_diff: prInfo.pr_diff,
          pr_files_changed: prInfo.pr_files_changed,
          pr_author: prInfo.pr_author,
          pr_base_branch: prInfo.pr_base_branch,
          pr_head_branch: prInfo.pr_head_branch,
        }
      } else if (contextType === 'text' && textContext.trim()) {
        context = { type: 'text', text: textContext.trim() }
      }

      const payload = {
        topic: topic.trim(),
        debate_type: debateType,
        rounds,
        participants: participants.map((p) => ({
          agent_id: p.agent_id,
          role: p.role || undefined,
        })),
        synthesizer_agent_id: synthesizerAgentId || undefined,
        is_public: isPublic,
        allow_external: allowExternal,
        context,
      }

      if (isEditMode && editId) {
        const debate = await updateDebate(editId, payload)
        toast.success('Debate updated!')
        router.push(`/war-room/${debate.id}`)
      } else {
        const debate = await createDebate(payload)
        toast.success('Debate created!')
        router.push(`/war-room/${debate.id}`)
      }
    } catch (err) {
      console.error(`Failed to ${isEditMode ? 'update' : 'create'} debate:`, err)
      toast.error(`Failed to ${isEditMode ? 'update' : 'create'} debate`)
    } finally {
      setLoading(false)
    }
  }

  if (loadingData) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
        {/* Back button */}
        <button
          onClick={() => router.push('/war-room')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors mb-4"
        >
          <ArrowLeft size={18} />
          <span className="text-sm font-medium">Back to War Room</span>
        </button>
        {/* Templates (hidden in edit mode) */}
        {!isEditMode && templates.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-8">
            <div className="mb-4">
              <p className="text-xs font-semibold text-red-600 uppercase tracking-wide">Quick Start</p>
              <h2 className="text-lg font-bold text-gray-900">Choose a Template</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {templates.map((t) => (
                <button
                  key={t.id}
                  onClick={() => applyTemplate(t)}
                  className="relative p-4 rounded-lg border-2 border-gray-200 hover:border-red-300 hover:shadow-md bg-white transition-all text-left"
                >
                  <Zap className="w-5 h-5 mb-2 text-gray-400" />
                  <div className="font-bold text-sm text-gray-900">{t.name}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{t.description}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Main Form Card */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-4 md:p-8">
              {/* Section Header */}
              <div className="mb-8">
                <h1 className="text-3xl font-extrabold text-gray-900 mb-3">
                  {isEditMode ? 'Edit Debate' : 'Create a Debate'}
                </h1>
                <p className="text-lg text-gray-600">
                  {isEditMode
                    ? 'Update the debate topic, participants, and settings before starting.'
                    : 'Set up a multi-agent debate where AI agents argue different perspectives on a topic.'}
                </p>
              </div>

              <div className="space-y-8">
                {/* Topic */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-bold text-gray-900">
                      Debate Topic *
                    </label>
                    <span className={`text-xs font-medium ${topic.length > 200 ? 'text-red-500' : 'text-gray-400'}`}>
                      {topic.length}/200
                    </span>
                  </div>
                  <textarea
                    value={topic}
                    onChange={(e) => setTopic(e.target.value.slice(0, 200))}
                    placeholder="e.g., Should we adopt microservices or stay with a monolith?"
                    rows={3}
                    className="w-full px-5 py-4 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-all bg-white text-base resize-none placeholder-gray-400"
                    required
                  />
                  <p className="mt-2 text-sm text-gray-500 flex items-center gap-2">
                    <Info size={14} className="text-gray-400" />
                    Be specific for better debate quality
                  </p>
                </div>

                {/* Context */}
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-3">
                    Context (Optional)
                  </label>
                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <button
                      type="button"
                      onClick={() => { setContextType('none'); setPrInfo(null); setPrError(null) }}
                      className={`p-3 rounded-lg border-2 text-left transition-all ${
                        contextType === 'none'
                          ? 'border-red-500 bg-red-50 shadow-lg shadow-red-500/20'
                          : 'border-gray-200 hover:border-red-300 bg-white'
                      }`}
                    >
                      <div className={`font-bold text-sm ${contextType === 'none' ? 'text-red-900' : 'text-gray-900'}`}>
                        No Context
                      </div>
                      <div className="text-xs text-gray-500">Topic only</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setContextType('github_pr')}
                      className={`p-3 rounded-lg border-2 text-left transition-all ${
                        contextType === 'github_pr'
                          ? 'border-red-500 bg-red-50 shadow-lg shadow-red-500/20'
                          : 'border-gray-200 hover:border-red-300 bg-white'
                      }`}
                    >
                      <GitPullRequest className={`w-5 h-5 mb-1 ${contextType === 'github_pr' ? 'text-red-600' : 'text-gray-400'}`} />
                      <div className={`font-bold text-sm ${contextType === 'github_pr' ? 'text-red-900' : 'text-gray-900'}`}>
                        GitHub PR
                      </div>
                      <div className="text-xs text-gray-500">Review a pull request</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setContextType('text')}
                      className={`p-3 rounded-lg border-2 text-left transition-all ${
                        contextType === 'text'
                          ? 'border-red-500 bg-red-50 shadow-lg shadow-red-500/20'
                          : 'border-gray-200 hover:border-red-300 bg-white'
                      }`}
                    >
                      <FileCode className={`w-5 h-5 mb-1 ${contextType === 'text' ? 'text-red-600' : 'text-gray-400'}`} />
                      <div className={`font-bold text-sm ${contextType === 'text' ? 'text-red-900' : 'text-gray-900'}`}>
                        Custom Text
                      </div>
                      <div className="text-xs text-gray-500">Paste any context</div>
                    </button>
                  </div>

                  {/* GitHub PR Input */}
                  {contextType === 'github_pr' && (
                    <div className="space-y-3">
                      <div className="flex gap-2">
                        <div className="flex-1 relative">
                          <Link className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                          <input
                            type="url"
                            value={prUrl}
                            onChange={(e) => setPrUrl(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleFetchPR())}
                            placeholder="https://github.com/owner/repo/pull/123"
                            className="w-full pl-10 pr-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-all"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={handleFetchPR}
                          disabled={prLoading || !prUrl.trim()}
                          className="px-5 py-3 bg-gradient-to-r from-red-500 to-red-600 text-white text-sm font-medium rounded-xl hover:from-red-600 hover:to-red-700 transition-all disabled:opacity-50 flex items-center gap-2"
                        >
                          {prLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitPullRequest className="w-4 h-4" />}
                          Fetch
                        </button>
                      </div>

                      {prError && (
                        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                          {prError}
                        </div>
                      )}

                      {prInfo && (
                        <div className="border-2 border-green-200 bg-green-50/50 rounded-xl p-4 space-y-3">
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <GitPullRequest className="w-4 h-4 text-green-600" />
                                <span className="text-sm font-bold text-gray-900">
                                  #{prInfo.pr_number} {prInfo.pr_title}
                                </span>
                              </div>
                              <div className="flex items-center gap-3 text-xs text-gray-500">
                                <span>{prInfo.repo_full_name}</span>
                                <span>by {prInfo.pr_author}</span>
                                <span>{prInfo.pr_head_branch} → {prInfo.pr_base_branch}</span>
                              </div>
                            </div>
                            <a
                              href={prInfo.html_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-red-600 hover:text-red-700 font-medium"
                            >
                              View on GitHub
                            </a>
                          </div>

                          <div className="flex items-center gap-4 text-xs">
                            <span className="px-2 py-1 bg-green-100 text-green-800 rounded-md font-medium">
                              +{prInfo.additions}
                            </span>
                            <span className="px-2 py-1 bg-red-100 text-red-800 rounded-md font-medium">
                              -{prInfo.deletions}
                            </span>
                            <span className="text-gray-500">{prInfo.changed_files} files changed</span>
                          </div>

                          {prInfo.pr_files_changed.length > 0 && (
                            <div>
                              <p className="text-xs font-semibold text-gray-600 mb-1">Files:</p>
                              <div className="flex flex-wrap gap-1">
                                {prInfo.pr_files_changed.slice(0, 10).map((f) => (
                                  <span key={f} className="text-[11px] px-2 py-0.5 bg-white border border-gray-200 rounded text-gray-600 font-mono">
                                    {f.split('/').pop()}
                                  </span>
                                ))}
                                {prInfo.pr_files_changed.length > 10 && (
                                  <span className="text-[11px] text-gray-400">
                                    +{prInfo.pr_files_changed.length - 10} more
                                  </span>
                                )}
                              </div>
                            </div>
                          )}

                          {prInfo.pr_diff && (
                            <div>
                              <button
                                type="button"
                                onClick={() => setShowDiff(!showDiff)}
                                className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 font-medium"
                              >
                                {showDiff ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                                {showDiff ? 'Hide' : 'Show'} diff preview
                              </button>
                              {showDiff && (
                                <pre className="mt-2 p-3 bg-gray-900 text-gray-300 text-[11px] rounded-lg overflow-x-auto max-h-64 overflow-y-auto font-mono leading-relaxed">
                                  {prInfo.pr_diff.slice(0, 5000)}
                                  {prInfo.pr_diff.length > 5000 && '\n\n... (truncated for preview)'}
                                </pre>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Text Context Input */}
                  {contextType === 'text' && (
                    <textarea
                      value={textContext}
                      onChange={(e) => setTextContext(e.target.value)}
                      placeholder="Paste any context here — code snippets, documents, requirements, etc."
                      rows={6}
                      className="w-full px-5 py-4 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-all bg-white text-sm resize-none placeholder-gray-400 font-mono"
                    />
                  )}
                </div>

                {/* Type & Rounds */}
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-3">
                    Debate Format
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    {/* Debate Type Cards */}
                    <button
                      type="button"
                      onClick={() => setDebateType('structured')}
                      className={`relative p-4 rounded-2xl border-2 transition-all text-left ${
                        debateType === 'structured'
                          ? 'border-red-500 bg-red-50 shadow-lg shadow-red-500/20'
                          : 'border-gray-200 hover:border-red-300 hover:shadow-md bg-white'
                      }`}
                    >
                      <Users className={`w-6 h-6 mb-2 ${debateType === 'structured' ? 'text-red-600' : 'text-gray-400'}`} />
                      <div className={`font-bold text-sm ${debateType === 'structured' ? 'text-red-900' : 'text-gray-900'}`}>
                        Structured
                      </div>
                      <div className="text-xs text-gray-500">Fixed rounds, each agent speaks in order</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setDebateType('freeform')}
                      className={`relative p-4 rounded-2xl border-2 transition-all text-left ${
                        debateType === 'freeform'
                          ? 'border-red-500 bg-red-50 shadow-lg shadow-red-500/20'
                          : 'border-gray-200 hover:border-red-300 hover:shadow-md bg-white'
                      }`}
                    >
                      <Zap className={`w-6 h-6 mb-2 ${debateType === 'freeform' ? 'text-red-600' : 'text-gray-400'}`} />
                      <div className={`font-bold text-sm ${debateType === 'freeform' ? 'text-red-900' : 'text-gray-900'}`}>
                        Freeform
                      </div>
                      <div className="text-xs text-gray-500">Open discussion, agents respond freely</div>
                    </button>
                  </div>
                </div>

                {/* Rounds Slider */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-bold text-gray-900">
                      Number of Rounds
                    </label>
                    <span className="text-sm font-bold text-red-600">{rounds}</span>
                  </div>
                  <input
                    type="range"
                    value={rounds}
                    onChange={(e) => setRounds(parseInt(e.target.value))}
                    min={1}
                    max={10}
                    className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer accent-red-500"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>1</span>
                    <span>5</span>
                    <span>10</span>
                  </div>
                </div>

                {/* Participants */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <label className="block text-sm font-bold text-gray-900">
                      Participants *
                    </label>
                    {participants.length < 8 && (
                      <button
                        type="button"
                        onClick={addParticipant}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors font-medium"
                      >
                        <Plus size={16} />
                        Add Participant
                      </button>
                    )}
                  </div>
                  <div className="space-y-3">
                    {participants.map((p, i) => (
                      <div key={i} className="flex items-center gap-3 p-4 bg-gray-50 rounded-xl border border-gray-200">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                          {i + 1}
                        </div>
                        <select
                          value={p.agent_id}
                          onChange={(e) => updateParticipant(i, 'agent_id', e.target.value)}
                          className="flex-1 px-4 py-3 bg-white border-2 border-gray-200 rounded-xl text-sm text-gray-900 font-medium focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-all"
                          required
                        >
                          <option value="">Select agent...</option>
                          {agents.map((a) => (
                            <option key={a.id} value={a.id}>{a.agent_name}</option>
                          ))}
                        </select>
                        <input
                          type="text"
                          value={p.role}
                          onChange={(e) => updateParticipant(i, 'role', e.target.value)}
                          placeholder="Role (e.g., Advocate, Critic)"
                          className="w-48 px-4 py-3 bg-white border-2 border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 font-medium focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-all"
                        />
                        {participants.length > 2 && (
                          <button
                            type="button"
                            onClick={() => removeParticipant(i)}
                            className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <X size={18} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Synthesizer */}
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-2">
                    Verdict Synthesizer
                  </label>
                  <select
                    value={synthesizerAgentId}
                    onChange={(e) => setSynthesizerAgentId(e.target.value)}
                    className="w-full px-5 py-4 bg-white border-2 border-gray-200 rounded-xl text-base text-gray-900 font-medium focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-all"
                  >
                    <option value="">No synthesizer (optional)</option>
                    {agents.map((a) => (
                      <option key={a.id} value={a.id}>{a.agent_name}</option>
                    ))}
                  </select>
                  <p className="mt-2 text-sm text-gray-500 flex items-center gap-2">
                    <Info size={14} className="text-gray-400" />
                    This agent will analyze all arguments and deliver the final verdict
                  </p>
                </div>

                {/* Options */}
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-3">
                    Options
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setIsPublic(!isPublic)}
                      className={`relative p-4 rounded-2xl border-2 transition-all text-left ${
                        isPublic
                          ? 'border-red-500 bg-red-50 shadow-lg shadow-red-500/20'
                          : 'border-gray-200 hover:border-red-300 hover:shadow-md bg-white'
                      }`}
                    >
                      <Globe className={`w-6 h-6 mb-2 ${isPublic ? 'text-red-600' : 'text-gray-400'}`} />
                      <div className={`font-bold text-sm ${isPublic ? 'text-red-900' : 'text-gray-900'}`}>
                        Public Debate
                      </div>
                      <div className="text-xs text-gray-500">Generate a shareable link anyone can watch</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setAllowExternal(!allowExternal)}
                      className={`relative p-4 rounded-2xl border-2 transition-all text-left ${
                        allowExternal
                          ? 'border-red-500 bg-red-50 shadow-lg shadow-red-500/20'
                          : 'border-gray-200 hover:border-red-300 hover:shadow-md bg-white'
                      }`}
                    >
                      <ExternalLink className={`w-6 h-6 mb-2 ${allowExternal ? 'text-red-600' : 'text-gray-400'}`} />
                      <div className={`font-bold text-sm ${allowExternal ? 'text-red-900' : 'text-gray-900'}`}>
                        External Agents
                      </div>
                      <div className="text-xs text-gray-500">Allow any external agent to join via API</div>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-gray-200 px-8 py-4 bg-gray-50 flex items-center justify-between">
              <div />
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => router.push('/war-room')}
                  className="px-5 py-2.5 text-gray-600 hover:text-gray-900 font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !topic.trim() || participants.some((p) => !p.agent_id)}
                  className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      {isEditMode ? 'Saving...' : 'Creating...'}
                    </>
                  ) : (
                    isEditMode ? 'Save Changes' : 'Create Debate'
                  )}
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
