"use client";

import { useState, useEffect } from "react";
import { extractErrorMessage } from '@/lib/api/error'
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle,
  Copy,
  ExternalLink,
  Shield,
  AlertCircle,
  Globe,
} from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { AgentDomain, DNSRecordsResponse } from "@/types/agent-domain";
import toast from "react-hot-toast";

export default function DomainInstructionsPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params.agentName as string;
  const domainId = params.domainId as string;

  const [domain, setDomain] = useState<AgentDomain | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    fetchDomain();
  }, [domainId]);

  useEffect(() => {
    if (domain && domain.is_custom_domain && !domain.is_verified) {
      fetchDNSRecords();
    }
  }, [domain]);

  const fetchDomain = async () => {
    try {
      setLoading(true);
      setError(null);

      const domainData = await apiClient.request(
        "GET",
        `/api/v1/agents/${agentName}/domains/${domainId}`
      );

      setDomain(domainData);
    } catch (err: any) {
      console.error("Failed to fetch domain:", err);
      setError(extractErrorMessage(err, "Failed to load domain"))
    } finally {
      setLoading(false);
    }
  };

  const [dnsRecords, setDnsRecords] = useState<any[]>([]);
  
  const fetchDNSRecords = async () => {
    try {
      const dnsData: DNSRecordsResponse = await apiClient.request(
        "GET",
        `/api/v1/agents/${agentName}/domains/${domainId}/dns-records`
      );
      
      setDnsRecords(dnsData.records || []);
    } catch (err: any) {
      console.error("Failed to fetch DNS records:", err);
      // Don't set error - this is not critical, we can fallback to showing placeholder
    }
  };

  const handleVerifyDomain = async () => {
    try {
      setVerifying(true);
      const result = await apiClient.request(
        "POST",
        `/api/v1/agents/${agentName}/domains/${domainId}/verify`
      );

      if (result.is_verified) {
        toast.success("Domain verified successfully!");
        await fetchDomain();
      } else {
        toast.error(
          result.message ||
            "Domain verification failed. Please check your DNS configuration."
        );
      }
    } catch (err: any) {
      toast.error(extractErrorMessage(err, "Failed to verify domain"))
    } finally {
      setVerifying(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard!");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading domain...</p>
        </div>
      </div>
    );
  }

  if (error || !domain) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-8">
        <div className="max-w-3xl mx-auto">
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-red-900">Error</h3>
              <p className="text-red-700 text-sm mt-1">
                {error || "Domain not found"}
              </p>
            </div>
          </div>
          <button
            onClick={() => router.push(`/agents/${agentName}/domains`)}
            className="flex items-center gap-2 text-amber-600 hover:text-amber-700 transition-colors text-sm font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Domains
          </button>
        </div>
      </div>
    );
  }

  // For custom domains: domain.domain is the custom domain (e.g., rajumazumder.com)
  // For platform domains: domain.subdomain + platform domain (e.g., test.synkora.ai)
  const platformSubdomain = domain.subdomain;
  
  // Display domain based on type
  const displayDomain = domain.is_custom_domain 
    ? domain.domain  // Show custom domain: rajumazumder.com
    : (domain.subdomain ? `${domain.subdomain}.synkora.ai` : 'synkora.ai'); // Show platform subdomain
  
  const fullDomain = displayDomain;

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.push(`/agents/${agentName}/domains`)}
            className="flex items-center gap-2 text-amber-600 hover:text-amber-700 mb-4 transition-colors text-sm font-medium"
          >
            <ArrowLeft size={16} />
            Back to Domains
          </button>
          <div className="flex items-center gap-3 mb-4">
            <div
              className={`w-12 h-12 rounded-full flex items-center justify-center shadow-sm ${
                domain.is_verified
                  ? "bg-emerald-100"
                  : "bg-amber-100"
              }`}
            >
              {domain.is_verified ? (
                <CheckCircle className="w-6 h-6 text-emerald-600" />
              ) : (
                <AlertCircle className="w-6 h-6 text-amber-600" />
              )}
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">
                DNS Configuration
              </h1>
              <p className="text-gray-600 mt-0.5 text-sm">
                {domain.is_verified
                  ? "Your domain is verified and active"
                  : "Configure DNS to activate your custom domain"}
              </p>
            </div>
          </div>
        </div>

        {/* Domain Info */}
        <div className="space-y-5">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Globe className="w-4 h-4 text-amber-600" />
              Your Domain
            </h2>
            <div className="flex items-center gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex-1">
                <p className="text-xs text-amber-700 mb-1">Domain</p>
                <p className="text-base font-mono font-semibold text-gray-900">
                  {fullDomain}
                </p>
              </div>
              <button
                onClick={() => copyToClipboard(fullDomain)}
                className="p-2 hover:bg-amber-100 rounded-lg transition-colors"
                title="Copy domain"
              >
                <Copy className="w-4 h-4 text-amber-600" />
              </button>
              {domain.is_verified && (
                <a
                  href={`https://${fullDomain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 hover:bg-amber-100 rounded-lg transition-colors"
                  title="Visit domain"
                >
                  <ExternalLink className="w-4 h-4 text-amber-600" />
                </a>
              )}
            </div>
          </div>

          {/* Domain Mapping Info for Custom Domains */}
          {domain.is_custom_domain && platformSubdomain && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl shadow-sm p-4">
              <h3 className="font-semibold text-blue-900 text-sm mb-2 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                How It Works
              </h3>
              <p className="text-xs text-blue-800 mb-2">
                Your custom domain <span className="font-mono font-semibold">{domain.domain}</span> will point to your agent hosted at <span className="font-mono font-semibold">{platformSubdomain}.synkora.ai</span>.
              </p>
              <p className="text-xs text-blue-800">
                This means visitors can access your agent through your own domain while it's actually served from our platform infrastructure.
              </p>
            </div>
          )}

          {/* DNS Configuration Steps */}
          {!domain.is_verified && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-5">Setup Instructions</h2>

              <div className="space-y-5">
                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-amber-100 text-amber-700 rounded-full flex items-center justify-center font-semibold text-sm shadow-sm">
                    1
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1.5 text-sm">
                      Add DNS Records
                    </h3>
                    <p className="text-xs text-gray-600 mb-2">
                      Log in to your domain provider (e.g., GoDaddy, Namecheap,
                      Cloudflare) and add the following TWO DNS records:
                    </p>
                    
                    {dnsRecords.length > 0 ? (
                      <div className="space-y-3">
                        {dnsRecords.map((record, index) => (
                          <div key={index} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                            <div className="flex items-center gap-2 mb-2">
                              <div className="px-2 py-1 bg-amber-100 text-amber-700 text-xs font-semibold rounded">
                                Record {index + 1}
                              </div>
                              <span className="text-xs text-gray-500">{record.purpose}</span>
                            </div>
                            <div className="grid grid-cols-3 gap-3 text-xs mb-2">
                              <div>
                                <p className="text-gray-500 mb-1 text-xs">Type</p>
                                <p className="font-mono font-semibold text-gray-900 text-sm">{record.type}</p>
                              </div>
                              <div>
                                <p className="text-gray-500 mb-1 text-xs">Name</p>
                                <p className="font-mono font-semibold text-gray-900 text-sm break-all">
                                  {record.name}
                                </p>
                              </div>
                              <div>
                                <p className="text-gray-500 mb-1 text-xs">Value</p>
                                <p className="font-mono font-semibold text-gray-900 text-sm break-all">
                                  {record.value}
                                </p>
                              </div>
                            </div>
                            <button
                              onClick={() => copyToClipboard(`${record.name} ${record.type} ${record.value}`)}
                              className="text-xs text-amber-600 hover:text-amber-700 flex items-center gap-1.5 font-medium"
                            >
                              <Copy className="w-3.5 h-3.5" />
                              Copy record
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                        <p className="text-sm text-gray-500">Loading DNS records...</p>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-amber-100 text-amber-700 rounded-full flex items-center justify-center font-semibold text-sm shadow-sm">
                    2
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1.5 text-sm">
                      Wait for DNS Propagation
                    </h3>
                    <p className="text-xs text-gray-600">
                      DNS changes typically take 5-10 minutes to propagate, but
                      can take up to 48 hours in some cases.
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-amber-100 text-amber-700 rounded-full flex items-center justify-center font-semibold text-sm shadow-sm">
                    3
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1.5 text-sm">
                      Verify Domain
                    </h3>
                    <p className="text-xs text-gray-600 mb-3">
                      Once DNS propagates, click the verify button below to
                      activate your domain.
                    </p>
                    <button
                      onClick={handleVerifyDomain}
                      disabled={verifying}
                      className="flex items-center gap-2 px-5 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm font-medium"
                    >
                      <Shield className="w-4 h-4" />
                      {verifying ? "Verifying..." : "Verify Domain"}
                    </button>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-amber-100 text-amber-700 rounded-full flex items-center justify-center font-semibold text-sm shadow-sm">
                    4
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1.5 text-sm">
                      Customize Chat Interface
                    </h3>
                    <p className="text-xs text-gray-600">
                      After verification, you can customize the chat interface
                      with your branding and colors.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Verified Status */}
          {domain.is_verified && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl shadow-sm p-5">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h3 className="font-semibold text-emerald-900 mb-1.5 text-sm">
                    Domain Verified Successfully!
                  </h3>
                  <p className="text-emerald-800 text-xs mb-3">
                    Your domain is now active and ready to use. You can customize
                    the chat interface or visit your domain.
                  </p>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() =>
                        router.push(`/agents/${agentName}/chat-customization`)
                      }
                      className="px-5 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors shadow-sm font-medium"
                    >
                      Customize Chat Interface
                    </button>
                    <a
                      href={`https://${fullDomain}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 px-5 py-2 text-sm text-emerald-700 bg-white border border-emerald-300 rounded-lg hover:bg-emerald-50 transition-colors shadow-sm font-medium"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Visit Domain
                    </a>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* DNS Configuration Info */}
          {domain.subdomain && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl shadow-sm p-4">
              <h3 className="font-semibold text-blue-900 text-sm mb-2 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                Domain Configuration
              </h3>
              <p className="text-xs text-blue-800 mb-2">
                Your agent is currently configured to be served from <span className="font-mono font-semibold">{fullDomain}</span>.
              </p>
              <p className="text-xs text-blue-800">
                If you want to serve your agent from the root domain (<span className="font-mono font-semibold">{domain.domain}</span>) instead, 
                please <button 
                  onClick={() => router.push(`/agents/${agentName}/domains/${domainId}/edit`)}
                  className="text-blue-600 hover:text-blue-700 underline font-medium"
                >edit the domain settings</button> and leave the subdomain field empty.
              </p>
            </div>
          )}

          {/* Important Notes */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl shadow-sm p-4">
            <h3 className="font-semibold text-amber-900 text-sm mb-2 flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              Important Notes
            </h3>
            <ul className="space-y-1.5 text-xs text-amber-800">
              <li className="flex items-start gap-2">
                <span className="text-amber-600 mt-0.5">•</span>
                <span>
                  SSL certificates will be automatically provisioned once the domain
                  is verified
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 mt-0.5">•</span>
                <span>
                  Make sure to use the exact DNS record values provided above
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 mt-0.5">•</span>
                <span>
                  If using Cloudflare, disable the proxy (orange cloud) for the DNS
                  record
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600 mt-0.5">•</span>
                <span>
                  Contact support if you encounter any issues with DNS configuration
                </span>
              </li>
            </ul>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => router.push(`/agents/${agentName}/domains`)}
              className="px-5 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-white hover:border-amber-300 transition-colors shadow-sm font-medium"
            >
              Back to Domains
            </button>
            {domain.is_verified && (
              <button
                onClick={() =>
                  router.push(`/agents/${agentName}/chat-customization`)
                }
                className="px-5 py-2 text-sm bg-gradient-to-r from-amber-500 to-yellow-500 text-white rounded-lg hover:from-amber-600 hover:to-yellow-600 transition-all shadow-sm font-medium"
              >
                Customize Chat Interface
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
