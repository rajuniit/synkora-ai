"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, AlertCircle, Users } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { teamsBotsApi } from "@/lib/api/messaging-bots";
import type { CreateTeamsBotRequest } from "@/types/messaging-bots";

export default function CreateTeamsBotPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState<CreateTeamsBotRequest>({
    agent_id: "",
    bot_name: "",
    app_id: "",
    app_password: "",
    bot_id: "",
    webhook_url: "",
    welcome_message: "",
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const loadAgent = async () => {
      try {
        const agent = await apiClient.getAgent(agentName);
        setFormData((prev) => ({ ...prev, agent_id: agent.id }));
      } catch (err: any) {
        console.error("Error loading agent:", err);
        setError(err.response?.data?.message || "Failed to load agent");
      } finally {
        setLoading(false);
      }
    };
    loadAgent();
  }, [agentName]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.bot_name.trim()) {
      newErrors.bot_name = "Bot name is required";
    }

    if (!formData.app_id.trim()) {
      newErrors.app_id = "App ID is required";
    }

    if (!formData.app_password.trim()) {
      newErrors.app_password = "App password is required";
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
      await teamsBotsApi.createBot(formData);
      router.push(`/agents/${agentName}/messaging-bots`);
    } catch (err: any) {
      console.error("Error creating Teams bot:", err);
      setError(err.response?.data?.message || "Failed to create Teams bot");
    } finally {
      setSubmitting(false);
    }
  };

  const handleChange = (field: keyof CreateTeamsBotRequest, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev: Record<string, string>) => ({ ...prev, [field]: "" }));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-red-50/30 to-gray-50 p-4 md:p-6">
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <button
            onClick={() => router.push(`/agents/${agentName}/messaging-bots`)}
            className="flex items-center text-red-600 hover:text-red-700 mb-4 text-sm font-medium"
          >
            <ArrowLeft size={16} className="mr-2" />
            Back to Messaging Bots
          </button>
          <div className="flex items-center gap-3">
            <div className="bg-blue-100 p-2.5 rounded-lg">
              <Users className="text-blue-600" size={20} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Create Teams Bot</h1>
              <p className="text-gray-600 mt-0.5 text-sm">Connect your agent to Microsoft Teams</p>
            </div>
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-5">
          <h3 className="text-xs font-medium text-blue-900 mb-2">Before you begin</h3>
          <ul className="text-xs text-blue-800 space-y-1 list-disc list-inside">
            <li>Register your bot in Azure Portal</li>
            <li>Create a Bot Channels Registration</li>
            <li>Get your App ID and generate an App Password</li>
            <li>Configure the messaging endpoint</li>
          </ul>
          <a
            href="https://dev.botframework.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 hover:text-blue-700 font-medium mt-2 inline-block"
          >
            View Setup Guide →
          </a>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-5 flex items-start">
            <AlertCircle className="text-red-600 mr-2 flex-shrink-0 mt-0.5" size={16} />
            <div>
              <h3 className="text-xs font-medium text-red-800">Error</h3>
              <p className="text-xs text-red-700 mt-1">{error}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-5">
          <div>
            <label htmlFor="bot_name" className="block text-xs font-medium text-gray-700 mb-2">
              Bot Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="bot_name"
              value={formData.bot_name}
              onChange={(e) => handleChange("bot_name", e.target.value)}
              className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent ${
                errors.bot_name ? "border-red-500" : "border-gray-300"
              }`}
              placeholder="e.g., Support Bot"
            />
            {errors.bot_name && <p className="mt-1 text-xs text-red-600">{errors.bot_name}</p>}
          </div>

          <div>
            <label htmlFor="app_id" className="block text-xs font-medium text-gray-700 mb-2">
              App ID <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="app_id"
              value={formData.app_id}
              onChange={(e) => handleChange("app_id", e.target.value)}
              className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent ${
                errors.app_id ? "border-red-500" : "border-gray-300"
              }`}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            />
            {errors.app_id && <p className="mt-1 text-xs text-red-600">{errors.app_id}</p>}
            <p className="mt-1 text-xs text-gray-500">
              Find this in your Azure Bot Channels Registration
            </p>
          </div>

          <div>
            <label htmlFor="app_password" className="block text-xs font-medium text-gray-700 mb-2">
              App Password <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              id="app_password"
              value={formData.app_password}
              onChange={(e) => handleChange("app_password", e.target.value)}
              className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent ${
                errors.app_password ? "border-red-500" : "border-gray-300"
              }`}
              placeholder="App password"
            />
            {errors.app_password && (
              <p className="mt-1 text-xs text-red-600">{errors.app_password}</p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              Generate from Azure Portal (will be encrypted)
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t">
            <button
              type="button"
              onClick={() => router.push(`/agents/${agentName}/messaging-bots`)}
              className="px-5 py-2 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-white hover:border-red-300 transition-colors font-medium"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium shadow-sm"
            >
              {submitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Creating...
                </>
              ) : (
                "Create Teams Bot"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
