"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, MessageCircle, ExternalLink, CheckCircle, AlertCircle } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import Link from "next/link";

interface TokenValidation {
  valid: boolean;
  message: string;
  bot_info?: {
    bot_id: number;
    username: string;
    name: string;
    can_join_groups: boolean;
    can_read_all_group_messages: boolean;
  };
}

export default function CreateTelegramBotPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;

  const [formData, setFormData] = useState({
    bot_name: "",
    bot_token: "",
    use_webhook: false,
    webhook_url: "",
  });

  const [agentId, setAgentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [tokenValidation, setTokenValidation] = useState<TokenValidation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAgent();
  }, [agentName]);

  const loadAgent = async () => {
    try {
      const agent = await apiClient.getAgent(agentName);
      setAgentId(agent.id);
    } catch (err: any) {
      console.error("Error loading agent:", err);
      setError("Failed to load agent");
    }
  };

  const handleValidateToken = async () => {
    if (!formData.bot_token.trim()) {
      setError("Please enter a bot token");
      return;
    }

    try {
      setValidating(true);
      setError(null);
      setTokenValidation(null);

      const result = await apiClient.validateTelegramToken(formData.bot_token);
      setTokenValidation(result);

      // Auto-fill bot name if empty
      if (result.valid && result.bot_info?.name && !formData.bot_name) {
        setFormData(prev => ({
          ...prev,
          bot_name: result.bot_info!.name
        }));
      }
    } catch (err: any) {
      console.error("Error validating token:", err);
      setError(err.response?.data?.detail || "Failed to validate token");
    } finally {
      setValidating(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!agentId) {
      setError("Agent not loaded");
      return;
    }

    if (!tokenValidation?.valid) {
      setError("Please validate your bot token first");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      await apiClient.createTelegramBot({
        agent_id: agentId,
        bot_name: formData.bot_name,
        bot_token: formData.bot_token,
        use_webhook: formData.use_webhook,
        webhook_url: formData.use_webhook ? formData.webhook_url : undefined,
      });

      router.push(`/agents/${agentName}/telegram-bots`);
    } catch (err: any) {
      console.error("Error creating bot:", err);
      setError(err.response?.data?.detail || "Failed to create Telegram bot");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Link
            href={`/agents/${agentName}/telegram-bots`}
            className="inline-flex items-center text-primary-600 hover:text-primary-700 text-sm font-medium mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Telegram Bots
          </Link>
          <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Add Telegram Bot</h1>
          <p className="text-gray-600 mt-1 text-sm">
            Connect a Telegram bot to your agent <span className="font-semibold">{agentName}</span>
          </p>
        </div>

        {/* Setup Guide */}
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4 mb-6">
          <div className="flex items-start">
            <MessageCircle className="h-5 w-5 text-primary-600 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-primary-800">How to create a Telegram bot</h3>
              <ol className="mt-2 text-xs text-primary-700 space-y-1 list-decimal list-inside">
                <li>Open Telegram and search for @BotFather</li>
                <li>Send /newbot and follow the prompts</li>
                <li>Copy the bot token provided</li>
                <li>Paste it below and validate</li>
              </ol>
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
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Bot Configuration</h2>

            {/* Bot Token */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Bot Token <span className="text-red-500">*</span>
              </label>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={formData.bot_token}
                  onChange={(e) => {
                    setFormData({ ...formData, bot_token: e.target.value });
                    setTokenValidation(null);
                  }}
                  placeholder="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  required
                />
                <button
                  type="button"
                  onClick={handleValidateToken}
                  disabled={validating || !formData.bot_token.trim()}
                  className="px-4 py-2 bg-primary-100 text-primary-700 rounded-lg text-sm font-medium hover:bg-primary-200 transition-colors disabled:opacity-50"
                >
                  {validating ? "Validating..." : "Validate"}
                </button>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Get this from @BotFather on Telegram
              </p>
            </div>

            {/* Token Validation Result */}
            {tokenValidation && (
              <div className={`mb-4 p-3 rounded-lg ${tokenValidation.valid ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-start gap-2">
                  {tokenValidation.valid ? (
                    <CheckCircle className="h-5 w-5 text-emerald-600 flex-shrink-0" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
                  )}
                  <div>
                    <p className={`text-sm font-medium ${tokenValidation.valid ? 'text-emerald-800' : 'text-red-800'}`}>
                      {tokenValidation.message}
                    </p>
                    {tokenValidation.valid && tokenValidation.bot_info && (
                      <div className="mt-2 text-xs text-emerald-700 space-y-1">
                        <p>Username: @{tokenValidation.bot_info.username}</p>
                        <p>Bot ID: {tokenValidation.bot_info.bot_id}</p>
                        <p>Can join groups: {tokenValidation.bot_info.can_join_groups ? 'Yes' : 'No'}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Bot Name */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Display Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.bot_name}
                onChange={(e) => setFormData({ ...formData, bot_name: e.target.value })}
                placeholder="My Support Bot"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                A friendly name for this bot in Synkora
              </p>
            </div>

            {/* Webhook Mode (Advanced) */}
            <div className="border-t border-gray-200 pt-4 mt-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Advanced Settings</h3>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.use_webhook}
                  onChange={(e) => setFormData({ ...formData, use_webhook: e.target.checked })}
                  className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">Use webhook instead of long polling</span>
              </label>
              <p className="mt-1 text-xs text-gray-500 ml-6">
                Long polling is recommended for most use cases. Webhook requires HTTPS endpoint.
              </p>

              {formData.use_webhook && (
                <div className="mt-3 ml-6">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Webhook URL
                  </label>
                  <input
                    type="url"
                    value={formData.webhook_url}
                    onChange={(e) => setFormData({ ...formData, webhook_url: e.target.value })}
                    placeholder="https://your-domain.com/webhook/telegram"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Submit Buttons */}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={loading || !tokenValidation?.valid}
              className="flex-1 px-4 py-2 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-lg text-sm font-medium hover:from-primary-600 hover:to-primary-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Creating..." : "Create Telegram Bot"}
            </button>
            <Link
              href={`/agents/${agentName}/telegram-bots`}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors text-center"
            >
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
