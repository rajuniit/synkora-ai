"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Shield,
  GitBranch,
  RefreshCw,
  Copy,
  Eye,
  EyeOff,
  Plus,
  Trash2,
  ChevronDown,
  CheckCircle,
  AlertTriangle,
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
}

interface AgentRoute {
  external_org_id: string;
  agent_id: string;
  agent_name?: string;
}

interface Agent {
  id: string;
  agent_name: string;
}

export default function WidgetEditPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;
  const widgetId = params.widgetId as string;

  const [widget, setWidget] = useState<Widget | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [routes, setRoutes] = useState<AgentRoute[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Basic settings
  const [widgetName, setWidgetName] = useState("");
  const [allowedDomains, setAllowedDomains] = useState("");
  const [rateLimit, setRateLimit] = useState(100);
  const [isActive, setIsActive] = useState(true);

  // Identity verification
  const [identityVerificationRequired, setIdentityVerificationRequired] = useState(false);
  const [identitySecret, setIdentitySecret] = useState<string | null>(null);
  const [showSecret, setShowSecret] = useState(false);
  const [regeneratingSecret, setRegeneratingSecret] = useState(false);

  // Agent routing
  const [enableAgentRouting, setEnableAgentRouting] = useState(false);
  const [newOrgId, setNewOrgId] = useState("");
  const [newAgentId, setNewAgentId] = useState("");
  const [addingRoute, setAddingRoute] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [widgetData, routesData, agentsData] = await Promise.all([
        apiClient.getWidget(widgetId),
        apiClient.getWidgetRoutes(widgetId),
        apiClient.getAgents(),
      ]);

      setWidget(widgetData);
      setWidgetName(widgetData.widget_name || "");
      setAllowedDomains((widgetData.allowed_domains || []).join(", "));
      setRateLimit(widgetData.rate_limit || 100);
      setIsActive(widgetData.is_active ?? true);
      setIdentityVerificationRequired(widgetData.identity_verification_required ?? false);
      setEnableAgentRouting(widgetData.enable_agent_routing ?? false);

      const agentList: Agent[] = Array.isArray(agentsData) ? agentsData : agentsData?.agents_list || [];
      setAgents(agentList);

      const enriched = routesData.map((r: AgentRoute) => ({
        ...r,
        agent_name: agentList.find((a) => a.id === r.agent_id)?.agent_name || r.agent_id,
      }));
      setRoutes(enriched);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load widget");
    } finally {
      setLoading(false);
    }
  }, [widgetId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const domains = allowedDomains
        .split(",")
        .map((d) => d.trim())
        .filter(Boolean);
      await apiClient.updateWidget(widgetId, {
        widget_name: widgetName,
        allowed_domains: domains.length > 0 ? domains : null,
        rate_limit: rateLimit,
        is_active: isActive,
        identity_verification_required: identityVerificationRequired,
        enable_agent_routing: enableAgentRouting,
      });
      toast.success("Widget settings saved");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleRegenerateSecret = async () => {
    if (
      !confirm(
        "Regenerate the identity secret?\n\nAny existing server-side integrations using the old secret will stop working immediately."
      )
    )
      return;
    setRegeneratingSecret(true);
    try {
      const result = await apiClient.regenerateIdentitySecret(widgetId);
      setIdentitySecret(result.data?.identity_secret || null);
      setShowSecret(true);
      toast.success("New secret generated — copy it now, it won't be shown again");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to regenerate secret");
    } finally {
      setRegeneratingSecret(false);
    }
  };

  const handleAddRoute = async () => {
    if (!newOrgId.trim() || !newAgentId) {
      toast.error("Org ID and agent are required");
      return;
    }
    setAddingRoute(true);
    try {
      const updated = [
        ...routes.map((r) => ({ external_org_id: r.external_org_id, agent_id: r.agent_id })),
        { external_org_id: newOrgId.trim(), agent_id: newAgentId },
      ];
      await apiClient.setWidgetRoutes(widgetId, updated);
      const resolvedAgentName = agents.find((a) => a.id === newAgentId)?.agent_name || newAgentId;
      setRoutes([...routes, { external_org_id: newOrgId.trim(), agent_id: newAgentId, agent_name: resolvedAgentName }]);
      setNewOrgId("");
      setNewAgentId("");
      toast.success("Route added");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to add route");
    } finally {
      setAddingRoute(false);
    }
  };

  const handleDeleteRoute = async (orgId: string) => {
    try {
      await apiClient.deleteWidgetRoute(widgetId, orgId);
      setRoutes(routes.filter((r) => r.external_org_id !== orgId));
      toast.success("Route removed");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to remove route");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => toast.success("Copied to clipboard"));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (!widget) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
        <div className="max-w-2xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 text-sm">Widget not found.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-2xl mx-auto">

        {/* Header */}
        <div className="mb-6">
          <Link
            href={`/agents/${agentName}/widgets`}
            className="inline-flex items-center text-primary-600 hover:text-primary-700 text-sm font-medium mb-4 transition-colors"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Widgets
          </Link>
          <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Edit Widget</h1>
          <p className="text-gray-600 mt-1 text-sm">
            Update settings for <span className="font-semibold">{widget.widget_name}</span>
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-6">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-6">

          {/* ── General ───────────────────────────────────────────────────────── */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">General</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Widget name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={widgetName}
                  onChange={(e) => setWidgetName(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Allowed domains
                  <span className="ml-1 font-normal text-gray-500">(comma-separated, leave blank to allow all)</span>
                </label>
                <input
                  type="text"
                  value={allowedDomains}
                  onChange={(e) => setAllowedDomains(e.target.value)}
                  placeholder="app.example.com, *.example.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Rate limit <span className="font-normal text-gray-500">(requests / hour)</span>
                </label>
                <input
                  type="number"
                  min={1}
                  max={10000}
                  value={rateLimit}
                  onChange={(e) => setRateLimit(Number(e.target.value))}
                  className="w-32 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                    className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-700">Widget is active</span>
                </label>
                <p className="mt-1 text-xs text-gray-500 ml-6">Inactive widgets stop accepting all traffic</p>
              </div>
            </div>
          </div>

          {/* ── Identity Verification ─────────────────────────────────────────── */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-2 mb-1">
              <Shield className="h-5 w-5 text-primary-600" />
              <h2 className="text-lg font-semibold text-gray-900">Identity Verification</h2>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Prevent end-users from impersonating each other using HMAC signatures generated on your server.
            </p>

            {/* Toggle */}
            <div className="mb-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={identityVerificationRequired}
                  onChange={(e) => setIdentityVerificationRequired(e.target.checked)}
                  className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">Require identity verification on every request</span>
              </label>
              <p className="mt-1 text-xs text-gray-500 ml-6">
                When enabled, requests without a valid{" "}
                <code className="bg-gray-100 px-1 rounded">userHash</code> are rejected with HTTP 403.
              </p>
            </div>

            {identityVerificationRequired && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4 flex gap-2 text-xs text-amber-800">
                <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <span>
                  Make sure your server is generating the hash before enabling this, otherwise all widget traffic will be blocked.
                </span>
              </div>
            )}

            {/* Secret */}
            <div className="border-t border-gray-200 pt-4 space-y-2">
              <h3 className="text-sm font-medium text-gray-700">Identity secret</h3>
              <p className="text-xs text-gray-500">
                Compute <code className="bg-gray-100 px-1 rounded">HMAC-SHA256(secret, userId)</code> on your server and pass
                it as <code className="bg-gray-100 px-1 rounded">userHash</code> in the widget init call.{" "}
                <span className="font-medium text-gray-700">Never expose this secret in the browser.</span>
              </p>

              {identitySecret ? (
                <div className="flex items-center gap-2 bg-green-50 border border-green-300 rounded-lg px-3 py-2">
                  <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
                  <code className="text-xs text-green-800 break-all flex-1">
                    {showSecret ? identitySecret : "•".repeat(44)}
                  </code>
                  <button
                    type="button"
                    onClick={() => setShowSecret(!showSecret)}
                    className="text-green-600 hover:text-green-800 transition-colors"
                  >
                    {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(identitySecret)}
                    className="text-green-600 hover:text-green-800 transition-colors"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <p className="text-xs text-gray-500 italic">
                  The secret was shown when this widget was created. Use the button below to rotate it.
                </p>
              )}

              <button
                type="button"
                onClick={handleRegenerateSecret}
                disabled={regeneratingSecret}
                className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-red-600 transition-colors disabled:opacity-50 font-medium"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${regeneratingSecret ? "animate-spin" : ""}`} />
                Regenerate secret
              </button>
            </div>

            {/* Code examples */}
            <details className="mt-4 group">
              <summary className="flex items-center gap-1.5 text-sm font-medium text-gray-600 cursor-pointer select-none list-none">
                <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
                Server-side code examples
              </summary>
              <div className="mt-3 space-y-2">
                {[
                  {
                    lang: "Node.js",
                    code: `const crypto = require("crypto");\nconst hash = crypto\n  .createHmac("sha256", process.env.WIDGET_IDENTITY_SECRET)\n  .update(user.id)\n  .digest("hex");`,
                  },
                  {
                    lang: "Python",
                    code: `import hmac, hashlib\nhash = hmac.new(\n    os.environ["WIDGET_IDENTITY_SECRET"].encode(),\n    user_id.encode(),\n    hashlib.sha256\n).hexdigest()`,
                  },
                  {
                    lang: "PHP",
                    code: `$hash = hash_hmac("sha256", $userId, $_ENV["WIDGET_IDENTITY_SECRET"]);`,
                  },
                  {
                    lang: "Ruby",
                    code: `require "openssl"\nhash = OpenSSL::HMAC.hexdigest("SHA256", ENV["WIDGET_IDENTITY_SECRET"], user_id)`,
                  },
                ].map(({ lang, code }) => (
                  <div key={lang} className="rounded-lg bg-gray-900 overflow-hidden text-xs">
                    <div className="flex items-center justify-between bg-gray-800 px-3 py-1.5">
                      <span className="text-gray-400 text-[11px] uppercase tracking-wide">{lang}</span>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(code)}
                        className="text-gray-400 hover:text-white transition-colors"
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <pre className="p-3 text-green-300 overflow-x-auto leading-relaxed">{code}</pre>
                  </div>
                ))}

                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs text-gray-600">
                  <p className="font-medium mb-1.5">Widget init with identity verification:</p>
                  <pre className="bg-white border border-gray-200 rounded p-2 text-[11px] overflow-x-auto whitespace-pre">{`SynkoraWidget.init({
  widgetId:  "your-widget-id",
  apiKey:    "swk_...",
  user:      { id: currentUser.id, name: currentUser.name, orgId: currentOrg.id },
  userHash:  "{{ hash computed on your server }}",
});`}</pre>
                </div>
              </div>
            </details>
          </div>

          {/* ── Agent Routing ─────────────────────────────────────────────────── */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-2 mb-1">
              <GitBranch className="h-5 w-5 text-primary-600" />
              <h2 className="text-lg font-semibold text-gray-900">Agent Routing</h2>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Route different customer orgs to different agents — each with their own knowledge base, prompts, and tools.
            </p>

            {/* Toggle */}
            <div className="mb-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={enableAgentRouting}
                  onChange={(e) => setEnableAgentRouting(e.target.checked)}
                  className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">Enable org-based agent routing</span>
              </label>
              <p className="mt-1 text-xs text-gray-500 ml-6">
                When enabled, requests with a <code className="bg-gray-100 px-1 rounded">user.orgId</code> are routed using
                the table below. Unmatched orgs fall back to this widget&apos;s default agent.
              </p>
            </div>

            {enableAgentRouting && (
              <div className="border-t border-gray-200 pt-4 space-y-4">
                {/* Routes table */}
                {routes.length > 0 ? (
                  <div className="rounded-lg border border-gray-200 overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                            Org ID
                          </th>
                          <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                            Agent
                          </th>
                          <th className="px-4 py-2.5 w-10" />
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {routes.map((route) => (
                          <tr key={route.external_org_id} className="hover:bg-gray-50">
                            <td className="px-4 py-3">
                              <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{route.external_org_id}</code>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-700">{route.agent_name || route.agent_id}</td>
                            <td className="px-4 py-3 text-right">
                              <button
                                type="button"
                                onClick={() => handleDeleteRoute(route.external_org_id)}
                                className="text-gray-400 hover:text-red-500 transition-colors"
                                title="Remove route"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 italic">
                    No routes yet. All orgs will use this widget&apos;s default agent.
                  </p>
                )}

                {/* Add route */}
                <div className="flex items-end gap-2">
                  <div className="flex-1">
                    <label className="block text-xs font-medium text-gray-600 mb-1">Org ID</label>
                    <input
                      type="text"
                      value={newOrgId}
                      onChange={(e) => setNewOrgId(e.target.value)}
                      placeholder="e.g. acme, org_123"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          handleAddRoute();
                        }
                      }}
                    />
                  </div>
                  <div className="flex-1">
                    <label className="block text-xs font-medium text-gray-600 mb-1">Route to agent</label>
                    <select
                      value={newAgentId}
                      onChange={(e) => setNewAgentId(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white"
                    >
                      <option value="">Select agent…</option>
                      {agents.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.agent_name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="button"
                    onClick={handleAddRoute}
                    disabled={addingRoute || !newOrgId.trim() || !newAgentId}
                    className="flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-lg text-sm font-medium hover:from-primary-600 hover:to-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    <Plus className="h-4 w-4" />
                    Add
                  </button>
                </div>

                <div className="bg-primary-50 border border-primary-200 rounded-lg p-3 text-xs text-primary-800">
                  Pass <code className="bg-primary-100 px-1 rounded">user.orgId</code> in{" "}
                  <code className="bg-primary-100 px-1 rounded">SynkoraWidget.init()</code> to activate routing. Orgs not
                  listed above fall back to the widget&apos;s default agent.
                </div>
              </div>
            )}
          </div>

          {/* ── Actions ───────────────────────────────────────────────────────── */}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 px-4 py-2 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-lg text-sm font-medium hover:from-primary-600 hover:to-primary-700 transition-all disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save Changes"}
            </button>
            <Link
              href={`/agents/${agentName}/widgets`}
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
