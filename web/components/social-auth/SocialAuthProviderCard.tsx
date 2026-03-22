'use client';

import React from 'react';
import { ProviderIcon } from './ProviderIcon';
import { SocialProvider } from '@/types/social-auth';

interface SocialAuthProviderCardProps {
  provider: SocialProvider;
  isLinked: boolean;
  providerEmail?: string;
  linkedAt?: string;
  onUnlink: () => Promise<void>;
  isUnlinking: boolean;
}

export const SocialAuthProviderCard: React.FC<SocialAuthProviderCardProps> = ({
  provider,
  isLinked,
  providerEmail,
  linkedAt,
  onUnlink,
  isUnlinking,
}) => {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <ProviderIcon provider={provider} size="lg" />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
                {provider}
              </h3>
              <span
                className={`px-2 py-1 text-xs font-medium rounded-full ${
                  isLinked
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                    : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                }`}
              >
                {isLinked ? 'Linked' : 'Not Linked'}
              </span>
            </div>
            {isLinked && providerEmail && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {providerEmail}
              </p>
            )}
            {isLinked && linkedAt && (
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                Linked: {new Date(linkedAt).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isLinked ? (
            <button
              onClick={onUnlink}
              disabled={isUnlinking}
              className="px-3 py-1.5 text-sm font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUnlinking ? 'Unlinking...' : 'Unlink'}
            </button>
          ) : (
            <button
              onClick={() => {
                // Trigger OAuth flow - will be handled by the page
                window.location.href = `/api/v1/auth/social/${provider}`;
              }}
              className="px-3 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md transition-colors"
            >
              Link Account
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
