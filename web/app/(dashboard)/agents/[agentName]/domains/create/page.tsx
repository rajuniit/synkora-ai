"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Save, AlertCircle, CheckCircle, Copy, Globe } from "lucide-react";
import { createAgentDomain, getDNSRecords } from "@/lib/api/agent-domains";
import { AgentDomainCreate, AgentDomain, DNSRecordsResponse } from "@/types/agent-domain";
import toast from "react-hot-toast";

export default function CreateDomainPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdDomain, setCreatedDomain] = useState<AgentDomain | null>(null);
  const [dnsRecords, setDnsRecords] = useState<DNSRecordsResponse | null>(null);
  const [formData, setFormData] = useState<AgentDomainCreate>({
    is_custom_domain: true,
    subdomain: "",
    domain: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const domain = await createAgentDomain(agentName, formData);
      setCreatedDomain(domain);
      
      // Fetch DNS records to get the actual platform domain
      const records = await getDNSRecords(agentName, domain.id);
      setDnsRecords(records);
      
      toast.success("Domain created successfully!");
    } catch (err: any) {
      console.error("Failed to create domain:", err);
      setError(err.response?.data?.detail || err.message || "Failed to create domain");
      toast.error("Failed to create domain");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard!");
  };

  // Show DNS instructions after successful creation
  if (createdDomain && dnsRecords) {
    const fullDomain = createdDomain.subdomain 
      ? `${createdDomain.subdomain}.${createdDomain.domain}`
      : createdDomain.domain;

    // Find the CNAME record from the DNS records
    const cnameRecord = dnsRecords.records.find(record => record.type === 'CNAME');
    const platformDomain = dnsRecords.platform_domain;

    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 via-yellow-50/30 to-amber-50 p-6">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center shadow-sm">
                <CheckCircle className="w-6 h-6 text-emerald-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Domain Created Successfully!</h1>
                <p className="text-gray-600 mt-0.5 text-sm">Configure DNS to activate your custom domain</p>
              </div>
            </div>
          </div>

          {/* DNS Configuration Instructions */}
          <div className="space-y-5">
            {/* Domain Info */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Globe className="w-4 h-4 text-amber-600" />
                Your Domain
              </h2>
              <div className="flex items-center gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex-1">
                  <p className="text-xs text-amber-700 mb-1">Domain</p>
                  <p className="text-base font-mono font-semibold text-gray-900">{fullDomain}</p>
                </div>
                <button
                  onClick={() => copyToClipboard(fullDomain)}
                  className="p-2 hover:bg-amber-100 rounded-lg transition-colors"
                  title="Copy domain"
                >
                  <Copy className="w-4 h-4 text-amber-600" />
                </button>
              </div>
            </div>

            {/* DNS Configuration Steps */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-5">Setup Instructions</h2>
              
              <div className="space-y-5">
                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-amber-100 text-amber-700 rounded-full flex items-center justify-center font-semibold text-sm shadow-sm">
                    1
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1.5 text-sm">Add DNS Record</h3>
                    <p className="text-xs text-gray-600 mb-2">
                      Log in to your domain provider (e.g., GoDaddy, Namecheap, Cloudflare) and add the following DNS record:
                    </p>
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                      <div className="grid grid-cols-3 gap-3 text-xs mb-2">
                        <div>
                          <p className="text-gray-500 mb-1 text-xs">Type</p>
                          <p className="font-mono font-semibold text-gray-900 text-sm">CNAME</p>
                        </div>
                        <div>
                          <p className="text-gray-500 mb-1 text-xs">Name</p>
                          <p className="font-mono font-semibold text-gray-900 text-sm">{cnameRecord?.name || createdDomain.subdomain || "@"}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 mb-1 text-xs">Value</p>
                          <p className="font-mono font-semibold text-gray-900 text-sm">{cnameRecord?.value || platformDomain}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => copyToClipboard(`${cnameRecord?.name || createdDomain.subdomain || "@"} CNAME ${cnameRecord?.value || platformDomain}`)}
                        className="text-xs text-amber-600 hover:text-amber-700 flex items-center gap-1.5 font-medium"
                      >
                        <Copy className="w-3.5 h-3.5" />
                        Copy DNS record
                      </button>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-amber-100 text-amber-700 rounded-full flex items-center justify-center font-semibold text-sm shadow-sm">
                    2
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1.5 text-sm">Wait for DNS Propagation</h3>
                    <p className="text-xs text-gray-600">
                      DNS changes typically take 5-10 minutes to propagate, but can take up to 48 hours in some cases.
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-amber-100 text-amber-700 rounded-full flex items-center justify-center font-semibold text-sm shadow-sm">
                    3
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1.5 text-sm">Verify Domain</h3>
                    <p className="text-xs text-gray-600">
                      Once DNS propagates, return to the domains page and click "Verify" to activate your domain.
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-amber-100 text-amber-700 rounded-full flex items-center justify-center font-semibold text-sm shadow-sm">
                    4
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1.5 text-sm">Customize Chat Interface</h3>
                    <p className="text-xs text-gray-600">
                      After verification, you can customize the chat interface with your branding and colors.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Important Notes */}
            <div className="bg-amber-50 border border-amber-200 rounded-lg shadow-sm p-4">
              <h3 className="font-semibold text-amber-900 text-sm mb-2 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                Important Notes
              </h3>
              <ul className="space-y-1.5 text-xs text-amber-800">
                <li className="flex items-start gap-2">
                  <span className="text-amber-600 mt-0.5">•</span>
                  <span>SSL certificates will be automatically provisioned once the domain is verified</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-600 mt-0.5">•</span>
                  <span>Make sure to use the exact DNS record values provided above</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-600 mt-0.5">•</span>
                  <span>If using Cloudflare, disable the proxy (orange cloud) for the DNS record</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-600 mt-0.5">•</span>
                  <span>Contact support if you encounter any issues with DNS configuration</span>
                </li>
              </ul>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => router.push(`/agents/${agentName}/domains`)}
                className="px-5 py-2 text-sm bg-gradient-to-r from-amber-500 to-yellow-500 text-white rounded-lg hover:from-amber-600 hover:to-yellow-600 transition-all shadow-sm font-medium"
              >
                Go to Domains
              </button>
              <button
                onClick={() => router.push(`/agents/${agentName}/domains/${createdDomain.id}/edit`)}
                className="px-5 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-white hover:border-amber-300 transition-colors shadow-sm font-medium"
              >
                Customize Chat Interface
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-yellow-50/30 to-amber-50 p-6">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.push(`/agents/${agentName}/domains`)}
            className="flex items-center gap-2 text-amber-600 hover:text-amber-700 mb-4 transition-colors text-sm font-medium"
          >
            <ArrowLeft size={16} />
            Back to Domains
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Add Custom Domain</h1>
          <p className="text-gray-600 mt-1 text-sm">
            Configure a custom domain for your agent's chat interface
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-5 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-red-900 text-sm">Error</h3>
              <p className="text-red-700 text-xs mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-5">
            {/* Domain Type */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-2">
                Domain Type
              </label>
              <div className="space-y-2">
                <label className="flex items-start gap-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-amber-200 hover:bg-amber-50/50 transition-colors">
                  <input
                    type="radio"
                    checked={formData.is_custom_domain}
                    onChange={() =>
                      setFormData({ ...formData, is_custom_domain: true })
                    }
                    className="mt-0.5 w-4 h-4 text-amber-600 focus:ring-amber-500"
                  />
                  <div className="flex-1">
                    <span className="font-medium text-gray-900 block mb-0.5 text-sm">
                      Custom Domain
                    </span>
                    <span className="text-xs text-gray-600">
                      Use your own domain (e.g., chat.yourdomain.com)
                    </span>
                  </div>
                </label>
                <label className="flex items-start gap-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-amber-200 hover:bg-amber-50/50 transition-colors">
                  <input
                    type="radio"
                    checked={!formData.is_custom_domain}
                    onChange={() =>
                      setFormData({ ...formData, is_custom_domain: false })
                    }
                    className="mt-0.5 w-4 h-4 text-amber-600 focus:ring-amber-500"
                  />
                  <div className="flex-1">
                    <span className="font-medium text-gray-900 block mb-0.5 text-sm">
                      Platform Subdomain
                    </span>
                    <span className="text-xs text-gray-600">
                      Use a subdomain on our platform (e.g., yourname.platform.com)
                    </span>
                  </div>
                </label>
              </div>
            </div>

            {/* Custom Domain Fields */}
            {formData.is_custom_domain ? (
              <>
                <div>
                  <label
                    htmlFor="domain"
                    className="block text-xs font-medium text-gray-700 mb-2"
                  >
                    Domain Name *
                  </label>
                  <input
                    type="text"
                    id="domain"
                    value={formData.domain || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, domain: e.target.value })
                    }
                    placeholder="yourdomain.com"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Enter your root domain (e.g., yourdomain.com)
                  </p>
                </div>

                <div>
                  <label
                    htmlFor="subdomain"
                    className="block text-xs font-medium text-gray-700 mb-2"
                  >
                    Platform Subdomain *
                  </label>
                  <input
                    type="text"
                    id="subdomain"
                    value={formData.subdomain || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, subdomain: e.target.value })
                    }
                    placeholder="myagent"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Required: A platform subdomain is always needed for fallback access and DNS mapping (e.g., myagent.synkora.ai)
                  </p>
                </div>
              </>
            ) : (
              <div>
                <label
                  htmlFor="subdomain"
                  className="block text-xs font-medium text-gray-700 mb-2"
                >
                  Subdomain *
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    id="subdomain"
                    value={formData.subdomain || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, subdomain: e.target.value })
                    }
                    placeholder="yourname"
                    className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                    required
                  />
                  <span className="text-gray-600 text-sm">.platform.com</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Choose a unique subdomain for your agent
                </p>
              </div>
            )}

            {/* Info Box */}
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <h3 className="font-medium text-amber-900 mb-2 text-xs">Next Steps</h3>
              <ul className="space-y-1 text-xs text-amber-800">
                <li className="flex items-start gap-2">
                  <span className="text-amber-600 mt-0.5">•</span>
                  <span>After creating the domain, you'll receive DNS configuration instructions</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-600 mt-0.5">•</span>
                  <span>Add the required DNS records to your domain provider</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-600 mt-0.5">•</span>
                  <span>DNS verification typically takes 5-10 minutes</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-600 mt-0.5">•</span>
                  <span>Once verified, you can customize the chat interface</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 mt-5">
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2 text-sm bg-gradient-to-r from-amber-500 to-yellow-500 text-white rounded-lg hover:from-amber-600 hover:to-yellow-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm font-medium"
            >
              <Save className="w-4 h-4" />
              {loading ? "Creating..." : "Create Domain"}
            </button>
            <button
              type="button"
              onClick={() => router.push(`/agents/${agentName}/domains`)}
              className="px-5 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-white hover:border-amber-300 transition-colors shadow-sm font-medium"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
