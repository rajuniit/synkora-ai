/**
 * Activity Log Management Hooks
 * Custom hooks for activity log-related API operations
 */

import { useState, useCallback, useEffect } from 'react';
import { apiClient } from '@/lib/api/client';
import type {
  ActivityLog,
  ActivityLogFilters,
} from '@/types/activity';

export function useActivityLog() {
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ActivityLogFilters>({});

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filters.action) params.append('action', filters.action);
      if (filters.resource_type) params.append('resource_type', filters.resource_type);
      if (filters.account_id) params.append('account_id', filters.account_id);
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.limit) params.append('limit', filters.limit.toString());
      if (filters.offset) params.append('offset', filters.offset.toString());

      const queryString = params.toString();
      const url = `/api/v1/activity-logs${queryString ? `?${queryString}` : ''}`;
      
      const response = await apiClient.request('GET', url);
      setLogs(response.data || response || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch activity logs');
      setLogs([]);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  return {
    logs,
    isLoading,
    error,
    filters,
    setFilters,
    refetch: fetchLogs,
  };
}
