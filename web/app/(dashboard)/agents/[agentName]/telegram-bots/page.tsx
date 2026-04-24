"use client";

import { useState, useEffect } from "react";
import { extractErrorMessage } from '@/lib/api/error'
import { useParams, useRouter } from "next/navigation";
import { Plus, Power, PowerOff, RefreshCw, Trash2, Settings, ExternalLink, MessageCircle, ChevronRight } from "lucide-react";
import { apiClient } from "@/lib/api/client";

interface TelegramBot {
  id: string;
  agent_id: string;
  bot_name: string;
  bot_username: string | null;
  telegram_bot_id: number | null;
  use_webhook: boolean;
  is_active: boolean;
  connection_status: string;
  last_connected_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export default function TelegramBotsPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;

  const [bots, setBots] = useState<TelegramBot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    loadBots();
  }, [agentName]);

  const loadBots = async () => {
    try {
      setLoading(true);
      setError(null);

      // First get the agent to get its ID
      const agent = await apiClient.getAgent(agentName);
      const agentId = agent.id;

      // Then get bots for this agent
      const botsData = await apiClient.getTelegramBots(agentId);
      setBots(botsData);
    } catch (err: any) {
      console.error("Error loading Telegram bots:", err);
      setError(err.response?.data?.message || "Failed to load Telegram bots");
    } finally {
      setLoading(false);
    }
  };

  const handleStartBot = async (botId: string) => {
    try {
      setActionLoading(botId);
      await apiClient.startTelegramBot(botId);
      await loadBots();
    } catch (err: any) {
      console.error("Error starting bot:", err);
      alert(extractErrorMessage(err, "Failed to start bot"))
    } finally {
      setActionLoading(null);
    }
  };

  const handleStopBot = async (botId: string) => {
    try {
      setActionLoading(botId);
      await apiClient.stopTelegramBot(botId);
      await loadBots();
    } catch (err: any) {
      console.error("Error stopping bot:", err);
      alert(extractErrorMessage(err, "Failed to stop bot"))
    } finally {
      setActionLoading(null);
    }
  };

  const handleRestartBot = async (botId: string) => {
    try {
      setActionLoading(botId);
      await apiClient.restartTelegramBot(botId);
      await loadBots();
    } catch (err: any) {
      console.error("Error restarting bot:", err);
      alert(extractErrorMessage(err, "Failed to restart bot"))
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteBot = async (botId: string, botName: string) => {
    if (!confirm(`Are you sure you want to delete the bot "${botName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setActionLoading(botId);
      await apiClient.deleteTelegramBot(botId);
      await loadBots();
    } catch (err: any) {
      console.error("Error deleting bot:", err);
      alert(extractErrorMessage(err, "Failed to delete bot"))
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "connected":
        return "text-emerald-600 bg-emerald-50";
      case "disconnected":
        return "text-gray-600 bg-gray-50";
      case "error":
        return "text-red-600 bg-red-50";
      default:
        return "text-gray-600 bg-gray-50";
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

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
          <span className="text-gray-900 font-medium">Telegram Bots</span>
        </div>

        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Telegram Bots</h1>
            <p className="text-gray-600 mt-1 text-sm">
              Connect your agent <span className="font-semibold">{agentName}</span> to Telegram
            </p>
          </div>
          <button
            onClick={() => router.push(`/agents/${agentName}/telegram-bots/create`)}
            className="flex items-center gap-2 bg-gradient-to-r from-primary-500 to-primary-600 text-white px-3 py-2 rounded-lg hover:from-primary-600 hover:to-primary-700 transition-all text-xs font-medium shadow-sm"
          >
            <Plus size={16} />
            Add Telegram Bot
          </button>
        </div>

        {/* Setup Guide Link */}
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4 mb-6">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <MessageCircle className="h-4 w-4 text-primary-600" />
            </div>
            <div className="ml-3 flex-1">
              <h3 className="text-xs font-medium text-primary-800">
                Need help setting up a Telegram bot?
              </h3>
              <p className="mt-1 text-xs text-primary-700">
                Create a bot using BotFather on Telegram to get your bot token.
              </p>
              <a
                href="https://core.telegram.org/bots#botfather"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-flex items-center text-xs font-medium text-primary-600 hover:text-primary-700"
              >
                View BotFather Documentation
                <ExternalLink className="ml-1 h-3 w-3" />
              </a>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-6">
            <p className="text-xs text-red-800">{error}</p>
          </div>
        )}

        {/* Bots List */}
        {bots.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-xl shadow-sm border border-gray-200">
            <MessageCircle className="mx-auto h-10 w-10 text-primary-400" />
            <h3 className="mt-3 text-base font-medium text-gray-900">No Telegram bots</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating a new Telegram bot.
            </p>
            <div className="mt-5">
              <button
                onClick={() => router.push(`/agents/${agentName}/telegram-bots/create`)}
                className="inline-flex items-center px-3 py-2 border border-transparent rounded-lg shadow-sm text-xs font-medium text-white bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 transition-all"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Telegram Bot
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-200">
              <h2 className="text-base font-semibold text-gray-900">Your Telegram Bots</h2>
            </div>
            <div className="divide-y divide-gray-200">
              {bots.map((bot) => (
                <div key={bot.id} className="p-5 hover:bg-primary-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <h3 className="text-base font-medium text-gray-900 truncate">
                          {bot.bot_name}
                        </h3>
                        {bot.bot_username && (
                          <span className="text-sm text-gray-500">@{bot.bot_username}</span>
                        )}
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
                            bot.connection_status
                          )}`}
                        >
                          {bot.connection_status}
                        </span>
                      </div>
                      <div className="mt-1.5 flex items-center text-xs text-gray-500 space-x-3">
                        {bot.telegram_bot_id && (
                          <>
                            <span>Bot ID: {bot.telegram_bot_id}</span>
                            <span>-</span>
                          </>
                        )}
                        <span>Mode: {bot.use_webhook ? "Webhook" : "Long Polling"}</span>
                        <span>-</span>
                        <span>Last connected: {formatDate(bot.last_connected_at)}</span>
                      </div>
                      {bot.last_error && (
                        <div className="mt-1 text-xs text-red-600">
                          Error: {bot.last_error}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 ml-4">
                      {bot.connection_status === "connected" ? (
                        <button
                          onClick={() => handleStopBot(bot.id)}
                          disabled={actionLoading === bot.id}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                          title="Stop bot"
                        >
                          <PowerOff size={16} />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleStartBot(bot.id)}
                          disabled={actionLoading === bot.id}
                          className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors disabled:opacity-50"
                          title="Start bot"
                        >
                          <Power size={16} />
                        </button>
                      )}
                      <button
                        onClick={() => handleRestartBot(bot.id)}
                        disabled={actionLoading === bot.id}
                        className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors disabled:opacity-50"
                        title="Restart bot"
                      >
                        <RefreshCw size={16} />
                      </button>
                      <button
                        onClick={() =>
                          router.push(`/agents/${agentName}/telegram-bots/${bot.id}/edit`)
                        }
                        className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                        title="Edit bot"
                      >
                        <Settings size={16} />
                      </button>
                      <button
                        onClick={() => handleDeleteBot(bot.id, bot.bot_name)}
                        disabled={actionLoading === bot.id}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                        title="Delete bot"
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
    </div>
  );
}
