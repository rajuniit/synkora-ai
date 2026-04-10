"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, AlertCircle, MessageCircle, CheckCircle, Smartphone, Cloud } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { whatsappBotsApi } from "@/lib/api/messaging-bots";
import type { CreateWhatsAppBotRequest, WhatsAppQREvent } from "@/types/messaging-bots";

type ActiveTab = "cloud_api" | "device_link";
type QRStep = 1 | 2 | 3;

export default function CreateWhatsAppBotPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("cloud_api");

  // Cloud API form state
  const [formData, setFormData] = useState<CreateWhatsAppBotRequest>({
    agent_id: "",
    bot_name: "",
    phone_number_id: "",
    business_account_id: "",
    access_token: "",
    verify_token: "",
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // Device Link (QR) flow state
  const [agentId, setAgentId] = useState("");
  const [qrStep, setQrStep] = useState<QRStep>(1);
  const [qrBotName, setQrBotName] = useState("");
  const [qrBotNameError, setQrBotNameError] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [qrData, setQrData] = useState<string | null>(null);
  const [qrStatus, setQrStatus] = useState<string>("Waiting for QR code...");
  const [connectedPhone, setConnectedPhone] = useState<string | null>(null);
  const [qrError, setQrError] = useState<string | null>(null);
  const [startingQR, setStartingQR] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const loadAgent = async () => {
      try {
        const agent = await apiClient.getAgent(agentName);
        setAgentId(agent.id);
        setFormData((prev) => ({ ...prev, agent_id: agent.id }));
      } catch (err: any) {
        setError(err.response?.data?.message || "Failed to load agent");
      } finally {
        setLoading(false);
      }
    };
    loadAgent();
  }, [agentName]);

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      closeEventSource();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------------------
  // Cloud API helpers
  // ---------------------------------------------------------------------------

  const validateCloudForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!formData.bot_name.trim()) newErrors.bot_name = "Bot name is required";
    if (!formData.phone_number_id.trim()) newErrors.phone_number_id = "Phone number ID is required";
    if (!formData.business_account_id.trim()) newErrors.business_account_id = "WhatsApp Business Account ID is required";
    if (!formData.access_token.trim()) newErrors.access_token = "Access token is required";
    setFormErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleCloudSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateCloudForm()) return;
    setSubmitting(true);
    setError(null);
    try {
      await whatsappBotsApi.createBot(formData);
      router.push(`/agents/${agentName}/messaging-bots`);
    } catch (err: any) {
      setError(err.response?.data?.message || "Failed to create WhatsApp bot");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCloudChange = (field: keyof CreateWhatsAppBotRequest, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (formErrors[field]) setFormErrors((prev) => ({ ...prev, [field]: "" }));
  };

  // ---------------------------------------------------------------------------
  // Device Link (QR) helpers
  // ---------------------------------------------------------------------------

  const closeEventSource = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  };

  const handleStartQR = async () => {
    if (!qrBotName.trim()) {
      setQrBotNameError("Bot name is required");
      return;
    }
    setQrBotNameError("");
    setStartingQR(true);
    setQrError(null);

    try {
      const { session_id } = await whatsappBotsApi.startQRSession(agentId, qrBotName);
      setSessionId(session_id);
      setQrStep(2);
      setQrStatus("Waiting for QR code...");
      openEventSource(session_id);
    } catch (err: any) {
      setQrError(err.response?.data?.detail || "Failed to start QR session");
    } finally {
      setStartingQR(false);
    }
  };

  const openEventSource = (sid: string) => {
    closeEventSource();

    // Build the SSE URL — use the API base URL from the environment (matches http.ts)
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001";
    const url = `${baseUrl}/api/v1/whatsapp-bots/qr/${sid}/stream`;

    const es = new EventSource(url, { withCredentials: true });
    eventSourceRef.current = es;

    es.onmessage = async (event) => {
      try {
        const payload: WhatsAppQREvent = JSON.parse(event.data);

        if (payload.type === "qr" && payload.qr_data) {
          setQrData(payload.qr_data);
          setQrStatus("Scan the QR code with WhatsApp on your phone");
        } else if (payload.type === "status" && payload.status === "scanning") {
          setQrStatus("Scanning... keep your phone steady");
        } else if (payload.type === "connected") {
          setQrStatus("Connected!");
          es.close();
          eventSourceRef.current = null;
          // Auto-save the bot
          try {
            await whatsappBotsApi.saveQRBot(sid, agentId, qrBotName);
            setConnectedPhone(payload.phone_number || "Linked device");
            setQrStep(3);
          } catch (saveErr: any) {
            setQrError(saveErr.response?.data?.detail || "Connected but failed to save bot");
            setQrStep(1);
          }
        } else if (payload.type === "error") {
          setQrError(payload.message || "An error occurred");
          es.close();
          eventSourceRef.current = null;
          setQrStep(1);
        }
      } catch {
        // ignore JSON parse errors
      }
    };

    es.onerror = () => {
      setQrError("Connection to server lost. Please try again.");
      es.close();
      eventSourceRef.current = null;
      setQrStep(1);
    };
  };

  const handleCancelQR = async () => {
    closeEventSource();
    if (sessionId) {
      try {
        await whatsappBotsApi.cancelQRSession(sessionId);
      } catch {
        // best-effort cancel
      }
      setSessionId(null);
    }
    setQrStep(1);
    setQrData(null);
    setQrStatus("Waiting for QR code...");
    setQrError(null);
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.push(`/agents/${agentName}/messaging-bots`)}
            className="flex items-center text-red-600 hover:text-red-700 mb-4 text-sm font-medium"
          >
            <ArrowLeft size={16} className="mr-2" />
            Back to Messaging Bots
          </button>
          <div className="flex items-center gap-3">
            <div className="bg-emerald-100 p-2.5 rounded-lg">
              <MessageCircle className="text-emerald-600" size={20} />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Create WhatsApp Bot</h1>
              <p className="text-gray-600 mt-0.5 text-sm">Connect your agent to WhatsApp</p>
            </div>
          </div>
        </div>

        {/* Global error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-5 flex items-start">
            <AlertCircle className="text-red-600 mr-2 flex-shrink-0 mt-0.5" size={16} />
            <div>
              <h3 className="text-xs font-medium text-red-800">Error</h3>
              <p className="text-xs text-red-700 mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Tab bar */}
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg mb-5">
          <button
            type="button"
            onClick={() => setActiveTab("cloud_api")}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === "cloud_api"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <Cloud size={15} />
            Cloud API
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("device_link")}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === "device_link"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <Smartphone size={15} />
            Device Link (QR)
          </button>
        </div>

        {/* ------------------------------------------------------------------ */}
        {/* Cloud API Tab                                                       */}
        {/* ------------------------------------------------------------------ */}
        {activeTab === "cloud_api" && (
          <>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-5">
              <h3 className="text-xs font-medium text-blue-900 mb-2">Before you begin</h3>
              <ul className="text-xs text-blue-800 space-y-1 list-disc list-inside">
                <li>Create a Facebook Developer account at developers.facebook.com</li>
                <li>Set up WhatsApp Business API in your Facebook app</li>
                <li>Get your Phone Number ID and Access Token</li>
                <li>Configure webhook URL in Facebook dashboard</li>
              </ul>
              <a
                href="https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:text-blue-700 font-medium mt-2 inline-block"
              >
                View Setup Guide →
              </a>
            </div>

            <form onSubmit={handleCloudSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-5">
              {/* Bot Name */}
              <div>
                <label htmlFor="bot_name" className="block text-xs font-medium text-gray-700 mb-2">
                  Bot Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="bot_name"
                  value={formData.bot_name}
                  onChange={(e) => handleCloudChange("bot_name", e.target.value)}
                  className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent ${
                    formErrors.bot_name ? "border-red-500" : "border-gray-300"
                  }`}
                  placeholder="e.g., Customer Support Bot"
                />
                {formErrors.bot_name && <p className="mt-1 text-xs text-red-600">{formErrors.bot_name}</p>}
              </div>

              {/* Phone Number ID */}
              <div>
                <label htmlFor="phone_number_id" className="block text-xs font-medium text-gray-700 mb-2">
                  Phone Number ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="phone_number_id"
                  value={formData.phone_number_id}
                  onChange={(e) => handleCloudChange("phone_number_id", e.target.value)}
                  className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent ${
                    formErrors.phone_number_id ? "border-red-500" : "border-gray-300"
                  }`}
                  placeholder="123456789012345"
                />
                {formErrors.phone_number_id && (
                  <p className="mt-1 text-xs text-red-600">{formErrors.phone_number_id}</p>
                )}
                <p className="mt-1 text-xs text-gray-500">Find this in your WhatsApp Business API settings</p>
              </div>

              {/* WhatsApp Business Account ID */}
              <div>
                <label htmlFor="business_account_id" className="block text-xs font-medium text-gray-700 mb-2">
                  WhatsApp Business Account ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="business_account_id"
                  value={formData.business_account_id}
                  onChange={(e) => handleCloudChange("business_account_id", e.target.value)}
                  className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent ${
                    formErrors.business_account_id ? "border-red-500" : "border-gray-300"
                  }`}
                  placeholder="123456789012345"
                />
                {formErrors.business_account_id && (
                  <p className="mt-1 text-xs text-red-600">{formErrors.business_account_id}</p>
                )}
              </div>

              {/* Access Token */}
              <div>
                <label htmlFor="access_token" className="block text-xs font-medium text-gray-700 mb-2">
                  Access Token <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  id="access_token"
                  value={formData.access_token}
                  onChange={(e) => handleCloudChange("access_token", e.target.value)}
                  className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent ${
                    formErrors.access_token ? "border-red-500" : "border-gray-300"
                  }`}
                  placeholder="EAAxxxxxxxxxx..."
                />
                {formErrors.access_token && (
                  <p className="mt-1 text-xs text-red-600">{formErrors.access_token}</p>
                )}
                <p className="mt-1 text-xs text-gray-500">
                  Generate from your Facebook App settings (will be encrypted)
                </p>
              </div>

              {/* Webhook Verify Token */}
              <div>
                <label htmlFor="verify_token" className="block text-xs font-medium text-gray-700 mb-2">
                  Webhook Verify Token
                </label>
                <input
                  type="text"
                  id="verify_token"
                  value={formData.verify_token}
                  onChange={(e) => handleCloudChange("verify_token", e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="your_verify_token"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Optional: Use for webhook verification in Facebook dashboard
                </p>
              </div>

              {/* Webhook URL info */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-xs font-medium text-blue-900 mb-2">Webhook Configuration</h3>
                <p className="text-xs text-blue-800 mb-2">Configure this webhook URL in your Facebook App:</p>
                <code className="block bg-white border border-blue-300 rounded px-3 py-2 text-xs text-gray-800">
                  {typeof window !== "undefined" ? window.location.origin : ""}/api/v1/whatsapp/webhook
                </code>
              </div>

              {/* Actions */}
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
                  className="px-5 py-2 text-sm bg-gradient-to-r from-emerald-500 to-emerald-600 text-white rounded-lg hover:from-emerald-600 hover:to-emerald-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium shadow-sm"
                >
                  {submitting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Creating...
                    </>
                  ) : (
                    "Create WhatsApp Bot"
                  )}
                </button>
              </div>
            </form>
          </>
        )}

        {/* ------------------------------------------------------------------ */}
        {/* Device Link (QR) Tab                                                */}
        {/* ------------------------------------------------------------------ */}
        {activeTab === "device_link" && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            {/* Step 1 — bot name input */}
            {qrStep === 1 && (
              <div className="space-y-5">
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <h3 className="text-xs font-medium text-amber-900 mb-1">Link a device via QR code</h3>
                  <p className="text-xs text-amber-800">
                    This links a personal or business WhatsApp number by scanning a QR code — no Meta Business API
                    credentials required.
                  </p>
                </div>

                {qrError && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start">
                    <AlertCircle className="text-red-600 mr-2 flex-shrink-0 mt-0.5" size={16} />
                    <p className="text-xs text-red-700">{qrError}</p>
                  </div>
                )}

                <div>
                  <label htmlFor="qr_bot_name" className="block text-xs font-medium text-gray-700 mb-2">
                    Bot Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    id="qr_bot_name"
                    value={qrBotName}
                    onChange={(e) => {
                      setQrBotName(e.target.value);
                      if (qrBotNameError) setQrBotNameError("");
                    }}
                    className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent ${
                      qrBotNameError ? "border-red-500" : "border-gray-300"
                    }`}
                    placeholder="e.g., Support Bot"
                  />
                  {qrBotNameError && <p className="mt-1 text-xs text-red-600">{qrBotNameError}</p>}
                </div>

                <div className="flex justify-end gap-3 pt-3 border-t">
                  <button
                    type="button"
                    onClick={() => router.push(`/agents/${agentName}/messaging-bots`)}
                    className="px-5 py-2 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-white hover:border-red-300 transition-colors font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleStartQR}
                    disabled={startingQR}
                    className="px-5 py-2 text-sm bg-gradient-to-r from-emerald-500 to-emerald-600 text-white rounded-lg hover:from-emerald-600 hover:to-emerald-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium shadow-sm"
                  >
                    {startingQR ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        Starting...
                      </>
                    ) : (
                      <>
                        <Smartphone size={15} />
                        Generate QR Code
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Step 2 — QR display */}
            {qrStep === 2 && (
              <div className="space-y-5">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h3 className="text-xs font-medium text-blue-900 mb-1">How to link your device</h3>
                  <ol className="text-xs text-blue-800 space-y-1 list-decimal list-inside">
                    <li>Open WhatsApp on your phone</li>
                    <li>Tap Menu (⋮) or Settings → Linked Devices</li>
                    <li>Tap "Link a Device" and scan the QR code below</li>
                  </ol>
                </div>

                {qrError && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start">
                    <AlertCircle className="text-red-600 mr-2 flex-shrink-0 mt-0.5" size={16} />
                    <p className="text-xs text-red-700">{qrError}</p>
                  </div>
                )}

                {/* QR code area */}
                <div className="flex flex-col items-center py-6">
                  {qrData ? (
                    <img
                      src={`data:image/png;base64,${qrData}`}
                      alt="WhatsApp QR Code"
                      className="w-56 h-56 rounded-lg border border-gray-200 shadow-sm"
                    />
                  ) : (
                    <div className="w-56 h-56 flex items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
                    </div>
                  )}

                  {/* Status badge */}
                  <div className="mt-4 flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-amber-400 animate-pulse"></div>
                    <span className="text-xs text-gray-600">{qrStatus}</span>
                  </div>
                </div>

                <div className="flex justify-center pt-3 border-t">
                  <button
                    type="button"
                    onClick={handleCancelQR}
                    className="px-5 py-2 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-white hover:border-red-300 transition-colors font-medium"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Step 3 — success */}
            {qrStep === 3 && (
              <div className="flex flex-col items-center py-8 space-y-4">
                <div className="bg-emerald-100 p-4 rounded-full">
                  <CheckCircle className="text-emerald-600" size={40} />
                </div>
                <h2 className="text-lg font-semibold text-gray-900">Device Linked!</h2>
                <p className="text-sm text-gray-600">
                  Connected as <span className="font-medium text-gray-900">{connectedPhone}</span>
                </p>
                <button
                  type="button"
                  onClick={() => router.push(`/agents/${agentName}/messaging-bots`)}
                  className="mt-2 px-6 py-2.5 text-sm bg-gradient-to-r from-emerald-500 to-emerald-600 text-white rounded-lg hover:from-emerald-600 hover:to-emerald-700 transition-all font-medium shadow-sm"
                >
                  Go to Messaging Bots
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
