"use client";

import { useState, useEffect } from "react";
import { extractErrorMessage } from '@/lib/api/error'
import { useParams, useRouter } from "next/navigation";
import {
  Plus,
  Trash2,
  Edit,
  Copy,
  RefreshCw,
  Eye,
  BarChart3,
  Globe,
  Key,
  AlertCircle,
  ArrowLeft,
  ChevronRight,
} from "lucide-react";
import { apiClient } from "@/lib/api/client";
import toast from "react-hot-toast";

interface Widget {
  widget_id: string;
  widget_name: string;
  agent_id: string;
  agent_name: string;
  allowed_domains: string[] | null;
  rate_limit: number;
  is_active: boolean;
  identity_verification_required: boolean;
  enable_agent_routing: boolean;
  created_at: string;
  updated_at: string;
}

export default function AgentWidgetsPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;

  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEmbedCode, setShowEmbedCode] = useState(false);
  const [embedCode, setEmbedCode] = useState("");

  useEffect(() => {
    fetchWidgets();
  }, [agentName]);

  const fetchWidgets = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get agent details using agents endpoint
      const agentResponse = await apiClient.request('GET', `/api/v1/agents/${agentName}`);
      
      if (!agentResponse.success || !agentResponse.data) {
        setError("Agent not found");
        return;
      }

      // Fetch widgets for this agent using the agent ID
      const widgets = await apiClient.getWidgets(agentResponse.data.id);
      setWidgets(widgets);
    } catch (err: any) {
      console.error("Failed to fetch widgets:", err);
      setError(extractErrorMessage(err, "Failed to load widgets"))
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteWidget = async (widgetId: string) => {
    if (!confirm("Are you sure you want to delete this widget?")) {
      return;
    }

    try {
      await apiClient.deleteWidget(widgetId);
      await fetchWidgets();
      toast.success("Widget deleted");
    } catch (err: any) {
      toast.error(extractErrorMessage(err, "Failed to delete widget"))
    }
  };

  const handleRegenerateKey = async (widgetId: string) => {
    if (!confirm("Are you sure you want to regenerate the API key? The old key will stop working.")) {
      return;
    }

    try {
      await apiClient.regenerateWidgetKey(widgetId);
      await fetchWidgets();
      toast.success("API key regenerated successfully");
    } catch (err: any) {
      toast.error(extractErrorMessage(err, "Failed to regenerate API key"))
    }
  };

  const handleShowEmbedCode = async (widgetId: string) => {
    try {
      const response = await apiClient.getWidgetEmbedCode(widgetId);
      setEmbedCode(response.data?.embed_code || response.embed_code);
      setShowEmbedCode(true);
    } catch (err: any) {
      toast.error(extractErrorMessage(err, "Failed to get embed code"))
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard!");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
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
        <span className="text-gray-900 font-medium">Widgets</span>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <button
            onClick={() => router.push(`/agents/${encodeURIComponent(agentName)}/view`)}
            className="inline-flex items-center gap-2 text-red-600 hover:text-red-700 font-medium mb-2 transition-colors text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Agent
          </button>
          <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Agent Widgets</h1>
          <p className="text-gray-600 mt-1 text-sm">
            Embed your agent <span className="font-semibold">{agentName}</span> on external websites
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all text-xs font-medium shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Create Widget
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-red-900 text-sm">Error</h3>
            <p className="text-red-700 text-xs mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Widgets List */}
      {widgets.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border-2 border-dashed border-red-300 shadow-sm">
          <Globe className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <h3 className="text-base font-medium text-gray-900 mb-2">
            No widgets yet
          </h3>
          <p className="text-gray-600 text-sm mb-4">
            Create your first widget to embed this agent on external websites
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all text-xs font-medium shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Create Widget
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {widgets.map((widget) => (
            <div
              key={widget.widget_id}
              className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-red-300 transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-3">
                    <h3 className="text-base font-semibold text-gray-900">
                      {widget.widget_name}
                    </h3>
                    <span
                      className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                        widget.is_active
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {widget.is_active ? "Active" : "Inactive"}
                    </span>
                    {widget.identity_verification_required && (
                      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-800">
                        Identity verified
                      </span>
                    )}
                    {widget.enable_agent_routing && (
                      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                        Routing on
                      </span>
                    )}
                  </div>

                  <div className="space-y-1.5 text-xs text-gray-600">
                    <div className="flex items-center gap-2">
                      <Globe className="w-3.5 h-3.5" />
                      <span>
                        Domains:{" "}
                        {widget.allowed_domains && widget.allowed_domains.length > 0
                          ? widget.allowed_domains.join(", ")
                          : "All domains allowed"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <BarChart3 className="w-3.5 h-3.5" />
                      <span>Rate limit: {widget.rate_limit} requests/hour</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Key className="w-3.5 h-3.5" />
                      <span className="font-mono">
                        Created: {new Date(widget.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleShowEmbedCode(widget.widget_id)}
                    className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="View embed code"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleRegenerateKey(widget.widget_id)}
                    className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Regenerate API key"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => router.push(`/agents/${agentName}/widgets/${widget.widget_id}/edit`)}
                    className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Edit widget"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDeleteWidget(widget.widget_id)}
                    className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Delete widget"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Embed Code Modal */}
      {showEmbedCode && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">Embed Code</h2>
                <button
                  onClick={() => setShowEmbedCode(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <p className="text-gray-600 text-sm mb-4">
                Copy and paste this code into your website's HTML:
              </p>

              <div className="relative">
                <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-xs">
                  <code>{embedCode}</code>
                </pre>
                <button
                  onClick={() => copyToClipboard(embedCode)}
                  className="absolute top-2 right-2 p-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
                  title="Copy to clipboard"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>

              <div className="mt-5 p-4 bg-red-50 border border-red-200 rounded-lg">
                <h3 className="font-medium text-red-900 text-sm mb-2">Setup Instructions</h3>
                <ol className="list-decimal list-inside space-y-1 text-xs text-red-800">
                  <li>Copy the embed code above</li>
                  <li>Paste it into your website's HTML where you want the widget to appear</li>
                  <li>The widget will automatically load and connect to your agent</li>
                  <li>Customize the theme in the widget settings if needed</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Widget Modal */}
      {showCreateModal && (
        <CreateWidgetModal
          agentName={agentName}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            fetchWidgets();
          }}
        />
      )}
      </div>
    </div>
  );
}

// Create Widget Modal Component
function CreateWidgetModal({
  agentName,
  onClose,
  onSuccess,
}: {
  agentName: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [formData, setFormData] = useState({
    widget_name: "",
    allowed_domains: "",
    rate_limit: 100,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Get agent ID using the agents endpoint
      const agentResponse = await apiClient.request('GET', `/api/v1/agents/${agentName}`);
      
      if (!agentResponse.success || !agentResponse.data) {
        throw new Error("Agent not found");
      }

      // Parse domains
      const domains = formData.allowed_domains
        .split(",")
        .map((d) => d.trim())
        .filter((d) => d.length > 0);

      // Create widget
      await apiClient.createWidget({
        agent_id: agentResponse.data.id,
        widget_name: formData.widget_name,
        allowed_domains: domains.length > 0 ? domains : null,
        rate_limit: formData.rate_limit,
      });

      onSuccess();
    } catch (err: any) {
      console.error("Failed to create widget:", err);
      setError(extractErrorMessage(err, err.message || "Failed to create widget"))
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full">
        <div className="p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Create Widget</h2>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Widget Name *
              </label>
              <input
                type="text"
                value={formData.widget_name}
                onChange={(e) =>
                  setFormData({ ...formData, widget_name: e.target.value })
                }
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="My Website Widget"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Allowed Domains
              </label>
              <input
                type="text"
                value={formData.allowed_domains}
                onChange={(e) =>
                  setFormData({ ...formData, allowed_domains: e.target.value })
                }
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="example.com, *.example.com (leave empty for all)"
              />
              <p className="text-xs text-gray-500 mt-1">
                Comma-separated list. Use * for wildcards. Leave empty to allow all domains.
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Rate Limit (requests/hour)
              </label>
              <input
                type="number"
                value={formData.rate_limit}
                onChange={(e) =>
                  setFormData({ ...formData, rate_limit: parseInt(e.target.value) })
                }
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                min="1"
                max="10000"
                required
              />
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-red-50 hover:border-red-300 transition-colors"
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 px-4 py-2 text-sm bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all disabled:opacity-50 font-medium shadow-sm"
                disabled={loading}
              >
                {loading ? "Creating..." : "Create Widget"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
