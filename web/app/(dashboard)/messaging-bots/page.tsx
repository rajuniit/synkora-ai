'use client'

import { useState} from 'react'
import Link from 'next/link'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/ErrorAlert'
import EmptyState from '@/components/common/EmptyState'
import { useWhatsAppBots, useTeamsBots } from '@/hooks/useMessagingBots'
import type { WhatsAppBot, TeamsBot } from '@/types/messaging-bots'

export default function MessagingBotsPage() {
  const { bots: whatsappBots, loading: whatsappLoading, error: whatsappError, toggleActive: toggleWhatsApp, deleteBot: deleteWhatsApp } = useWhatsAppBots()
  const { bots: teamsBots, loading: teamsLoading, error: teamsError, toggleActive: toggleTeams, deleteBot: deleteTeams } = useTeamsBots()
  
  const [deleteConfirm, setDeleteConfirm] = useState<{ type: 'whatsapp' | 'teams'; id: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loading = whatsappLoading || teamsLoading
  const totalBots = whatsappBots.length + teamsBots.length
  const activeBots = whatsappBots.filter(b => b.is_active).length + teamsBots.filter(b => b.is_active).length

  const handleDelete = async () => {
    if (!deleteConfirm) return
    
    try {
      if (deleteConfirm.type === 'whatsapp') {
        await deleteWhatsApp(deleteConfirm.id)
      } else {
        await deleteTeams(deleteConfirm.id)
      }
      setDeleteConfirm(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete bot')
    }
  }

  const handleToggleActive = async (type: 'whatsapp' | 'teams', bot: WhatsAppBot | TeamsBot) => {
    try {
      if (type === 'whatsapp') {
        await toggleWhatsApp(bot as WhatsAppBot)
      } else {
        await toggleTeams(bot as TeamsBot)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle bot status')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Messaging Bots</h1>
            <p className="text-gray-600 mt-2">
              Connect your agents to WhatsApp and Microsoft Teams
            </p>
          </div>
          <div className="flex gap-3">
            <Link
              href="/messaging-bots/whatsapp/create"
              className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center gap-2"
            >
              <span className="text-xl">💬</span>
              Add WhatsApp Bot
            </Link>
            <Link
              href="/messaging-bots/teams/create"
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2"
            >
              <span className="text-xl">👥</span>
              Add Teams Bot
            </Link>
          </div>
        </div>

        {(error || whatsappError || teamsError) && (
          <div className="mb-6">
            <ErrorAlert 
              message={error || whatsappError || teamsError || 'An error occurred'} 
              onDismiss={() => setError(null)} 
            />
          </div>
        )}

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow-sm">
            <div className="text-gray-600 text-sm">Total Bots</div>
            <div className="text-3xl font-bold text-gray-900 mt-2">{totalBots}</div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm">
            <div className="text-gray-600 text-sm">Active Bots</div>
            <div className="text-3xl font-bold text-green-600 mt-2">{activeBots}</div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm">
            <div className="text-gray-600 text-sm">WhatsApp Bots</div>
            <div className="text-3xl font-bold text-green-600 mt-2">{whatsappBots.length}</div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm">
            <div className="text-gray-600 text-sm">Teams Bots</div>
            <div className="text-3xl font-bold text-blue-600 mt-2">{teamsBots.length}</div>
          </div>
        </div>

        {/* Bots List */}
        {totalBots === 0 ? (
          <EmptyState
            title="No Messaging Bots"
            description="Get started by connecting your first WhatsApp or Microsoft Teams bot to enable messaging capabilities for your agents."
            actionLabel="Add WhatsApp Bot"
            actionHref="/messaging-bots/whatsapp/create"
          />
        ) : (
          <div className="space-y-6">
            {/* WhatsApp Bots Section */}
            {whatsappBots.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">💬</span>
                    <h2 className="text-xl font-semibold text-gray-900">WhatsApp Bots</h2>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      {whatsappBots.length} {whatsappBots.length === 1 ? 'bot' : 'bots'}
                    </span>
                  </div>
                </div>

                <div className="divide-y divide-gray-200">
                  {whatsappBots.map((bot) => (
                    <div key={bot.bot_id} className="p-6 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-lg font-semibold text-gray-900">{bot.bot_name}</h3>
                            {bot.is_active ? (
                              <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                Active
                              </span>
                            ) : (
                              <span className="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                Inactive
                              </span>
                            )}
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm mt-3">
                            <div>
                              <span className="text-gray-500">Agent:</span>
                              <span className="ml-2 font-medium text-gray-900">{bot.agent_name}</span>
                            </div>
                            <div>
                              <span className="text-gray-500">Phone Number ID:</span>
                              <code className="ml-2 px-2 py-1 bg-gray-100 rounded text-xs font-mono">
                                {bot.phone_number_id}
                              </code>
                            </div>
                          </div>

                          {bot.webhook_url && (
                            <div className="mt-3 text-sm">
                              <span className="text-gray-500">Webhook URL:</span>
                              <code className="ml-2 px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-mono">
                                {bot.webhook_url}
                              </code>
                            </div>
                          )}

                          <div className="mt-3 text-xs text-gray-500">
                            Created: {new Date(bot.created_at).toLocaleDateString()}
                            {bot.last_message_at && ` • Last message: ${new Date(bot.last_message_at).toLocaleDateString()}`}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 ml-4">
                          <button
                            onClick={() => handleToggleActive('whatsapp', bot)}
                            className={`p-2 rounded-lg transition-colors ${
                              bot.is_active
                                ? 'text-gray-600 hover:bg-gray-100'
                                : 'text-green-600 hover:bg-green-50'
                            }`}
                            title={bot.is_active ? 'Deactivate' : 'Activate'}
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              {bot.is_active ? (
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              ) : (
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              )}
                            </svg>
                          </button>

                          <Link
                            href={`/messaging-bots/whatsapp/${bot.bot_id}/edit`}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            title="Edit"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </Link>

                          {deleteConfirm?.type === 'whatsapp' && deleteConfirm?.id === bot.bot_id ? (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={handleDelete}
                                className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
                              >
                                Confirm
                              </button>
                              <button
                                onClick={() => setDeleteConfirm(null)}
                                className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setDeleteConfirm({ type: 'whatsapp', id: bot.bot_id })}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                              title="Delete"
                            >
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Teams Bots Section */}
            {teamsBots.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">👥</span>
                    <h2 className="text-xl font-semibold text-gray-900">Microsoft Teams Bots</h2>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {teamsBots.length} {teamsBots.length === 1 ? 'bot' : 'bots'}
                    </span>
                  </div>
                </div>

                <div className="divide-y divide-gray-200">
                  {teamsBots.map((bot) => (
                    <div key={bot.bot_id} className="p-6 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-lg font-semibold text-gray-900">{bot.bot_name}</h3>
                            {bot.is_active ? (
                              <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                Active
                              </span>
                            ) : (
                              <span className="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                Inactive
                              </span>
                            )}
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm mt-3">
                            <div>
                              <span className="text-gray-500">Agent:</span>
                              <span className="ml-2 font-medium text-gray-900">{bot.agent_name}</span>
                            </div>
                            <div>
                              <span className="text-gray-500">App ID:</span>
                              <code className="ml-2 px-2 py-1 bg-gray-100 rounded text-xs font-mono">
                                {bot.app_id.substring(0, 20)}...
                              </code>
                            </div>
                          </div>

                          {bot.welcome_message && (
                            <div className="mt-3 text-sm">
                              <span className="text-gray-500">Welcome Message:</span>
                              <p className="ml-2 text-gray-700 italic">{bot.welcome_message}</p>
                            </div>
                          )}

                          {bot.webhook_url && (
                            <div className="mt-3 text-sm">
                              <span className="text-gray-500">Webhook URL:</span>
                              <code className="ml-2 px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-mono">
                                {bot.webhook_url}
                              </code>
                            </div>
                          )}

                          <div className="mt-3 text-xs text-gray-500">
                            Created: {new Date(bot.created_at).toLocaleDateString()}
                            {bot.last_message_at && ` • Last message: ${new Date(bot.last_message_at).toLocaleDateString()}`}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 ml-4">
                          <button
                            onClick={() => handleToggleActive('teams', bot)}
                            className={`p-2 rounded-lg transition-colors ${
                              bot.is_active
                                ? 'text-gray-600 hover:bg-gray-100'
                                : 'text-green-600 hover:bg-green-50'
                            }`}
                            title={bot.is_active ? 'Deactivate' : 'Activate'}
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              {bot.is_active ? (
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              ) : (
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              )}
                            </svg>
                          </button>

                          <Link
                            href={`/messaging-bots/teams/${bot.bot_id}/edit`}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            title="Edit"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </Link>

                          {deleteConfirm?.type === 'teams' && deleteConfirm?.id === bot.bot_id ? (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={handleDelete}
                                className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
                              >
                                Confirm
                              </button>
                              <button
                                onClick={() => setDeleteConfirm(null)}
                                className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setDeleteConfirm({ type: 'teams', id: bot.bot_id })}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                              title="Delete"
                            >
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Info Box */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <svg className="w-6 h-6 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <div>
              <h3 className="text-sm font-medium text-blue-900 mb-2">About Messaging Bots</h3>
              <p className="text-sm text-blue-800 mb-3">
                Connect your agents to popular messaging platforms to enable conversations through WhatsApp and Microsoft Teams.
              </p>
              <div className="space-y-2 text-sm text-blue-800">
                <div>
                  <strong>WhatsApp:</strong> Requires WhatsApp Business API access and configuration
                </div>
                <div>
                  <strong>Microsoft Teams:</strong> Requires Azure Bot Service registration and app credentials
                </div>
              </div>
              <div className="mt-4">
                <Link
                  href="/messaging-bots/setup-guide"
                  className="text-sm text-blue-600 hover:text-blue-700 font-medium underline"
                >
                  View Setup Guide →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
