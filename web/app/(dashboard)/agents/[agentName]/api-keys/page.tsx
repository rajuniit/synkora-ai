/**
 * Agent API Keys Management Page
 * Modern UI for managing API keys with green accent colors
 */

'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { ChevronRight } from 'lucide-react';
import { useAgentApiKeys } from '@/hooks/useAgentApiKeys';
import type { AgentApiKey, CreateApiKeyRequest } from '@/types/agent-api';

export default function AgentApiKeysPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
  
  const [agent, setAgent] = useState<any>(null);
  const [apiKeys, setApiKeys] = useState<AgentApiKey[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [activeTab, setActiveTab] = useState<'keys' | 'docs'>('keys');
  const [newKeyResponse, setNewKeyResponse] = useState<{ key: string; name: string } | null>(null);
  const [loadingAgent, setLoadingAgent] = useState(true);

  const {
    loading,
    getApiKeys,
    createApiKey,
    deleteApiKey,
    regenerateApiKey,
  } = useAgentApiKeys();

  useEffect(() => {
    const loadAgent = async () => {
      try {
        setLoadingAgent(true);
        const { apiClient } = await import('@/lib/api/client');
        const agentData = await apiClient.getAgent(agentName);
        setAgent(agentData);
        const keys = await getApiKeys({ agent_id: agentData.id });
        setApiKeys(keys);
      } catch (err: any) {
        console.error('Failed to load agent:', err);
        const detail = err?.response?.data?.detail;
        toast.error(typeof detail === 'string' ? detail : 'Failed to load agent');
      } finally {
        setLoadingAgent(false);
      }
    };

    loadAgent();
  }, [agentName, getApiKeys]);

  const loadApiKeys = async (agentId: string) => {
    const keys = await getApiKeys({ agent_id: agentId });
    setApiKeys(keys);
  };

  const handleCreateApiKey = async (data: CreateApiKeyRequest) => {
    if (!agent) return;
    const response = await createApiKey(data);
    if (response) {
      toast.success('API key created — copy it now, it won\'t be shown again');
      setNewKeyResponse({ key: response.api_key, name: data.key_name });
      setShowCreateForm(false);
      await loadApiKeys(agent.id);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    if (!agent) return;
    
    // Show confirmation toast with action buttons
    toast((t: { id: string }) => (
      <div className="flex flex-col gap-3">
        <p className="font-semibold text-gray-900">Delete API Key?</p>
        <p className="text-sm text-gray-600">This action cannot be undone.</p>
        <div className="flex gap-2">
          <button
            onClick={async () => {
              toast.dismiss(t.id);
              const success = await deleteApiKey(keyId);
              if (success) {
                await loadApiKeys(agent.id);
              }
            }}
            className="px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium"
          >
            Delete
          </button>
          <button
            onClick={() => toast.dismiss(t.id)}
            className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm font-medium"
          >
            Cancel
          </button>
        </div>
      </div>
    ), {
      duration: Infinity,
      position: 'top-center',
    });
  };

  const handleRegenerateKey = async (keyId: string) => {
    if (!agent) return;
    
    // Show confirmation toast with action buttons
    toast((t: { id: string }) => (
      <div className="flex flex-col gap-3">
        <p className="font-semibold text-gray-900">Regenerate API Key?</p>
        <p className="text-sm text-gray-600">The old key will stop working immediately.</p>
        <div className="flex gap-2">
          <button
            onClick={async () => {
              toast.dismiss(t.id);
              const response = await regenerateApiKey(keyId);
              if (response) {
                setNewKeyResponse({ key: response.api_key, name: response.key_name });
                await loadApiKeys(agent.id);
              }
            }}
            className="px-3 py-1.5 bg-orange-600 text-white rounded-lg hover:bg-orange-700 text-sm font-medium"
          >
            Regenerate
          </button>
          <button
            onClick={() => toast.dismiss(t.id)}
            className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm font-medium"
          >
            Cancel
          </button>
        </div>
      </div>
    ), {
      duration: Infinity,
      position: 'top-center',
    });
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  if (loadingAgent || (loading && apiKeys.length === 0)) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-red-200 border-t-red-600"></div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-600 text-sm">Failed to load agent</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Breadcrumb */}
        <div className="flex items-center gap-1.5 text-sm mb-4">
          <button
            onClick={() => router.push('/agents')}
            className="text-gray-500 hover:text-red-600 transition-colors"
          >
            Agents
          </button>
          <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
          <button
            onClick={() => router.push(`/agents/${encodeURIComponent(agentName)}/view`)}
            className="text-gray-500 hover:text-red-600 transition-colors"
          >
            {agentName}
          </button>
          <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
          <span className="text-gray-900 font-medium">API Keys</span>
        </div>

        {/* Header */}
        <div className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight mb-1">API Keys</h1>
              <p className="text-sm text-gray-600">
                Manage API keys for programmatic access to <span className="font-semibold text-red-600">{agentName}</span>
              </p>
            </div>
            {!showCreateForm && (
              <button
                onClick={() => setShowCreateForm(true)}
                className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all text-xs font-medium shadow-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Create API Key
              </button>
            )}
          </div>
        </div>

        {/* New Key Display */}
        {newKeyResponse && (
          <div className="mb-6 bg-gradient-to-r from-red-50 to-red-50 border-2 border-red-300 rounded-xl p-5 shadow-sm">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="text-base font-bold text-gray-900 mb-2">
                  🎉 Save Your API Key
                </h3>
                <p className="text-xs text-gray-700 mb-3">
                  Make sure to copy your API key now. You won't be able to see it again!
                </p>
                <div className="bg-white border-2 border-red-300 rounded-lg p-3 mb-3">
                  <div className="flex items-center justify-between gap-3">
                    <code className="text-xs font-mono text-gray-900 flex-1 break-all">{newKeyResponse.key}</code>
                    <button
                      onClick={() => copyToClipboard(newKeyResponse.key)}
                      className="flex-shrink-0 px-3 py-1.5 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-lg transition-all text-xs font-medium shadow-sm"
                    >
                      Copy
                    </button>
                  </div>
                </div>
                <button
                  onClick={() => setNewKeyResponse(null)}
                  className="text-gray-600 hover:text-gray-900 font-medium underline text-xs"
                >
                  I've saved my key ✓
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Create Form Modal */}
        {showCreateForm && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="sticky top-0 bg-red-50 border-b border-gray-200 px-6 py-4 rounded-t-xl">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-gray-900">Create New API Key</h2>
                  <button
                    onClick={() => setShowCreateForm(false)}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
              <div className="p-6">
                <ApiKeyForm
                  agentId={agent.id}
                  onSubmit={handleCreateApiKey}
                  onCancel={() => setShowCreateForm(false)}
                  isLoading={loading}
                />
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="mb-5">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-1 inline-flex">
            <nav className="flex gap-1">
              <button
                onClick={() => setActiveTab('keys')}
                className={`py-2 px-3 rounded-md font-medium text-xs transition-all ${
                  activeTab === 'keys'
                    ? 'bg-gradient-to-r from-red-500 to-red-600 text-white shadow-sm'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                🔑 API Keys
              </button>
              <button
                onClick={() => setActiveTab('docs')}
                className={`py-2 px-3 rounded-md font-medium text-xs transition-all ${
                  activeTab === 'docs'
                    ? 'bg-gradient-to-r from-red-500 to-red-600 text-white shadow-sm'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                📚 Documentation
              </button>
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'keys' && (
          <div className="space-y-3">
            {apiKeys.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-xl border-2 border-dashed border-red-300 shadow-sm">
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                </div>
                <h3 className="text-base font-bold text-gray-900 mb-2">
                  No API keys yet
                </h3>
                <p className="text-gray-600 mb-5 text-sm">
                  Create your first API key to start using the API
                </p>
                <button
                  onClick={() => setShowCreateForm(true)}
                  className="inline-flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all text-xs font-medium shadow-sm"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Create API Key
                </button>
              </div>
            ) : (
              apiKeys.map((key) => (
                <div
                  key={key.id}
                  className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-red-300 transition-all"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-3">
                        <h3 className="text-base font-bold text-gray-900">
                          {key.key_name}
                        </h3>
                        <span
                          className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                            key.is_active
                              ? 'bg-emerald-100 text-emerald-700'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {key.is_active ? '✓ Active' : '○ Inactive'}
                        </span>
                      </div>

                      <div className="space-y-2 text-xs">
                        <div className="flex items-center gap-2 text-gray-600">
                          <div className="w-7 h-7 bg-gray-100 rounded-md flex items-center justify-center">
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                            </svg>
                          </div>
                          <code className="font-mono text-sm font-semibold text-gray-900">
                            {key.key_prefix}••••••••
                          </code>
                        </div>
                        <div className="flex items-center gap-2 text-gray-600">
                          <div className="w-7 h-7 bg-red-100 rounded-md flex items-center justify-center">
                            <svg className="w-3.5 h-3.5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                          </div>
                          <span className="font-medium">
                            <span className="text-red-600 font-bold">{key.rate_limit_per_minute}</span>/min · 
                            <span className="text-red-600 font-bold"> {key.rate_limit_per_hour}</span>/hr · 
                            <span className="text-red-600 font-bold"> {key.rate_limit_per_day}</span>/day
                          </span>
                        </div>
                        {key.expires_at && (
                          <div className="flex items-center gap-2 text-gray-600">
                            <div className="w-7 h-7 bg-red-100 rounded-md flex items-center justify-center">
                              <svg className="w-3.5 h-3.5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            </div>
                            <span>Expires: {new Date(key.expires_at).toLocaleDateString()}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleRegenerateKey(key.id)}
                        className="p-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-all"
                        title="Regenerate key"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDeleteKey(key.id)}
                        className="p-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-all"
                        title="Delete key"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'docs' && (
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-gray-200">
              <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-900">API Documentation</h3>
            </div>

            {/* Quick Start */}
            <div>
              <h4 className="text-base font-bold text-gray-900 mb-3 flex items-center gap-2">
                <span className="text-xl">🚀</span> Quick Start
              </h4>
              <div className="bg-gradient-to-br from-red-50 to-red-50 p-5 rounded-lg space-y-4 border border-red-200">
                <div>
                  <p className="font-semibold text-gray-900 mb-1 text-sm">1. Get your API key</p>
                  <p className="text-gray-700 text-xs">
                    Create an API key from the "API Keys" tab above
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-gray-900 mb-2 text-sm">2. Make your first request</p>
                  <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg text-xs overflow-x-auto">
{`curl -X POST ${apiBaseUrl}/api/v1/public/agents/${agent.id}/chat/stream \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "Hello, agent!",
    "conversation_id": null
  }'`}
                  </pre>
                </div>
              </div>
            </div>

            {/* Endpoints */}
            <div>
              <h4 className="text-base font-bold text-gray-900 mb-3 flex items-center gap-2">
                <span className="text-xl">🔌</span> Available Endpoints
              </h4>
              <div className="space-y-3">
                <div className="border-2 border-red-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-md font-bold text-xs">POST</span>
                    <code className="font-mono text-xs font-semibold text-gray-900">/api/v1/public/agents/:agent_id/chat/stream</code>
                  </div>
                  <p className="text-gray-700 mb-3 text-xs">
                    Stream responses from the agent in real-time using Server-Sent Events (SSE)
                  </p>
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <p className="font-semibold text-gray-900 mb-2 text-xs">Request Body:</p>
                    <pre className="text-xs overflow-x-auto text-gray-800 mb-2">
{`{
  "message": "Your message here",
  "conversation_id": "optional-conversation-id"
}`}
                    </pre>
                    <p className="text-xs text-gray-600 italic">
                      💡 Conversation history is automatically managed by the conversation_id. You don't need to send previous messages.
                    </p>
                  </div>
                </div>

                <div className="border-2 border-red-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-md font-bold text-xs">GET</span>
                    <code className="font-mono text-xs font-semibold text-gray-900">/api/v1/public/agents/:agent_id/conversations</code>
                  </div>
                  <p className="text-gray-700 text-xs">
                    List all conversations for this agent
                  </p>
                </div>

                <div className="border-2 border-red-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-md font-bold text-xs">GET</span>
                    <code className="font-mono text-xs font-semibold text-gray-900">/api/v1/public/agents/:agent_id/conversations/:conversation_id</code>
                  </div>
                  <p className="text-gray-700 text-xs">
                    Retrieve a specific conversation with its message history
                  </p>
                </div>

                <div className="border-2 border-red-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-md font-bold text-xs">DELETE</span>
                    <code className="font-mono text-xs font-semibold text-gray-900">/api/v1/public/agents/:agent_id/conversations/:conversation_id</code>
                  </div>
                  <p className="text-gray-700 text-xs">
                    Delete a conversation and its message history
                  </p>
                </div>
              </div>
            </div>

            {/* Security */}
            <div>
              <h4 className="text-base font-bold text-gray-900 mb-3 flex items-center gap-2">
                <span className="text-xl">🔒</span> Security Best Practices
              </h4>
              <div className="bg-gradient-to-br from-red-50 to-red-50 p-5 rounded-lg border border-red-200">
                <ul className="space-y-2 text-gray-800">
                  <li className="flex items-start gap-2 text-xs">
                    <span className="text-red-600 font-bold">✓</span>
                    <span>Never commit API keys to version control</span>
                  </li>
                  <li className="flex items-start gap-2 text-xs">
                    <span className="text-red-600 font-bold">✓</span>
                    <span>Use environment variables to store keys</span>
                  </li>
                  <li className="flex items-start gap-2 text-xs">
                    <span className="text-red-600 font-bold">✓</span>
                    <span>Rotate keys regularly</span>
                  </li>
                  <li className="flex items-start gap-2 text-xs">
                    <span className="text-red-600 font-bold">✓</span>
                    <span>Set IP whitelists when possible</span>
                  </li>
                  <li className="flex items-start gap-2 text-xs">
                    <span className="text-red-600 font-bold">✓</span>
                    <span>Use the minimum required permissions</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Modern API Key Form Component
function ApiKeyForm({
  agentId,
  onSubmit,
  onCancel,
  isLoading,
}: {
  agentId: string;
  onSubmit: (data: CreateApiKeyRequest) => Promise<void>;
  onCancel: () => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState<CreateApiKeyRequest>({
    agent_id: agentId,
    key_name: '',
    rate_limit_per_minute: 60,
    rate_limit_per_hour: 1000,
    rate_limit_per_day: 10000,
    allowed_ips: [],
    allowed_origins: [],
    permissions: ['chat', 'conversations'],
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-xs font-bold text-gray-900 mb-2">
          Key Name *
        </label>
        <input
          type="text"
          value={formData.key_name}
          onChange={(e) => setFormData({ ...formData, key_name: e.target.value })}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-all text-gray-900 font-medium"
          placeholder="e.g., Production API Key"
          required
        />
      </div>

      <div>
        <label className="block text-xs font-bold text-gray-900 mb-2">
          Rate Limits
        </label>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">
              Per Minute
            </label>
            <input
              type="number"
              value={formData.rate_limit_per_minute}
              onChange={(e) =>
                setFormData({ ...formData, rate_limit_per_minute: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-all text-gray-900 font-semibold"
              min="1"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">
              Per Hour
            </label>
            <input
              type="number"
              value={formData.rate_limit_per_hour}
              onChange={(e) =>
                setFormData({ ...formData, rate_limit_per_hour: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-all text-gray-900 font-semibold"
              min="1"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">
              Per Day
            </label>
            <input
              type="number"
              value={formData.rate_limit_per_day}
              onChange={(e) =>
                setFormData({ ...formData, rate_limit_per_day: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-all text-gray-900 font-semibold"
              min="1"
              required
            />
          </div>
        </div>
      </div>

      <div className="flex gap-3 pt-3">
        <button
          type="button"
          onClick={onCancel}
          className="px-5 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-white hover:border-red-300 transition-all font-medium text-sm"
          disabled={isLoading}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="flex-1 px-4 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm shadow-sm"
          disabled={isLoading}
        >
          {isLoading ? 'Creating...' : 'Create API Key'}
        </button>
      </div>
    </form>
  );
}
