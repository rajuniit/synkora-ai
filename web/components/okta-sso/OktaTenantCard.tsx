'use client';

import React from 'react';
import { OktaTenant } from '@/types/okta-sso';

interface OktaTenantCardProps {
  tenant: OktaTenant;
  onEdit: () => void;
  onDelete: () => void;
  onTest: () => void;
}

export const OktaTenantCard: React.FC<OktaTenantCardProps> = ({
  tenant,
  onEdit,
  onDelete,
  onTest,
}) => {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {tenant.okta_domain}
            </h3>
            <span
              className={`px-2 py-1 text-xs font-medium rounded-full ${
                tenant.is_active
                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                  : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
              }`}
            >
              {tenant.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
          
          <div className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
            <p>
              <span className="font-medium">Tenant ID:</span> {tenant.tenant_id}
            </p>
            <p>
              <span className="font-medium">Client ID:</span>{' '}
              {tenant.client_id.substring(0, 20)}...
            </p>
          </div>

          {tenant.updated_at && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
              Last updated: {new Date(tenant.updated_at).toLocaleDateString()}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 ml-4">
          <button
            onClick={onTest}
            className="px-3 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md transition-colors"
          >
            Test
          </button>
          <button
            onClick={onEdit}
            className="px-3 py-1.5 text-sm font-medium text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
          >
            Edit
          </button>
          <button
            onClick={onDelete}
            className="px-3 py-1.5 text-sm font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};
