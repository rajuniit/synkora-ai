'use client';

import { useState } from 'react';
import { ActivityLogTable } from '@/components/team/ActivityLogTable';
import { useActivityLog } from '@/hooks/useActivityLog';
import { ActivityAction, ActivityResourceType } from '@/types/activity';

export default function ActivityLogPage() {
  const { logs, isLoading, filters, setFilters } = useActivityLog();
  const [daysFilter, setDaysFilter] = useState<number>(7);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40">
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="mb-6">
          <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Activity Log</h1>
          <p className="mt-1 text-sm text-gray-600">
            View all activity and changes in your workspace
          </p>
        </div>

        {/* Filters */}
        <div className="mb-5 bg-white shadow-sm border border-gray-200 rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">
                Action Type
              </label>
              <select
                value={filters.action || ''}
                onChange={(e) => setFilters({ ...filters, action: (e.target.value as ActivityAction) || undefined })}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
              >
                <option value="">All Actions</option>
                <option value="create">Create</option>
                <option value="update">Update</option>
                <option value="delete">Delete</option>
                <option value="login">Login</option>
                <option value="logout">Logout</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">
                Resource Type
              </label>
              <select
                value={filters.resource_type || ''}
                onChange={(e) => setFilters({ ...filters, resource_type: (e.target.value as ActivityResourceType) || undefined })}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
              >
                <option value="">All Resources</option>
                <option value="agent">Agent</option>
                <option value="team_member">Team Member</option>
                <option value="profile">Profile</option>
                <option value="permission">Permission</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">
                Date Range
              </label>
              <select
                value={daysFilter}
                onChange={(e) => setDaysFilter(parseInt(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
              >
                <option value="1">Last 24 hours</option>
                <option value="7">Last 7 days</option>
                <option value="30">Last 30 days</option>
                <option value="90">Last 90 days</option>
              </select>
            </div>
          </div>
        </div>

        {/* Activity Log Table */}
        <ActivityLogTable logs={logs} />

        {/* Info Box */}
        <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-4 w-4 text-red-500"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-xs font-medium text-red-800">About Activity Logs</h3>
              <div className="mt-1.5 text-xs text-red-700">
                <p>
                  Activity logs track all important actions in your workspace for security and compliance.
                  Logs are retained for 90 days and can be exported for audit purposes.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
