'use client';

import { useState } from 'react';
import { Save, Loader2, AlertCircle, Info } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useOAuthApps } from '@/hooks/useAgentOutputs';
import toast from 'react-hot-toast';
import type {
  OutputConfig,
  CreateOutputConfigData,
  OutputProvider,
  SlackOutputConfig,
  EmailOutputConfig,
  WebhookOutputConfig,
} from '@/types/agent-outputs';

interface OutputConfigFormProps {
  output?: OutputConfig;
  onSubmit: (data: CreateOutputConfigData) => Promise<void>;
  onCancel: () => void;
}

export function OutputConfigForm({ output, onSubmit, onCancel }: OutputConfigFormProps) {
  const { oauthApps, getAppsByProvider } = useOAuthApps();
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState<OutputProvider>(output?.provider || 'slack');
  
  // Form fields
  const [name, setName] = useState(output?.name || '');
  const [description, setDescription] = useState(output?.description || '');
  const [oauthAppId, setOauthAppId] = useState<number | undefined>(output?.oauth_app_id);
  const [isEnabled, setIsEnabled] = useState(output?.is_enabled ?? true);
  const [sendOnWebhook, setSendOnWebhook] = useState(output?.send_on_webhook_trigger ?? true);
  const [sendOnChat, setSendOnChat] = useState(output?.send_on_chat_completion ?? false);
  const [retryOnFailure, setRetryOnFailure] = useState(output?.retry_on_failure ?? true);
  const [maxRetries, setMaxRetries] = useState(output?.max_retries || 3);
  const [outputTemplate, setOutputTemplate] = useState(output?.output_template || '');

  // Provider-specific config
  const [slackChannel, setSlackChannel] = useState<string>(
    (output?.config as SlackOutputConfig)?.channel || ''
  );
  const [emailTo, setEmailTo] = useState<string>(
    (output?.config as EmailOutputConfig)?.to?.join(', ') || ''
  );
  const [emailSubject, setEmailSubject] = useState<string>(
    (output?.config as EmailOutputConfig)?.subject || 'Agent Output'
  );
  const [webhookUrl, setWebhookUrl] = useState<string>(
    (output?.config as WebhookOutputConfig)?.url || ''
  );
  const [webhookMethod, setWebhookMethod] = useState<'POST' | 'PUT' | 'PATCH'>(
    (output?.config as WebhookOutputConfig)?.method || 'POST'
  );
  const [webhookHeaders, setWebhookHeaders] = useState<string>(
    JSON.stringify((output?.config as WebhookOutputConfig)?.headers || {}, null, 2)
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      let config: any = {};

      if (provider === 'slack') {
        config = { channel: slackChannel };
      } else if (provider === 'email') {
        config = {
          to: emailTo.split(',').map(e => e.trim()).filter(Boolean),
          subject: emailSubject,
        };
      } else if (provider === 'webhook') {
        config = {
          url: webhookUrl,
          method: webhookMethod,
          headers: webhookHeaders ? JSON.parse(webhookHeaders) : {},
        };
      }

      const data: CreateOutputConfigData = {
        name,
        description: description || undefined,
        provider,
        oauth_app_id: oauthAppId,
        config,
        output_template: outputTemplate || undefined,
        is_enabled: isEnabled,
        send_on_webhook_trigger: sendOnWebhook,
        send_on_chat_completion: sendOnChat,
        retry_on_failure: retryOnFailure,
        max_retries: maxRetries,
      };

      await onSubmit(data);
    } catch (error) {
      console.error('Error submitting output config:', error);
    } finally {
      setLoading(false);
    }
  };

  const providerApps = getAppsByProvider(provider);

  return (
    <form onSubmit={handleSubmit} className="p-6">
      <div className="space-y-6">
        {/* Basic Info */}
        <div>
          <h3 className="text-base font-semibold text-gray-900 mb-4">Basic Information</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Slack Notifications"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
                rows={2}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Provider Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Provider <span className="text-red-500">*</span>
          </label>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value as OutputProvider)}
            disabled={!!output}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            required
          >
            <option value="slack">Slack</option>
            <option value="email">Email</option>
            <option value="webhook">Webhook</option>
          </select>
          {!!output && (
            <p className="text-xs text-gray-600 mt-1">
              Provider cannot be changed after creation
            </p>
          )}
        </div>

        {/* OAuth App Selection (for Slack and Email) */}
        {(provider === 'slack' || provider === 'email') && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              {provider === 'slack' ? 'Slack App' : 'Email Configuration'} <span className="text-red-500">*</span>
            </label>
            <select
              value={oauthAppId?.toString() || ''}
              onChange={(e) => setOauthAppId(parseInt(e.target.value))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              required
            >
              <option value="">Select {provider} app</option>
              {providerApps.map((app) => (
                <option key={app.id} value={app.id.toString()}>
                  {app.name}
                </option>
              ))}
            </select>
            {providerApps.length === 0 && (
              <p className="text-xs text-gray-600 mt-1">
                No {provider} apps configured. Please set up OAuth app first.
              </p>
            )}
          </div>
        )}

        {/* Provider-Specific Configuration */}
        {provider === 'slack' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Channel or User <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={slackChannel}
              onChange={(e) => setSlackChannel(e.target.value)}
              placeholder="#channel or @username"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              required
            />
            <p className="text-xs text-gray-600 mt-1">
              Use # for channels or @ for direct messages
            </p>
          </div>
        )}

        {provider === 'email' && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Recipients <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={emailTo}
                onChange={(e) => setEmailTo(e.target.value)}
                placeholder="user@example.com, another@example.com"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                required
              />
              <p className="text-xs text-gray-600 mt-1">
                Comma-separated email addresses
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Subject <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={emailSubject}
                onChange={(e) => setEmailSubject(e.target.value)}
                placeholder="Agent Output"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                required
              />
            </div>
          </>
        )}

        {provider === 'webhook' && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Webhook URL <span className="text-red-500">*</span>
              </label>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://api.example.com/webhook"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                HTTP Method
              </label>
              <select
                value={webhookMethod}
                onChange={(e) => setWebhookMethod(e.target.value as 'POST' | 'PUT' | 'PATCH')}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              >
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="PATCH">PATCH</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Custom Headers (JSON)
              </label>
              <textarea
                value={webhookHeaders}
                onChange={(e) => setWebhookHeaders(e.target.value)}
                placeholder='{"Authorization": "Bearer token"}'
                rows={4}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent font-mono"
              />
            </div>
          </>
        )}

        {/* Output Template */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Output Template (Optional)
          </label>
          <textarea
            value={outputTemplate}
            onChange={(e) => setOutputTemplate(e.target.value)}
            placeholder="Use {response} for agent output, {event_type} for trigger type, etc."
            rows={4}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
          />
          <p className="text-xs text-gray-600 mt-1">
            Leave empty to use default formatting. Variables: {'{response}'}, {'{agent_name}'}, {'{event_type}'}
          </p>
        </div>

        {/* Trigger Configuration */}
        <div>
          <h3 className="text-base font-semibold text-gray-900 mb-3">When to Send</h3>
          <div className="space-y-3">
            <label className="flex items-center gap-2.5 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-gray-300 transition-all">
              <input
                type="checkbox"
                checked={sendOnWebhook}
                onChange={(e) => setSendOnWebhook(e.target.checked)}
                className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
              />
              <span className="text-sm font-medium text-gray-900">Send on webhook trigger</span>
            </label>
            <label className="flex items-center gap-2.5 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-gray-300 transition-all">
              <input
                type="checkbox"
                checked={sendOnChat}
                onChange={(e) => setSendOnChat(e.target.checked)}
                className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
              />
              <span className="text-sm font-medium text-gray-900">Send on chat completion</span>
            </label>
          </div>
        </div>

        {/* Retry Configuration */}
        <div>
          <h3 className="text-base font-semibold text-gray-900 mb-3">Retry Settings</h3>
          <div className="space-y-3">
            <label className="flex items-center gap-2.5 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-gray-300 transition-all">
              <input
                type="checkbox"
                checked={retryOnFailure}
                onChange={(e) => setRetryOnFailure(e.target.checked)}
                className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
              />
              <span className="text-sm font-medium text-gray-900">Retry on failure</span>
            </label>
            {retryOnFailure && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Max Retries
                </label>
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={maxRetries}
                  onChange={(e) => setMaxRetries(parseInt(e.target.value))}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                />
              </div>
            )}
          </div>
        </div>

        {/* Enable/Disable */}
        <div>
          <label className="flex items-center gap-2.5 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-gray-300 transition-all">
            <input
              type="checkbox"
              checked={isEnabled}
              onChange={(e) => setIsEnabled(e.target.checked)}
              className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
            />
            <span className="text-sm font-medium text-gray-900">Enable this output</span>
          </label>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-5 border-t border-gray-200">
          <button
            type="button"
            onClick={onCancel}
            className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-lg transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                {output ? 'Update' : 'Create'} Output
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
