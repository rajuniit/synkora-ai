"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, AlertCircle, ExternalLink } from "lucide-react";
import { apiClient } from "@/lib/api/client";

export default function CreateSlackBotPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;

  const [formData, setFormData] = useState({
    bot_name: "",
    slack_app_id: "",
    slack_bot_token: "",
    slack_app_token: "",
    slack_workspace_id: "",
    slack_workspace_name: "",
    connection_mode: "socket",
    signing_secret: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Get agent ID
      const agent = await apiClient.getAgent(agentName);

      // Prepare data based on connection mode
      const botData: any = {
        agent_id: agent.id,
        bot_name: formData.bot_name,
        slack_app_id: formData.slack_app_id,
        slack_bot_token: formData.slack_bot_token,
        connection_mode: formData.connection_mode,
      };

      // Add mode-specific fields
      if (formData.connection_mode === "socket") {
        botData.slack_app_token = formData.slack_app_token;
      } else {
        botData.signing_secret = formData.signing_secret;
      }

      // Create bot
      await apiClient.createSlackBot(botData);

      // Redirect back to bots list
      router.push(`/agents/${agentName}/slack-bots`);
    } catch (err: any) {
      console.error("Error creating Slack bot:", err);
      setError(err.response?.data?.detail || "Failed to create Slack bot");
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-red-50/30 to-gray-50 p-6">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-red-600 hover:text-red-700 mb-4 text-sm font-medium"
          >
            <ArrowLeft size={16} />
            Back to Slack Bots
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Create Slack Bot</h1>
          <p className="text-gray-600 mt-1 text-sm">
            Connect your agent <span className="font-semibold">{agentName}</span> to a Slack workspace
          </p>
        </div>

        {/* Setup Instructions */}
        <div className="mb-5 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-medium text-red-900 mb-2 text-sm">
                Before you begin
              </h3>
              <div className="text-xs text-red-800 space-y-2">
                <p>To create a Slack bot, you need to:</p>
                <ol className="list-decimal list-inside space-y-1 ml-2">
                  <li>Create a Slack app at <a href="https://api.slack.com/apps" target="_blank" rel="noopener noreferrer" className="underline hover:text-red-700">api.slack.com/apps</a></li>
                  <li>
                    {formData.connection_mode === "socket"
                      ? "Enable Socket Mode in your app settings"
                      : "Enable Event Subscriptions in your app settings"}
                  </li>
                  <li>Add the following bot token scopes:
                    <ul className="list-disc list-inside ml-4 mt-1">
                      <li><code className="bg-red-100 px-1 rounded">app_mentions:read</code></li>
                      <li><code className="bg-red-100 px-1 rounded">chat:write</code></li>
                      <li><code className="bg-red-100 px-1 rounded">im:history</code></li>
                      <li><code className="bg-red-100 px-1 rounded">im:read</code></li>
                      <li><code className="bg-red-100 px-1 rounded">im:write</code></li>
                    </ul>
                  </li>
                  <li>Install the app to your workspace</li>
                  <li>
                    {formData.connection_mode === "socket"
                      ? "Copy the Bot User OAuth Token and App-Level Token"
                      : "Copy the Bot User OAuth Token and Signing Secret"}
                  </li>
                </ol>
                <a
                  href="https://api.slack.com/apps"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 mt-3 text-xs font-medium text-red-600 hover:text-red-700 transition-colors"
                >
                  Open Slack API Dashboard
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-5 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-red-900 text-sm">Error</h3>
              <p className="text-red-700 text-xs mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-6 space-y-5">
            {/* Bot Name */}
            <div>
              <label htmlFor="bot_name" className="block text-xs font-medium text-gray-700 mb-1">
                Bot Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="bot_name"
                name="bot_name"
                value={formData.bot_name}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="My Agent Bot"
              />
              <p className="text-xs text-gray-500 mt-1">
                A friendly name to identify this bot
              </p>
            </div>

            {/* Connection Mode */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-2">
                Connection Mode
              </label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="connection_mode"
                    value="socket"
                    checked={formData.connection_mode === "socket"}
                    onChange={handleChange}
                    className="w-4 h-4 text-red-600 focus:ring-red-500"
                  />
                  <span className="text-sm text-gray-700">Socket Mode (Recommended)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="connection_mode"
                    value="event"
                    checked={formData.connection_mode === "event"}
                    onChange={handleChange}
                    className="w-4 h-4 text-red-600 focus:ring-red-500"
                  />
                  <span className="text-sm text-gray-700">Event Mode (HTTP Webhooks)</span>
                </label>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {formData.connection_mode === "socket"
                  ? "Socket Mode uses WebSocket connections (no public URL needed)"
                  : "Event Mode uses HTTP webhooks (requires public URL)"}
              </p>
            </div>

            {/* Slack App ID */}
            <div>
              <label htmlFor="slack_app_id" className="block text-xs font-medium text-gray-700 mb-1">
                Slack App ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="slack_app_id"
                name="slack_app_id"
                value={formData.slack_app_id}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent font-mono text-sm"
                placeholder="A1234567890"
              />
              <p className="text-xs text-gray-500 mt-1">
                Found in your Slack app's Basic Information page
              </p>
            </div>

            {/* Bot Token */}
            <div>
              <label htmlFor="slack_bot_token" className="block text-xs font-medium text-gray-700 mb-1">
                Bot User OAuth Token <span className="text-red-500">*</span>
              </label>
              <input
                type="password"
                id="slack_bot_token"
                name="slack_bot_token"
                value={formData.slack_bot_token}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent font-mono text-sm"
                placeholder="xoxb-..."
              />
              <p className="text-xs text-gray-500 mt-1">
                Found in OAuth & Permissions → Bot User OAuth Token (starts with xoxb-)
              </p>
            </div>

            {/* Socket Mode: App-Level Token */}
            {formData.connection_mode === "socket" && (
              <div>
                <label htmlFor="slack_app_token" className="block text-xs font-medium text-gray-700 mb-1">
                  App-Level Token <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  id="slack_app_token"
                  name="slack_app_token"
                  value={formData.slack_app_token}
                  onChange={handleChange}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent font-mono text-sm"
                  placeholder="xapp-..."
                />
                <p className="text-xs text-gray-500 mt-1">
                  Found in Basic Information → App-Level Tokens (starts with xapp-). Required for Socket Mode.
                </p>
              </div>
            )}

            {/* Event Mode: Signing Secret */}
            {formData.connection_mode === "event" && (
              <div>
                <label htmlFor="signing_secret" className="block text-xs font-medium text-gray-700 mb-1">
                  Signing Secret <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  id="signing_secret"
                  name="signing_secret"
                  value={formData.signing_secret}
                  onChange={handleChange}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent font-mono text-sm"
                  placeholder="Enter your signing secret"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Found in Basic Information → App Credentials → Signing Secret
                </p>
              </div>
            )}

            {/* Event Mode Notice */}
            {formData.connection_mode === "event" && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h4 className="font-medium text-blue-900 mb-1 text-sm">
                      Webhook URL Required
                    </h4>
                    <p className="text-xs text-blue-800">
                      After creating this bot, you'll receive a webhook URL. Add this URL to your Slack app's Event Subscriptions settings to receive events.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Auto-detection notice */}
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-medium text-emerald-900 mb-1 text-sm">
                    Workspace Auto-Detection
                  </h4>
                  <p className="text-xs text-emerald-800">
                    The workspace ID and name will be automatically detected when the bot connects to Slack for the first time.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Form Actions */}
          <div className="border-t border-gray-200 px-6 py-4 bg-red-50 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-4 py-2 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-white hover:border-red-300 transition-colors"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-sm"
            >
              {loading ? "Creating..." : "Create Bot"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
