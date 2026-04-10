"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Power, PowerOff, Settings, Trash2, ExternalLink, MessageCircle, Users, ChevronRight } from "lucide-react";
import { useWhatsAppBots, useTeamsBots } from "@/hooks/useMessagingBots";
import type { WhatsAppBot, TeamsBot } from "@/types/messaging-bots";
import { apiClient } from "@/lib/api/client";

export default function MessagingBotsPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;
  
  const [agentId, setAgentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load agent ID first
  useEffect(() => {
    const loadAgent = async () => {
      try {
        const agent = await apiClient.getAgent(agentName);
        setAgentId(agent.id);
      } catch (err: any) {
        console.error("Error loading agent:", err);
        setError(err.response?.data?.message || "Failed to load agent");
      } finally {
        setLoading(false);
      }
    };
    loadAgent();
  }, [agentName]);

  const {
    bots: whatsappBots,
    loading: whatsappLoading,
    error: whatsappError,
    toggleActive: toggleWhatsApp,
    deleteBot: deleteWhatsApp,
  } = useWhatsAppBots(agentId || undefined);

  const {
    bots: teamsBots,
    loading: teamsLoading,
    error: teamsError,
    toggleActive: toggleTeams,
    deleteBot: deleteTeams,
  } = useTeamsBots(agentId || undefined);

  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleToggleActive = async (type: "whatsapp" | "teams", bot: WhatsAppBot | TeamsBot) => {
    try {
      setActionLoading(bot.bot_id);
      if (type === "whatsapp") {
        await toggleWhatsApp(bot as WhatsAppBot);
      } else {
        await toggleTeams(bot as TeamsBot);
      }
    } catch (err: any) {
      alert(err.message || "Failed to toggle bot status");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (type: "whatsapp" | "teams", bot: WhatsAppBot | TeamsBot) => {
    if (
      !confirm(
        `Are you sure you want to delete the ${type === "whatsapp" ? "WhatsApp" : "Teams"} bot "${bot.bot_name}"? This action cannot be undone.`
      )
    ) {
      return;
    }

    try {
      setActionLoading(bot.bot_id);
      if (type === "whatsapp") {
        await deleteWhatsApp(bot.bot_id);
      } else {
        await deleteTeams(bot.bot_id);
      }
    } catch (err: any) {
      alert(err.message || "Failed to delete bot");
    } finally {
      setActionLoading(null);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleString();
  };

  if (loading || whatsappLoading || teamsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
      </div>
    );
  }

  const totalBots = whatsappBots.length + teamsBots.length;
  const activeBots = whatsappBots.filter((b: WhatsAppBot) => b.is_active).length + teamsBots.filter((b: TeamsBot) => b.is_active).length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Breadcrumb */}
        <div className="flex items-center gap-1.5 text-sm mb-4">
          <button
            onClick={() => router.push("/agents")}
            className="text-gray-500 hover:text-primary-600 transition-colors"
          >
            Agents
          </button>
          <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
          <button
            onClick={() => router.push(`/agents/${encodeURIComponent(agentName)}/view`)}
            className="text-gray-500 hover:text-primary-600 transition-colors"
          >
            {agentName}
          </button>
          <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
          <span className="text-gray-900 font-medium">Messaging Bots</span>
        </div>

        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Messaging Bots</h1>
            <p className="text-gray-600 mt-1">Connect your agent to WhatsApp and Microsoft Teams</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => router.push(`/agents/${agentName}/messaging-bots/whatsapp/create`)}
              className="flex items-center gap-2 bg-gradient-to-r from-red-500 to-red-600 text-white px-4 py-2 rounded-lg hover:from-red-600 hover:to-red-700 transition-all font-medium shadow-sm"
            >
              <MessageCircle size={18} />
              Add WhatsApp Bot
            </button>
            <button
              onClick={() => router.push(`/agents/${agentName}/messaging-bots/teams/create`)}
              className="flex items-center gap-2 bg-gradient-to-r from-red-500 to-red-600 text-white px-4 py-2 rounded-lg hover:from-red-600 hover:to-red-700 transition-all font-medium shadow-sm"
            >
              <Users size={18} />
              Add Teams Bot
            </button>
          </div>
        </div>

        {/* Setup Guide */}
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-5">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <ExternalLink className="h-4 w-4 text-red-600" />
            </div>
            <div className="ml-3 flex-1">
              <h3 className="text-xs font-medium text-red-900">Need help setting up messaging bots?</h3>
              <p className="mt-1 text-xs text-red-800">
                Follow our guides to configure WhatsApp Business API or Microsoft Teams Bot Framework.
              </p>
              <div className="mt-2 flex gap-4">
                <a
                  href="https://developers.facebook.com/docs/whatsapp/cloud-api"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center text-xs font-medium text-red-600 hover:text-red-700"
                >
                  WhatsApp Setup Guide
                  <ExternalLink className="ml-1 h-3 w-3" />
                </a>
                <a
                  href="https://dev.botframework.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center text-xs font-medium text-red-600 hover:text-red-700"
                >
                  Teams Bot Framework
                  <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Error Messages */}
        {(error || whatsappError || teamsError) && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-5">
            <p className="text-xs text-red-800">{error || whatsappError || teamsError}</p>
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6">
          <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
            <div className="text-gray-600 text-xs">Total Bots</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">{totalBots}</div>
          </div>
          <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
            <div className="text-gray-600 text-xs">Active Bots</div>
            <div className="text-2xl font-bold text-emerald-600 mt-1">{activeBots}</div>
          </div>
          <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
            <div className="text-gray-600 text-xs">WhatsApp</div>
            <div className="text-2xl font-bold text-red-600 mt-1">{whatsappBots.length}</div>
          </div>
          <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
            <div className="text-gray-600 text-xs">Teams</div>
            <div className="text-2xl font-bold text-red-600 mt-1">{teamsBots.length}</div>
          </div>
        </div>

        {/* No Bots State */}
        {totalBots === 0 ? (
          <div className="text-center py-10 bg-white rounded-xl shadow-sm border border-gray-200">
            <MessageCircle className="mx-auto h-10 w-10 text-red-400" />
            <h3 className="mt-3 text-base font-medium text-gray-900">No messaging bots</h3>
            <p className="mt-1 text-sm text-gray-500">Get started by creating your first WhatsApp or Teams bot.</p>
            <div className="mt-5 flex gap-2 justify-center">
              <button
                onClick={() => router.push(`/agents/${agentName}/messaging-bots/whatsapp/create`)}
                className="inline-flex items-center px-4 py-2 rounded-lg shadow-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 transition-all"
              >
                <MessageCircle className="h-4 w-4 mr-2" />
                Add WhatsApp Bot
              </button>
              <button
                onClick={() => router.push(`/agents/${agentName}/messaging-bots/teams/create`)}
                className="inline-flex items-center px-4 py-2 rounded-lg shadow-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 transition-all"
              >
                <Users className="h-4 w-4 mr-2" />
                Add Teams Bot
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            {/* WhatsApp Bots */}
            {whatsappBots.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-200 bg-red-50">
                  <div className="flex items-center gap-2">
                    <MessageCircle className="text-red-600" size={20} />
                    <h2 className="text-base font-semibold text-gray-900">WhatsApp Bots</h2>
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      {whatsappBots.length}
                    </span>
                  </div>
                </div>
                <div className="divide-y divide-gray-200">
                  {whatsappBots.map((bot: WhatsAppBot) => (
                    <div key={bot.bot_id} className="p-5 hover:bg-red-50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <h3 className="text-sm font-medium text-gray-900 truncate">{bot.bot_name}</h3>
                            {bot.is_active ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                                Active
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                Inactive
                              </span>
                            )}
                          </div>
                          <div className="mt-1.5 flex flex-col sm:flex-row sm:flex-wrap sm:space-x-3 text-xs text-gray-500 gap-0.5">
                            <span>Phone: {bot.phone_number_id}</span>
                            <span className="hidden sm:inline">•</span>
                            <span>Created: {formatDate(bot.created_at)}</span>
                            {bot.last_message_at && (
                              <>
                                <span className="hidden sm:inline">•</span>
                                <span>Last message: {formatDate(bot.last_message_at)}</span>
                              </>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5 ml-4">
                          {bot.is_active ? (
                            <button
                              onClick={() => handleToggleActive("whatsapp", bot)}
                              disabled={actionLoading === bot.bot_id}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                              title="Deactivate"
                            >
                              <PowerOff size={16} />
                            </button>
                          ) : (
                            <button
                              onClick={() => handleToggleActive("whatsapp", bot)}
                              disabled={actionLoading === bot.bot_id}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                              title="Activate"
                            >
                              <Power size={16} />
                            </button>
                          )}
                          <button
                            onClick={() =>
                              router.push(`/agents/${agentName}/messaging-bots/whatsapp/${bot.bot_id}/edit`)
                            }
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Edit"
                          >
                            <Settings size={16} />
                          </button>
                          <button
                            onClick={() => handleDelete("whatsapp", bot)}
                            disabled={actionLoading === bot.bot_id}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                            title="Delete"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Teams Bots */}
            {teamsBots.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-200 bg-red-50">
                  <div className="flex items-center gap-2">
                    <Users className="text-red-600" size={20} />
                    <h2 className="text-base font-semibold text-gray-900">Microsoft Teams Bots</h2>
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      {teamsBots.length}
                    </span>
                  </div>
                </div>
                <div className="divide-y divide-gray-200">
                  {teamsBots.map((bot: TeamsBot) => (
                    <div key={bot.bot_id} className="p-5 hover:bg-red-50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <h3 className="text-sm font-medium text-gray-900 truncate">{bot.bot_name}</h3>
                            {bot.is_active ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                                Active
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                Inactive
                              </span>
                            )}
                          </div>
                          <div className="mt-1.5 flex flex-col sm:flex-row sm:flex-wrap sm:space-x-3 text-xs text-gray-500 gap-0.5">
                            <span>App ID: {bot.app_id.substring(0, 20)}...</span>
                            <span className="hidden sm:inline">•</span>
                            <span>Created: {formatDate(bot.created_at)}</span>
                            {bot.last_message_at && (
                              <>
                                <span className="hidden sm:inline">•</span>
                                <span>Last message: {formatDate(bot.last_message_at)}</span>
                              </>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5 ml-4">
                          {bot.is_active ? (
                            <button
                              onClick={() => handleToggleActive("teams", bot)}
                              disabled={actionLoading === bot.bot_id}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                              title="Deactivate"
                            >
                              <PowerOff size={16} />
                            </button>
                          ) : (
                            <button
                              onClick={() => handleToggleActive("teams", bot)}
                              disabled={actionLoading === bot.bot_id}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                              title="Activate"
                            >
                              <Power size={16} />
                            </button>
                          )}
                          <button
                            onClick={() =>
                              router.push(`/agents/${agentName}/messaging-bots/teams/${bot.bot_id}/edit`)
                            }
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Edit"
                          >
                            <Settings size={16} />
                          </button>
                          <button
                            onClick={() => handleDelete("teams", bot)}
                            disabled={actionLoading === bot.bot_id}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                            title="Delete"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
