"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, AlertCircle, Users } from "lucide-react";
import { teamsBotsApi } from "@/lib/api/messaging-bots";
import type { TeamsBot } from "@/types/messaging-bots";

export default function EditTeamsBotPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;
  const botId = params.botId as string;

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bot, setBot] = useState<TeamsBot | null>(null);

  const [formData, setFormData] = useState({
    bot_name: "",
    app_id: "",
    app_password: "",
    tenant_id: "",
    bot_endpoint: "",
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const loadBot = async () => {
      try {
        const botData = await teamsBotsApi.getBot(botId);
        setBot(botData);
        setFormData({
          bot_name: botData.bot_name,
          app_id: botData.app_id,
          app_password: "", // Don't pre-fill for security
          tenant_id: botData.tenant_id || "",
          bot_endpoint: botData.bot_endpoint || "",
        });
      } catch (err: any) {
        console.error("Error loading bot:", err);
        setError(err.response?.data?.message || "Failed to load bot");
      } finally {
        setLoading(false);
      }
    };
    loadBot();
  }, [botId]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.bot_name.trim()) {
      newErrors.bot_name = "Bot name is required";
    }

    if (!formData.app_id.trim()) {
      newErrors.app_id = "App ID is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: { preventDefault: () => void }) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      // Only include app_password if it was changed
      const updateData = { ...formData };
      if (!updateData.app_password) {
        delete (updateData as any).app_password;
      }
      
      await teamsBotsApi.updateBot(botId, updateData);
      router.push(`/agents/${agentName}/messaging-bots`);
    } catch (err: any) {
      console.error("Error updating Teams bot:", err);
      setError(err.response?.data?.message || "Failed to update Teams bot");
    } finally {
      setSubmitting(false);
    }
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev: Record<string, string>) => ({ ...prev, [field]: "" }));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!bot) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-red-500 mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Bot not found</h3>
          <button
            onClick={() => router.push(`/agents/${agentName}/messaging-bots`)}
            className="mt-4 text-blue-600 hover:text-blue-500"
          >
            Back to Messaging Bots
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8">
          <button
            onClick={() => router.push(`/agents/${agentName}/messaging-bots`)}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft size={20} className="mr-2" />
            Back to Messaging Bots
          </button>
          <div className="flex items-center gap-3">
            <div className="bg-purple-100 p-3 rounded-lg">
              <Users className="text-purple-600" size={24} />
            </div>
            <div>
              <h1 className="text-xl sm:text-3xl font-bold text-gray-900">Edit Teams Bot</h1>
              <p className="text-gray-600 mt-1">Update your Teams bot configuration</p>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-start">
            <AlertCircle className="text-red-600 mr-3 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm p-6 space-y-6">
          <div>
            <label htmlFor="bot_name" className="block text-sm font-medium text-gray-700 mb-2">
              Bot Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="bot_name"
              value={formData.bot_name}
              onChange={(e) => handleChange("bot_name", e.target.value)}
              className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.bot_name ? "border-red-500" : "border-gray-300"
              }`}
            />
            {errors.bot_name && <p className="mt-1 text-sm text-red-600">{errors.bot_name}</p>}
          </div>

          <div>
            <label htmlFor="app_id" className="block text-sm font-medium text-gray-700 mb-2">
              App ID <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="app_id"
              value={formData.app_id}
              onChange={(e) => handleChange("app_id", e.target.value)}
              className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.app_id ? "border-red-500" : "border-gray-300"
              }`}
            />
            {errors.app_id && <p className="mt-1 text-sm text-red-600">{errors.app_id}</p>}
          </div>

          <div>
            <label htmlFor="app_password" className="block text-sm font-medium text-gray-700 mb-2">
              App Password
            </label>
            <input
              type="password"
              id="app_password"
              value={formData.app_password}
              onChange={(e) => handleChange("app_password", e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Leave empty to keep current password"
            />
            <p className="mt-1 text-sm text-gray-500">
              Leave empty to keep the existing password, or enter a new one to update
            </p>
          </div>

          <div>
            <label htmlFor="tenant_id" className="block text-sm font-medium text-gray-700 mb-2">
              Tenant ID
            </label>
            <input
              type="text"
              id="tenant_id"
              value={formData.tenant_id}
              onChange={(e) => handleChange("tenant_id", e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label htmlFor="bot_endpoint" className="block text-sm font-medium text-gray-700 mb-2">
              Bot Endpoint URL
            </label>
            <input
              type="text"
              id="bot_endpoint"
              value={formData.bot_endpoint}
              onChange={(e) => handleChange("bot_endpoint", e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={() => router.push(`/agents/${agentName}/messaging-bots`)}
              className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {submitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Updating...
                </>
              ) : (
                "Update Teams Bot"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
