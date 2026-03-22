'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/ErrorAlert'
import { apiClient } from '@/lib/api/client'

interface KnowledgeBase {
  id: number
  name: string
}

interface OAuthApp {
  id: number
  app_name: string
  provider: string
  client_id: string
  is_active: boolean
  is_default: boolean
}

const SOURCE_TYPES = [
  {
    value: 'SLACK',
    label: 'Slack',
    description: 'Sync messages, threads, and files from Slack channels',
    icon: '💬',
    color: 'bg-purple-100 text-purple-800',
  },
  {
    value: 'GMAIL',
    label: 'Gmail',
    description: 'Sync emails from Gmail using labels and filters',
    icon: '📧',
    color: 'bg-red-100 text-red-800',
  },
  {
    value: 'GITHUB',
    label: 'GitHub',
    description: 'Sync repositories, issues, pull requests, and discussions',
    icon: '🐙',
    color: 'bg-gray-100 text-gray-800',
  },
]

function ConnectDataSourceContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const kbIdParam = searchParams.get('kb_id')

  const [step, setStep] = useState<'select-type' | 'select-kb' | 'configure'>('select-type')
  const [selectedType, setSelectedType] = useState<string>('')
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [selectedKbId, setSelectedKbId] = useState<number | null>(kbIdParam ? parseInt(kbIdParam) : null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dataSourceName, setDataSourceName] = useState<string>('')
  const [oauthApps, setOauthApps] = useState<OAuthApp[]>([])
  const [selectedOAuthAppId, setSelectedOAuthAppId] = useState<number | null>(null)
  const [checkingOAuth, setCheckingOAuth] = useState(false)
  const [repositories, setRepositories] = useState<any[]>([])
  const [loadingRepos, setLoadingRepos] = useState(false)
  const [selectedRepos, setSelectedRepos] = useState<Set<string>>(new Set())

  // Slack config
  const [slackConfig, setSlackConfig] = useState({
    channels: '',
    sync_frequency: 3600,
    include_threads: true,
    include_files: true,
  })

  // Gmail config
  const [gmailConfig, setGmailConfig] = useState({
    labels: '',
    query: '',
    sync_frequency: 3600,
  })

  // GitHub config
  const [githubConfig, setGithubConfig] = useState({
    repositories: '',
    sync_frequency: 3600,
    include_issues: true,
    include_pull_requests: true,
    include_discussions: false,
    create_wiki: false,
  })

  useEffect(() => {
    fetchKnowledgeBases()
    if (kbIdParam) {
      setStep('select-type')
    }
  }, [])

  const fetchKnowledgeBases = async () => {
    try {
      const data = await apiClient.getKnowledgeBases()
      setKnowledgeBases(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch knowledge bases:', err)
    }
  }

  const fetchOAuthApps = async (provider: string) => {
    setCheckingOAuth(true)
    try {
      const data = await apiClient.getOAuthApps(provider)
      const apps = Array.isArray(data) ? data : []
      setOauthApps(apps)
      
      // Auto-select if only one app
      if (apps.length === 1) {
        setSelectedOAuthAppId(apps[0].id)
      }
      
      return apps.length > 0
    } catch (err) {
      console.error('Failed to fetch OAuth apps:', err)
      return false
    } finally {
      setCheckingOAuth(false)
    }
  }

  const fetchGitHubRepositories = async (oauthAppId: number) => {
    setLoadingRepos(true)
    setError(null)
    try {
      const data = await apiClient.getGitHubRepositories(oauthAppId)
      setRepositories(data.repositories || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch repositories')
      setRepositories([])
    } finally {
      setLoadingRepos(false)
    }
  }

  const handleOAuthAppChange = async (appId: number) => {
    setSelectedOAuthAppId(appId)
    setRepositories([])
    setSelectedRepos(new Set())
    
    if (selectedType === 'GITHUB' && appId) {
      await fetchGitHubRepositories(appId)
    }
  }

  const toggleRepository = (repoFullName: string) => {
    const newSelected = new Set(selectedRepos)
    if (newSelected.has(repoFullName)) {
      newSelected.delete(repoFullName)
    } else {
      newSelected.add(repoFullName)
    }
    setSelectedRepos(newSelected)
    
    // Update the repositories config
    setGithubConfig({
      ...githubConfig,
      repositories: Array.from(newSelected).join(', ')
    })
  }

  const toggleAllRepositories = () => {
    if (selectedRepos.size === repositories.length) {
      setSelectedRepos(new Set())
      setGithubConfig({ ...githubConfig, repositories: '' })
    } else {
      const allRepos = new Set(repositories.map(r => r.full_name))
      setSelectedRepos(allRepos)
      setGithubConfig({ ...githubConfig, repositories: Array.from(allRepos).join(', ') })
    }
  }

  const handleTypeSelect = async (type: string) => {
    setSelectedType(type)
    // Set default name based on type
    const defaultName = `${type.charAt(0).toUpperCase() + type.slice(1)} Data Source`
    setDataSourceName(defaultName)
    
    if (selectedKbId) {
      // Check OAuth apps before proceeding
      const hasOAuthApps = await fetchOAuthApps(type)
      if (hasOAuthApps) {
        setStep('configure')
      }
    } else {
      setStep('select-kb')
    }
  }

  const handleKbSelect = async (kbId: number) => {
    setSelectedKbId(kbId)
    // Check OAuth apps before proceeding
    const hasOAuthApps = await fetchOAuthApps(selectedType)
    if (hasOAuthApps) {
      setStep('configure')
    }
  }

  const handleConnect = async () => {
    if (!selectedType || !selectedKbId || !dataSourceName.trim()) {
      setError('Please provide a name for the data source')
      return
    }

    if (!selectedOAuthAppId) {
      setError('Please select an OAuth app')
      return
    }

    setLoading(true)
    setError(null)

    try {
      let sourceConfig
      if (selectedType === 'SLACK') {
        sourceConfig = slackConfig
      } else if (selectedType === 'GMAIL') {
        sourceConfig = gmailConfig
      } else if (selectedType === 'GITHUB') {
        sourceConfig = githubConfig
      }
      
      // Create data source with selected OAuth app
      await apiClient.createDataSource({
        name: dataSourceName.trim(),
        type: selectedType,
        knowledge_base_id: selectedKbId,
        config: sourceConfig,
        oauth_app_id: selectedOAuthAppId,
      })

      // Redirect back to data sources list
      router.push('/data-sources')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 via-red-50/30 to-red-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header - More Compact */}
        <div className="mb-6">
          <Link
            href="/data-sources"
            className="inline-flex items-center gap-2 text-red-600 hover:text-red-700 font-medium mb-3 transition-colors text-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Data Sources
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Connect Data Source</h1>
          <p className="text-gray-600 mt-1 text-sm">
            Connect a data source to sync documents to your knowledge base
          </p>
        </div>

        {/* Progress Steps - More Compact */}
        <div className="mb-6 bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-center">
            <div className="flex items-center">
              <div className={`flex items-center justify-center w-9 h-9 rounded-full text-sm font-semibold ${step === 'select-type' ? 'bg-gradient-to-r from-red-500 to-red-600 text-white shadow-sm' : 'bg-red-100 text-red-600'}`}>
                1
              </div>
              <div className={`w-20 h-1 ${step !== 'select-type' ? 'bg-gradient-to-r from-red-500 to-red-600' : 'bg-gray-200'}`}></div>
              <div className={`flex items-center justify-center w-9 h-9 rounded-full text-sm font-semibold ${step === 'select-kb' ? 'bg-gradient-to-r from-red-500 to-red-600 text-white shadow-sm' : step === 'configure' ? 'bg-red-100 text-red-600' : 'bg-gray-200 text-gray-400'}`}>
                2
              </div>
              <div className={`w-20 h-1 ${step === 'configure' ? 'bg-gradient-to-r from-red-500 to-red-600' : 'bg-gray-200'}`}></div>
              <div className={`flex items-center justify-center w-9 h-9 rounded-full text-sm font-semibold ${step === 'configure' ? 'bg-gradient-to-r from-red-500 to-red-600 text-white shadow-sm' : 'bg-gray-200 text-gray-400'}`}>
                3
              </div>
            </div>
          </div>
          <div className="flex justify-center mt-2.5 text-xs text-gray-600">
            <span className="w-28 text-center font-medium">Select Type</span>
            <span className="w-28 text-center font-medium">Select KB</span>
            <span className="w-28 text-center font-medium">Configure</span>
          </div>
        </div>

        {error && (
          <div className="mb-5">
            <ErrorAlert message={error} onDismiss={() => setError(null)} />
          </div>
        )}

        {/* Step 1: Select Source Type */}
        {step === 'select-type' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Select Data Source Type</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {SOURCE_TYPES.map((type) => (
                <button
                  key={type.value}
                  onClick={() => handleTypeSelect(type.value)}
                  className="bg-white rounded-lg border-2 border-gray-200 p-5 hover:border-red-400 hover:shadow-md transition-all text-left"
                >
                  <div className="flex items-start gap-3.5">
                    <div className="text-3xl">{type.icon}</div>
                    <div className="flex-1">
                      <h3 className="text-base font-semibold text-gray-900 mb-1">{type.label}</h3>
                      <p className="text-sm text-gray-600 mb-2">{type.description}</p>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${type.color}`}>
                        OAuth Required
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Select Knowledge Base */}
        {step === 'select-kb' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Select Knowledge Base</h2>
              <button
                onClick={() => setStep('select-type')}
                className="text-sm text-red-600 hover:text-red-700 font-medium"
              >
                ← Back
              </button>
            </div>
            <div className="grid grid-cols-1 gap-3">
              {knowledgeBases.map((kb) => (
                <button
                  key={kb.id}
                  onClick={() => handleKbSelect(kb.id)}
                  className="bg-white rounded-lg border-2 border-gray-200 p-4 hover:border-red-400 hover:shadow-md transition-all text-left"
                >
                  <h3 className="text-base font-semibold text-gray-900">{kb.name}</h3>
                </button>
              ))}
            </div>
            {knowledgeBases.length === 0 && (
              <div className="text-center py-8 bg-white rounded-lg border border-gray-200 text-gray-500">
                <p className="mb-2">No knowledge bases found.</p>
                <Link
                  href="/knowledge-bases/create"
                  className="text-red-600 hover:text-red-700 font-medium inline-block"
                >
                  Create a knowledge base first
                </Link>
              </div>
            )}
          </div>
        )}

        {/* Checking OAuth Apps Loading */}
        {checkingOAuth && (
          <div className="flex flex-col items-center justify-center py-12">
            <LoadingSpinner />
            <p className="text-gray-600 mt-4">Checking OAuth configuration...</p>
          </div>
        )}

        {/* No OAuth Apps Warning */}
        {!checkingOAuth && oauthApps.length === 0 && (selectedType && selectedKbId) && (
          <div className="bg-yellow-50 border-l-4 border-yellow-400 rounded-lg p-6">
            <div className="flex items-start gap-4">
              <svg className="w-6 h-6 text-yellow-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-yellow-900 mb-2">
                  OAuth App Not Configured
                </h3>
                <p className="text-yellow-800 mb-4">
                  You need to configure a {selectedType === 'SLACK' ? 'Slack' : selectedType === 'GMAIL' ? 'Gmail' : 'GitHub'} OAuth app before you can connect this data source. 
                  OAuth apps allow Synkora to securely access your {selectedType === 'SLACK' ? 'Slack workspace' : selectedType === 'GMAIL' ? 'Gmail account' : 'GitHub repositories'} on your behalf.
                </p>
                <div className="bg-white rounded-lg border border-yellow-200 p-4 mb-4">
                  <h4 className="font-medium text-gray-900 mb-2">What you need to do:</h4>
                  <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700">
                    <li>Create a {selectedType === 'SLACK' ? 'Slack' : selectedType === 'GMAIL' ? 'Google' : 'GitHub'} OAuth app in their developer console</li>
                    <li>Configure the OAuth app with the required scopes and redirect URI</li>
                    <li>Add the OAuth app credentials to Synkora</li>
                    <li>Return here to connect your data source</li>
                  </ol>
                </div>
                <div className="flex gap-3">
                  <Link
                    href="/oauth-apps/create"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Configure OAuth App
                  </Link>
                  <button
                    onClick={() => setStep(selectedKbId ? 'select-type' : 'select-kb')}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                  >
                    Go Back
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Configure */}
        {!checkingOAuth && step === 'configure' && oauthApps.length > 0 && (
        <div className="space-y-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Configure {selectedType === 'SLACK' ? 'Slack' : selectedType === 'GMAIL' ? 'Gmail' : 'GitHub'}
            </h2>
            <button
              onClick={() => setStep(selectedKbId ? 'select-type' : 'select-kb')}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              ← Back
            </button>
          </div>

          {/* OAuth App Selection - Always show when there are OAuth apps */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select OAuth App <span className="text-red-500">*</span>
            </label>
            <select
              value={selectedOAuthAppId || ''}
              onChange={(e) => handleOAuthAppChange(parseInt(e.target.value))}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              required
            >
              <option value="">Choose an OAuth app...</option>
              {oauthApps.map((app) => (
                <option key={app.id} value={app.id}>
                  {app.app_name}
                </option>
              ))}
            </select>
            <p className="text-sm text-gray-500 mt-1">
              Select which {selectedType === 'SLACK' ? 'Slack' : selectedType === 'GMAIL' ? 'Gmail' : 'GitHub'} account to connect
            </p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Data Source Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={dataSourceName}
                onChange={(e) => setDataSourceName(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                placeholder={`e.g., My ${selectedType === 'SLACK' ? 'Slack' : 'Gmail'} Workspace`}
                required
              />
              <p className="text-sm text-gray-500 mt-1">
                Give this data source a descriptive name to identify it later
              </p>
            </div>

            {selectedType === 'SLACK' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Channels (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={slackConfig.channels}
                    onChange={(e) => setSlackConfig({ ...slackConfig, channels: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    placeholder="e.g., general, engineering, support"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Leave empty to sync all channels you have access to
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Sync Frequency (seconds)
                  </label>
                  <input
                    type="number"
                    value={slackConfig.sync_frequency}
                    onChange={(e) => setSlackConfig({ ...slackConfig, sync_frequency: parseInt(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    min="60"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    How often to check for new messages (minimum 60 seconds)
                  </p>
                </div>

                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={slackConfig.include_threads}
                      onChange={(e) => setSlackConfig({ ...slackConfig, include_threads: e.target.checked })}
                      className="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500"
                    />
                    <span className="text-sm text-gray-700">Include thread replies</span>
                  </label>

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={slackConfig.include_files}
                      onChange={(e) => setSlackConfig({ ...slackConfig, include_files: e.target.checked })}
                      className="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500"
                    />
                    <span className="text-sm text-gray-700">Include file attachments</span>
                  </label>
                </div>
              </div>
            )}

            {selectedType === 'GMAIL' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Labels (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={gmailConfig.labels}
                    onChange={(e) => setGmailConfig({ ...gmailConfig, labels: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    placeholder="e.g., INBOX, IMPORTANT"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Leave empty to sync all emails
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Search Query (optional)
                  </label>
                  <input
                    type="text"
                    value={gmailConfig.query}
                    onChange={(e) => setGmailConfig({ ...gmailConfig, query: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    placeholder="e.g., from:example@gmail.com"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Use Gmail search syntax to filter emails
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Sync Frequency (seconds)
                  </label>
                  <input
                    type="number"
                    value={gmailConfig.sync_frequency}
                    onChange={(e) => setGmailConfig({ ...gmailConfig, sync_frequency: parseInt(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    min="60"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    How often to check for new emails (minimum 60 seconds)
                  </p>
                </div>
              </div>
            )}

            {selectedType === 'GITHUB' && (
              <div className="space-y-4">
                {/* Repository Selection */}
                {selectedOAuthAppId && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="block text-sm font-medium text-gray-700">
                        Select Repositories
                      </label>
                      {repositories.length > 0 && (
                        <button
                          onClick={toggleAllRepositories}
                          className="text-sm text-red-600 hover:text-red-700"
                        >
                          {selectedRepos.size === repositories.length ? 'Deselect All' : 'Select All'}
                        </button>
                      )}
                    </div>
                    
                    {loadingRepos ? (
                      <div className="flex items-center justify-center py-8 border border-gray-200 rounded-lg">
                        <LoadingSpinner size="sm" />
                        <span className="ml-2 text-sm text-gray-600">Loading repositories...</span>
                      </div>
                    ) : repositories.length > 0 ? (
                      <div className="border border-gray-200 rounded-lg max-h-64 overflow-y-auto">
                        {repositories.map((repo) => (
                          <label
                            key={repo.id}
                            className="flex items-start gap-3 p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                          >
                            <input
                              type="checkbox"
                              checked={selectedRepos.has(repo.full_name)}
                              onChange={() => toggleRepository(repo.full_name)}
                              className="mt-1 w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-gray-900">{repo.full_name}</span>
                                {repo.private && (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                                    Private
                                  </span>
                                )}
                                {repo.has_wiki && (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                    Wiki
                                  </span>
                                )}
                              </div>
                              {repo.description && (
                                <p className="text-sm text-gray-500 mt-1 truncate">{repo.description}</p>
                              )}
                              <p className="text-xs text-gray-400 mt-1">
                                Updated: {new Date(repo.updated_at).toLocaleDateString()}
                              </p>
                            </div>
                          </label>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 border border-gray-200 rounded-lg text-gray-500">
                        <p>No repositories found for this account.</p>
                      </div>
                    )}
                    <p className="text-sm text-gray-500 mt-1">
                      {selectedRepos.size > 0 
                        ? `${selectedRepos.size} repositor${selectedRepos.size === 1 ? 'y' : 'ies'} selected`
                        : 'Select repositories to sync, or leave empty to sync all accessible repositories'}
                    </p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Sync Frequency (seconds)
                  </label>
                  <input
                    type="number"
                    value={githubConfig.sync_frequency}
                    onChange={(e) => setGithubConfig({ ...githubConfig, sync_frequency: parseInt(e.target.value) })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    min="60"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    How often to check for new content (minimum 60 seconds)
                  </p>
                </div>

                <div className="space-y-3">
                  <label className="block text-sm font-medium text-gray-700">
                    Content to Sync
                  </label>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={githubConfig.include_issues}
                        onChange={(e) => setGithubConfig({ ...githubConfig, include_issues: e.target.checked })}
                        className="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500"
                      />
                      <span className="text-sm text-gray-700">Include Issues</span>
                    </label>

                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={githubConfig.include_pull_requests}
                        onChange={(e) => setGithubConfig({ ...githubConfig, include_pull_requests: e.target.checked })}
                        className="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500"
                      />
                      <span className="text-sm text-gray-700">Include Pull Requests</span>
                    </label>

                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={githubConfig.include_discussions}
                        onChange={(e) => setGithubConfig({ ...githubConfig, include_discussions: e.target.checked })}
                        className="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500"
                      />
                      <span className="text-sm text-gray-700">Include Discussions</span>
                    </label>

                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={githubConfig.create_wiki}
                        onChange={(e) => setGithubConfig({ ...githubConfig, create_wiki: e.target.checked })}
                        className="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500"
                      />
                      <span className="text-sm text-gray-700">Create Repository Wiki</span>
                    </label>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    When enabled, a wiki will be created for each repository to document its structure and purpose
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <div>
                <p className="text-sm font-medium text-blue-900">Connect Data Source</p>
                <p className="text-sm text-blue-700 mt-1">
                  This will link your {selectedType === 'SLACK' ? 'Slack' : selectedType === 'GMAIL' ? 'Gmail' : 'GitHub'} data source to the selected knowledge base using the authorized OAuth app. 
                  The data source will start syncing based on your configured frequency.
                </p>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleConnect}
              disabled={loading}
              className="flex-1 px-5 py-2.5 text-sm font-medium bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-lg transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <LoadingSpinner size="sm" />
                  Connecting...
                </span>
              ) : (
                'Connect Data Source'
              )}
            </button>
            <Link
              href="/data-sources"
              className="px-5 py-2.5 text-sm font-medium border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-center"
            >
              Cancel
            </Link>
          </div>
        </div>
        )}
      </div>
    </div>
  )
}

export default function ConnectDataSourcePage() {
  return (
    <Suspense fallback={
      <div className="p-8 max-w-4xl mx-auto">
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
        </div>
      </div>
    }>
      <ConnectDataSourceContent />
    </Suspense>
  )
}
