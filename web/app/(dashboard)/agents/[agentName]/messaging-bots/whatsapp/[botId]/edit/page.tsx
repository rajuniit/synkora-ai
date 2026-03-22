"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, AlertCircle, MessageCircle, Smartphone, CheckCircle, Unlink } from "lucide-react";
import { whatsappBotsApi } from "@/lib/api/messaging-bots";
import type { UpdateWhatsAppBotRequest, WhatsAppBot } from "@/types/messaging-bots";

export default function EditWhatsAppBotPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;
  const botId = params.botId as string;

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [unlinking, setUnlinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bot, setBot] = useState<WhatsAppBot | null>(null);
  const [botName, setBotName] = useState("");
  const [nameError, setNameError] = useState("");

  // Cloud API form fields
  const [formData, setFormData] = useState<UpdateWhatsAppBotRequest>({
    bot_name: "",
    access_token: "",
    verify_token: "",
    webhook_url: "",
    is_active: true,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const loadBot = async () => {
      try {
        const botData = await whatsappBotsApi.getBot(botId);
        setBot(botData);
        setBotName(botData.bot_name);
        setFormData({
          bot_name: botData.bot_name,
          access_token: "",
          verify_token: botData.verify_token || "",
          webhook_url: botData.webhook_url || "",
          is_active: botData.is_active,
        });
      } catch (err: any) {
        setError(err.response?.data?.message || "Failed to load bot");
      } finally {
        setLoading(false);
      }
    };
    loadBot();
  }, [botId]);

  const handleUnlink = async () => {
    if (!confirm("Unlink this device? The bot will stop receiving messages until re-linked via QR.")) return;
    setUnlinking(true);
    setError(null);
    try {
      await whatsappBotsApi.unlinkDevice(botId);
      router.push(`/agents/${agentName}/messaging-bots`);
    } catch (err: any) {
      setError(err.response?.data?.message || "Failed to unlink device");
    } finally {
      setUnlinking(false);
    }
  };

  // Save handler for device_link bots (name only)
  const handleDeviceLinkSave = async () => {
    if (!botName.trim()) {
      setNameError("Bot name is required");
      return;
    }
    setNameError("");
    setSubmitting(true);
    setError(null);
    try {
      await whatsappBotsApi.updateBot(botId, { bot_name: botName });
      router.push(`/agents/${agentName}/messaging-bots`);
    } catch (err: any) {
      setError(err.response?.data?.message || "Failed to update bot");
    } finally {
      setSubmitting(false);
    }
  };

  // Save handler for cloud_api bots
  const handleCloudApiSubmit = async (e: { preventDefault: () => void }) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};
    if (!formData.bot_name?.trim()) newErrors.bot_name = "Bot name is required";
    setErrors(newErrors);
    if (Object.keys(newErrors).length > 0) return;

    setSubmitting(true);
    setError(null);
    try {
      const updateData: UpdateWhatsAppBotRequest = { ...formData };
      if (!updateData.access_token) delete (updateData as any).access_token;
      await whatsappBotsApi.updateBot(botId, updateData);
      router.push(`/agents/${agentName}/messaging-bots`);
    } catch (err: any) {
      setError(err.response?.data?.message || "Failed to update WhatsApp bot");
    } finally {
      setSubmitting(false);
    }
  };

  const handleChange = (field: keyof UpdateWhatsAppBotRequest, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (typeof field === "string" && errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
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

  const isDeviceLink = bot.connection_type === "device_link";

  return (
    <div className="min-h-screen bg-gray-50 p-8">
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
            <div className="bg-green-100 p-3 rounded-lg">
              <MessageCircle className="text-green-600" size={24} />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Edit WhatsApp Bot</h1>
              <p className="text-gray-600 mt-1">
                {isDeviceLink ? "Device Link (QR)" : "Cloud API"} connection
              </p>
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

        {/* ── Device Link edit view ── */}
        {isDeviceLink ? (
          <div className="bg-white rounded-lg shadow-sm p-6 space-y-6">
            {/* Connected device info */}
            <div className="flex items-center gap-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="bg-green-100 p-3 rounded-full">
                <Smartphone className="text-green-600" size={24} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <CheckCircle className="text-green-600" size={16} />
                  <span className="font-medium text-green-800">Device linked</span>
                </div>
                {bot.linked_phone_number && (
                  <p className="text-sm text-green-700 mt-0.5">{bot.linked_phone_number}</p>
                )}
              </div>
            </div>

            {/* Bot name */}
            <div>
              <label htmlFor="bot_name" className="block text-sm font-medium text-gray-700 mb-2">
                Bot Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="bot_name"
                value={botName}
                onChange={(e) => { setBotName(e.target.value); setNameError(""); }}
                className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  nameError ? "border-red-500" : "border-gray-300"
                }`}
              />
              {nameError && <p className="mt-1 text-sm text-red-600">{nameError}</p>}
            </div>

            <div className="flex justify-between items-center pt-4 border-t">
              <button
                type="button"
                onClick={handleUnlink}
                disabled={unlinking || submitting}
                className="flex items-center gap-2 px-4 py-2 text-red-600 border border-red-300 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {unlinking ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600" />
                ) : (
                  <Unlink size={16} />
                )}
                Unlink Device
              </button>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => router.push(`/agents/${agentName}/messaging-bots`)}
                  className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                  disabled={submitting || unlinking}
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeviceLinkSave}
                  disabled={submitting || unlinking}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {submitting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                      Saving...
                    </>
                  ) : (
                    "Save Changes"
                  )}
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* ── Cloud API edit form ── */
          <form onSubmit={handleCloudApiSubmit} className="bg-white rounded-lg shadow-sm p-6 space-y-6">
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
              <label htmlFor="access_token" className="block text-sm font-medium text-gray-700 mb-2">
                Access Token
              </label>
              <input
                type="password"
                id="access_token"
                value={formData.access_token}
                onChange={(e) => handleChange("access_token", e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Leave empty to keep current token"
              />
              <p className="mt-1 text-sm text-gray-500">
                Leave empty to keep the existing token, or enter a new one to update
              </p>
            </div>

            <div>
              <label htmlFor="verify_token" className="block text-sm font-medium text-gray-700 mb-2">
                Verify Token
              </label>
              <input
                type="text"
                id="verify_token"
                value={formData.verify_token}
                onChange={(e) => handleChange("verify_token", e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label htmlFor="webhook_url" className="block text-sm font-medium text-gray-700 mb-2">
                Webhook URL
              </label>
              <input
                type="text"
                id="webhook_url"
                value={formData.webhook_url}
                onChange={(e) => handleChange("webhook_url", e.target.value)}
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
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {submitting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                    Updating...
                  </>
                ) : (
                  "Update WhatsApp Bot"
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
